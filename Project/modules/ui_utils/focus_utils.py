"""Centralized focus/relationship coordinator for PyQt dialogs.

This module intentionally keeps its existing public behavior stable.
New helpers added below are opt-in and do not affect existing dialogs
unless they explicitly call them.
"""

import unicodedata

from PyQt5.QtCore import QObject, Qt, QEvent, QTimer
from PyQt5.QtWidgets import QLineEdit, QComboBox, QPushButton
from modules.ui_utils import ui_feedback

class FieldCoordinator(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.links = {}
        self._placeholder_templates = {}
        self._validators = {}
        self._last_error_source = None
        self._last_error_label = None
        self._live_timers = {}

    def set_error(self, source_widget, message: str, status_label=None) -> bool:
        """Show an error on status_label and remember the source widget."""
        if status_label is None:
            return False
        try:
            self._last_error_source = source_widget
            self._last_error_label = status_label
        except Exception:
            pass
        return ui_feedback.set_status_label(status_label, message or "", ok=False)

    def set_ok(self, message: str, status_label=None, duration: int = 3000) -> bool:
        """Show success and clear remembered error state."""
        if status_label is None:
            return False
        try:
            self._last_error_source = None
            self._last_error_label = None
        except Exception:
            pass
        return ui_feedback.set_status_label(status_label, message or "", ok=True, duration=duration)

    def clear_status(self, status_label=None) -> bool:
        """Clear the status label and reset remembered error state."""
        if status_label is None:
            return False
        ui_feedback.clear_status_label(status_label)
        try:
            if self._last_error_label is status_label:
                self._last_error_source = None
                self._last_error_label = None
        except Exception:
            pass
        return True

    def register_validator(self, widget, validate_fn, status_label=None) -> bool:
        """Opt-in: auto-clear the last error when this widget becomes valid."""
        if widget is None or validate_fn is None or status_label is None:
            return False

        # Avoid double-connecting.
        if widget in self._validators:
            return True
        self._validators[widget] = {'validate_fn': validate_fn, 'status_label': status_label}

        def _maybe_clear():
            try:
                if self._last_error_source is not widget:
                    return
                if self._last_error_label is not status_label:
                    return
            except Exception:
                return

            try:
                validate_fn()
            except Exception:
                return

            ui_feedback.clear_status_label(status_label)
            try:
                self._last_error_source = None
                self._last_error_label = None
            except Exception:
                pass

        try:
            if isinstance(widget, QLineEdit):
                widget.editingFinished.connect(_maybe_clear)
            elif isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(lambda _i=None: _maybe_clear())
            else:
                return False
        except Exception:
            return False

        return True

    def _remember_placeholder(self, widget):
        if not isinstance(widget, QLineEdit):
            return
        if widget in self._placeholder_templates:
            return
        try:
            self._placeholder_templates[widget] = widget.placeholderText() or ""
        except Exception:
            self._placeholder_templates[widget] = ""

    def _set_reactive_placeholder(self, widget, show: bool) -> None:
        """Show/hide remembered placeholder for a target widget."""
        if not isinstance(widget, QLineEdit):
            return
        self._remember_placeholder(widget)
        try:
            widget.setPlaceholderText(self._placeholder_templates.get(widget, "") if show else "")
        except Exception:
            pass

    def add_link(
        self,
        source,
        target_map=None,
        lookup_fn=None,
        next_focus=None,
        status_label=None,
        on_sync=None,
        auto_jump=False,
        placeholder_mode=None,
        swallow_empty: bool = True,
        validate_fn=None,
        live_lookup: bool = False,
        live_min_chars: int = 0,
        live_debounce_ms: int = 180,
    ):
        """Register relationship (lookup optional for simple focus-jumps).

        swallow_empty controls Enter behavior:
        - True (default): empty field swallows Enter and stays put
        - False: empty field allows Enter to advance to next_focus
        """
        reactive_placeholders = (placeholder_mode == 'reactive')
        self.links[source] = {
            'targets': target_map or {},
            'lookup': lookup_fn,
            'next': next_focus,
            'status_label': status_label,
            'on_sync': on_sync,
            'auto_jump': auto_jump,
            'reactive_placeholders': reactive_placeholders,
            'swallow_empty': bool(swallow_empty),
            'validate_fn': validate_fn,
            'live_lookup': bool(live_lookup),
            'live_min_chars': int(live_min_chars or 0),
            'live_debounce_ms': int(live_debounce_ms or 0),
        }

        # Opt-in: hide placeholders at rest; only show when targets stay empty after sync.
        if reactive_placeholders:
            for _w in (target_map or {}).values():
                self._set_reactive_placeholder(_w, show=False)
        
        if isinstance(source, QLineEdit):
            # Default behavior: sync on user typing + finish-editing.
            # Opt-in behavior (live_lookup=True): sync debounced on textChanged to
            # support cases where focus doesn't change (e.g., clicking a NoFocus button).
            source.textEdited.connect(lambda: self._sync_fields(source))
            source.editingFinished.connect(lambda: self._sync_fields(source))

            link = self.links[source]
            if link.get('lookup') and link.get('live_lookup'):
                # One timer per source widget.
                timer = QTimer(source)
                timer.setSingleShot(True)
                self._live_timers[source] = timer

                def _fire_live():
                    try:
                        txt = (source.text() or '').strip()
                    except Exception:
                        txt = ''

                    min_chars = int(link.get('live_min_chars') or 0)
                    if txt and len(txt) < min_chars:
                        # Don't spam lookups or show 'Not Found' while still typing.
                        return
                    self._sync_fields(source)

                def _schedule_live(_t=None):
                    try:
                        delay = int(link.get('live_debounce_ms') or 0)
                    except Exception:
                        delay = 0
                    if delay <= 0:
                        _fire_live()
                        return
                    try:
                        timer.stop()
                        timer.timeout.disconnect()
                    except Exception:
                        pass
                    try:
                        timer.timeout.connect(_fire_live)
                    except Exception:
                        pass
                    timer.start(delay)

                source.textChanged.connect(_schedule_live)
        elif isinstance(source, QComboBox):
            source.activated.connect(lambda: self._sync_fields(source))
            
        source.installEventFilter(self)

    @staticmethod
    def _clean_lookup_text(text: str) -> str:
        """Normalize text used for lookups.

        Barcode scanners sometimes inject non-printable control characters
        (e.g., ASCII GS/RS) that are not removed by .strip(). These cause cache/DB
        lookups to fail even when the visible text looks correct.

        We remove Unicode category "C*" characters and then strip whitespace.
        """
        s = '' if text is None else str(text)
        try:
            s = ''.join(ch for ch in s if not unicodedata.category(ch).startswith('C'))
        except Exception:
            # Best-effort fallback: keep original string
            pass
        return s.strip()

    def _sync_fields(self, source):
        link = self.links[source]
        if not link['lookup']: return # Skip if it's just a focus jump link

        if hasattr(source, 'text'):
            val = self._clean_lookup_text(source.text())
        else:
            try:
                val = (source.currentText() or '').strip()
            except Exception:
                val = ''
        if not val:
            self._apply_state(source, None, is_clear=True)
            return

        result, err_msg = self._run_lookup(link['lookup'], val)
        self._apply_state(source, result, err_msg=err_msg)

    def _run_lookup(self, lookup_fn, val):
        """Runs lookup_fn and normalizes return value.

        Supported:
        - dict | None
        - (dict | None, str | None)
        """
        try:
            out = lookup_fn(val)
        except Exception:
            return None, "Lookup failed"
        if isinstance(out, tuple) and len(out) == 2:
            return out[0], out[1]
        return out, None

    def _apply_state(self, source, result, is_clear=False, err_msg=None):
        link = self.links[source]
        for key, widget in link['targets'].items():
            if widget:
                widget.blockSignals(True)
                widget.setText(str(result.get(key, "")) if result else "")
                widget.blockSignals(False)

                if link.get('reactive_placeholders'):
                    # On clear, hide placeholders. Otherwise show only for empty fields.
                    if is_clear:
                        self._set_reactive_placeholder(widget, show=False)
                    else:
                        try:
                            empty = isinstance(widget, QLineEdit) and not (widget.text() or "").strip()
                        except Exception:
                            empty = False
                        self._set_reactive_placeholder(widget, show=empty)

        if link['status_label']:
            if is_clear:
                self.clear_status(link['status_label'])
            elif result:
                self.set_ok("Match Found", status_label=link['status_label'])
            else:
                self.set_error(source, err_msg or "Not Found", status_label=link['status_label'])

        if link['on_sync']: link['on_sync'](result)
        if not is_clear and result and link.get('auto_jump'): self._move_focus(link['next'])

    def _move_focus(self, target):
        if not target: return
        if callable(target): target()
        else:
            target.setFocus()
            if hasattr(target, 'selectAll'): target.selectAll()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if isinstance(obj, QPushButton):
                obj.click()
                return True

            if obj in self.links:
                link = self.links[obj]
                # Get the value regardless of whether we are doing a lookup
                if hasattr(obj, 'text'):
                    val = self._clean_lookup_text(obj.text())
                else:
                    try:
                        val = (obj.currentText() or '').strip()
                    except Exception:
                        val = ''

                # Optional: validate on Enter (primarily for simple focus-jump links)
                validate_fn = link.get('validate_fn')
                
                # --- THE SWALLOW LOGIC ---
                # If the box is empty, we "swallow" the Enter key and stay here.
                if not val and link.get('swallow_empty', True):
                    # If a validate_fn exists, run it so the user sees the proper
                    # validation message even when the field is empty.
                    if callable(validate_fn) and link.get('status_label'):
                        try:
                            validate_fn()
                        except ValueError as e:
                            self.set_error(obj, str(e), status_label=link.get('status_label'))
                        except Exception:
                            pass
                    if hasattr(obj, 'selectAll'):
                        obj.selectAll()
                    return True # Returns True but DOES NOT call _move_focus

                # If this is a simple focus jump link with validate_fn, validate before moving.
                if callable(validate_fn) and not link.get('lookup'):
                    try:
                        validate_fn()
                    except ValueError as e:
                        if link.get('status_label'):
                            self.set_error(obj, str(e), status_label=link.get('status_label'))
                        if hasattr(obj, 'selectAll'):
                            obj.selectAll()
                        return True
                    except Exception:
                        # Best-effort: if validation throws unexpectedly, block the jump.
                        return True
                
                # If there is a lookup function, validate/sync
                if link['lookup']:
                    result, err_msg = self._run_lookup(link['lookup'], val)
                    if result:
                        self._apply_state(obj, result)
                        self._move_focus(link['next'])
                    else:
                        if link['status_label']:
                            self.set_error(obj, err_msg or "Invalid Entry", status_label=link['status_label'])
                        if hasattr(obj, 'selectAll'): obj.selectAll()
                else:
                    # Simple focus jump (Now only happens if val is NOT empty)
                    self._move_focus(link['next'])
                
                return True 
                
        return super().eventFilter(obj, event)


# =========================================================
# OPT-IN HELPERS (do not change existing behavior)
# =========================================================

def set_initial_focus(
    dlg,
    *,
    tab_widget=None,
    tab_index: int | None = None,
    tab_name: str | None = None,
    first_widget=None,
    select_all: bool = True,
) -> bool:
    """Best-effort initial focus helper.

    - If tab_widget is provided, selects a tab by index or by tab text.
    - Focuses first_widget and optionally selectAll() for line edits.

    Returns True if it likely focused something.
    """
    focused = False

    # 1) Activate tab (optional)
    try:
        if tab_widget is not None:
            if tab_index is not None:
                tab_widget.setCurrentIndex(int(tab_index))
            elif tab_name is not None:
                name = str(tab_name)
                for i in range(tab_widget.count()):
                    try:
                        if str(tab_widget.tabText(i)) == name:
                            tab_widget.setCurrentIndex(i)
                            break
                    except Exception:
                        continue
    except Exception:
        pass

    # 2) Focus widget (optional)
    try:
        if first_widget is not None:
            first_widget.setFocus(Qt.OtherFocusReason)
            focused = True
            if select_all and hasattr(first_widget, 'selectAll'):
                try:
                    first_widget.selectAll()
                except Exception:
                    pass
    except Exception:
        pass

    return focused


class FocusGate:
    """Remembers and toggles focusability for a group of widgets.

    Goal: "lock" widgets so they cannot receive focus until unlocked.
    This only affects focus policy (and optionally enabled/readOnly).

    This is opt-in and does not integrate automatically with FieldCoordinator.
    """

    def __init__(
        self,
        widgets,
        *,
        lock_enabled: bool = False,
        lock_read_only: bool = False,
    ):
        self._widgets = [w for w in (widgets or []) if w is not None]
        self._orig_focus_policy = {}
        self._orig_enabled = {}
        self._orig_read_only = {}
        self._lock_enabled = bool(lock_enabled)
        self._lock_read_only = bool(lock_read_only)
        self._remembered = False

    def remember(self) -> None:
        if self._remembered:
            return
        for w in self._widgets:
            try:
                self._orig_focus_policy[w] = w.focusPolicy()
            except Exception:
                pass
            try:
                self._orig_enabled[w] = w.isEnabled()
            except Exception:
                pass
            # Some widgets (e.g., QLineEdit) support readOnly
            try:
                if hasattr(w, 'isReadOnly') and callable(getattr(w, 'isReadOnly')):
                    self._orig_read_only[w] = bool(w.isReadOnly())
            except Exception:
                pass
        self._remembered = True

    def lock(self) -> None:
        """Prevent widgets from receiving focus."""
        self.remember()
        for w in self._widgets:
            try:
                w.setFocusPolicy(Qt.NoFocus)
            except Exception:
                pass
            if self._lock_enabled:
                try:
                    w.setEnabled(False)
                except Exception:
                    pass
            if self._lock_read_only and isinstance(w, QLineEdit):
                try:
                    w.setReadOnly(True)
                except Exception:
                    pass

    def unlock(self) -> None:
        """Restore original focusability (and optional enabled/readOnly state)."""
        self.remember()
        for w in self._widgets:
            try:
                w.setFocusPolicy(self._orig_focus_policy.get(w, Qt.StrongFocus))
            except Exception:
                pass
            if self._lock_enabled:
                try:
                    w.setEnabled(self._orig_enabled.get(w, True))
                except Exception:
                    pass
            if self._lock_read_only and isinstance(w, QLineEdit):
                try:
                    w.setReadOnly(self._orig_read_only.get(w, False))
                except Exception:
                    pass

    def set_locked(self, locked: bool) -> None:
        if locked:
            self.lock()
        else:
            self.unlock()


def set_focus_enabled(widgets, enabled: bool, *, remember: dict | None = None) -> dict:
    """Lightweight helper: toggle focusPolicy for widgets.

    - When enabled=False: sets Qt.NoFocus
    - When enabled=True: restores remembered policy (if provided) else Qt.StrongFocus

    Returns the remember-map to allow callers to persist it.
    """
    store = remember if isinstance(remember, dict) else {}
    ws = [w for w in (widgets or []) if w is not None]

    if enabled:
        for w in ws:
            try:
                w.setFocusPolicy(store.get(w, Qt.StrongFocus))
            except Exception:
                pass
        return store

    # disabling
    for w in ws:
        try:
            if w not in store:
                store[w] = w.focusPolicy()
        except Exception:
            pass
        try:
            w.setFocusPolicy(Qt.NoFocus)
        except Exception:
            pass
    return store


def enforce_exclusive_lineedits(
    a: QLineEdit,
    b: QLineEdit,
    *,
    on_switch_to_a=None,
    on_switch_to_b=None,
    clear_status_label=None,
) -> bool:
    """Opt-in: make two source line-edits mutually exclusive.

    Behavior:
    - When the user starts entering a non-empty value in A, and B already has text,
      B is cleared (with signals blocked), and on_switch_to_a is called.
    - Symmetric for switching to B.

    Notes:
    - Uses textChanged so it works for scanner/programmatic setText too.
    - Has no effect unless this function is called.
    """
    if not isinstance(a, QLineEdit) or not isinstance(b, QLineEdit):
        return False

    state = {'busy': False}

    def _safe_text(le: QLineEdit) -> str:
        try:
            return (le.text() or '').strip()
        except Exception:
            return ''

    def _clear(le: QLineEdit) -> None:
        try:
            le.blockSignals(True)
            le.setText('')
        except Exception:
            pass
        finally:
            try:
                le.blockSignals(False)
            except Exception:
                pass

    def _maybe_switch(active: QLineEdit, other: QLineEdit, on_switch) -> None:
        if state['busy']:
            return
        if not _safe_text(active):
            return
        if not _safe_text(other):
            return

        state['busy'] = True
        try:
            _clear(other)
            if clear_status_label is not None:
                try:
                    ui_feedback.clear_status_label(clear_status_label)
                except Exception:
                    pass
            if callable(on_switch):
                try:
                    on_switch()
                except Exception:
                    pass
        finally:
            state['busy'] = False

    try:
        a.textChanged.connect(lambda _t=None: _maybe_switch(a, b, on_switch_to_a))
        b.textChanged.connect(lambda _t=None: _maybe_switch(b, a, on_switch_to_b))
    except Exception:
        return False

    return True