"""Centralized focus/relationship coordinator for PyQt dialogs.

This module intentionally keeps its existing public behavior stable.
New helpers added below are opt-in and do not affect existing dialogs
unless they explicitly call them.
"""

import unicodedata

from PyQt5.QtCore import QObject, Qt, QEvent, QTimer
from PyQt5.QtWidgets import QLineEdit, QComboBox, QPushButton
from modules.ui_utils import ui_feedback
from modules.ui_utils.canonicalization import canonicalize_product_code, canonicalize_title_text

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

        if reactive_placeholders:
            for _w in (target_map or {}).values():
                self._set_reactive_placeholder(_w, show=False)
        
        if isinstance(source, QLineEdit):
            link = self.links[source]
            if link.get('lookup') and link.get('live_lookup'):
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

                # When live_lookup is enabled, avoid immediate per-keystroke lookups.
                # Debounced execution is driven by textChanged.
                source.textChanged.connect(_schedule_live)
            else:
                source.textEdited.connect(lambda: self._sync_fields(source))

            source.editingFinished.connect(lambda: self._sync_fields(source))
        elif isinstance(source, QComboBox):
            source.activated.connect(lambda: self._sync_fields(source))
            
        source.installEventFilter(self)

    @staticmethod
    def _clean_lookup_text(text: str) -> str:
        s = str(text or "")
        try:
            s = ''.join(ch for ch in s if not unicodedata.category(ch).startswith('C'))
        except Exception:
            pass
        return s

    def _standardize_widget_text(self, widget):
        if not isinstance(widget, QLineEdit):
            return
        raw = widget.text().strip()
        if not raw: return

        name = (widget.objectName() or "").lower()
        standardized = raw

        # 1. PRICE/COST FORMATTING (e.g., 1. -> 1.00)
        if "price" in name or "cost" in name:
            try:
                # Only format if it's a valid number
                val = float(raw)
                standardized = f"{val:.2f}"
            except ValueError:
                standardized = raw # Leave it for validation to catch the error

        # 2. CASING STANDARDIZATION
        elif "code" in name:
            standardized = canonicalize_product_code(raw)
        else:
            standardized = canonicalize_title_text(raw)
            
        if raw != standardized:
            widget.blockSignals(True)
            widget.setText(standardized)
            widget.blockSignals(False)

    def _sync_fields(self, source):
        link = self.links[source]
        if isinstance(source, QLineEdit):
            raw_text = source.text()
        elif isinstance(source, QComboBox):
            raw_text = source.currentText()
        else:
            raw_text = ""
        
        val = self._clean_lookup_text(raw_text)
        if val != raw_text and isinstance(source, QLineEdit):
            source.blockSignals(True)
            source.setText(val)
            source.blockSignals(False)

        lookup_val = val.strip()
        if not lookup_val:
            self._apply_state(source, None, is_clear=True)
            return

        if not link['lookup']: 
            return
        
        # Perform the search using the stripped value
        result, err_msg = self._run_lookup(link['lookup'], lookup_val)
        self._apply_state(source, result, err_msg=err_msg)

    def _run_lookup(self, lookup_fn, val):
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
        # 1. Reactive Status Clearing (Clear error when user clicks back in)
        if event.type() == QEvent.FocusIn:
            if obj in self.links:
                link = self.links[obj]
                if link.get('status_label'):
                    self.clear_status(link['status_label'])

        # 2. Key Handling (Enter/Return)
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if obj in self.links:
                # Handle QPushButton click
                if isinstance(obj, QPushButton):
                    obj.click()
                    return True

                link = self.links[obj]
                
                # Apply Phase 1 Casing Standardization immediately on ENTER
                self._standardize_widget_text(obj)
                
                val = obj.text() if hasattr(obj, 'text') else ""
                validate_fn = link.get('validate_fn')

                # IMPROVED TRAP: Uses QTimer to ensure the grab happens AFTER Qt's default processing
                def _trap_focus():
                    # A 0ms timer ensures this happens at the start of the next cycle
                    QTimer.singleShot(0, lambda: (obj.setFocus(), obj.selectAll() if hasattr(obj, 'selectAll') else None))

                # --- PATH A: Validation (Mainly ADD Tab) ---
                if callable(validate_fn):
                    try:
                        validate_fn()
                    except ValueError as e:
                        # Duplicate code or invalid name found
                        if link.get('status_label'):
                            self.set_error(obj, str(e), status_label=link['status_label'])
                        _trap_focus()  # STICKY: Trap focus firmly
                        return True    # Swallow the event

                # If validation normalized/cleared text, re-read before lookup/jump.
                try:
                    val = obj.text() if hasattr(obj, 'text') else val
                except Exception:
                    pass

                # --- PATH B: Lookup (Mainly UPDATE/REMOVE Tabs) ---
                if link['lookup']:
                    result, err_msg = self._run_lookup(link['lookup'], val)
                    if result:
                        self._apply_state(obj, result)
                        self._move_focus(link['next'])
                    else:
                        if link['status_label']:
                            self.set_error(obj, err_msg or "Not Found", status_label=link['status_label'])
                        _trap_focus() # STICKY: Trap focus firmly
                        return True 
                else:
                    # --- PATH C: Simple Focus Jump ---
                    if not val and link.get('swallow_empty', True):
                        _trap_focus()
                        return True
                    self._move_focus(link['next'])
                
                return True 
                
        return super().eventFilter(obj, event)


# =========================================================
# OPT-IN HELPERS
# =========================================================

def set_initial_focus(dlg, *, tab_widget=None, tab_index=None, tab_name=None, first_widget=None, select_all=True):
    focused = False
    try:
        if tab_widget is not None:
            if tab_index is not None:
                tab_widget.setCurrentIndex(int(tab_index))
            elif tab_name is not None:
                name = str(tab_name)
                for i in range(tab_widget.count()):
                    if str(tab_widget.tabText(i)) == name:
                        tab_widget.setCurrentIndex(i)
                        break
    except Exception: pass
    try:
        if first_widget is not None:
            first_widget.setFocus(Qt.OtherFocusReason)
            focused = True
            if select_all and hasattr(first_widget, 'selectAll'):
                first_widget.selectAll()
    except Exception: pass
    return focused

class FocusGate:
    def __init__(self, widgets, lock_enabled: bool = False, lock_read_only: bool = False):
        self._widgets = [w for w in (widgets or []) if w is not None]
        self._orig_focus_policy = {}
        self._orig_enabled = {}
        self._orig_read_only = {}
        self._lock_enabled_cfg = bool(lock_enabled)
        self._lock_read_only_cfg = bool(lock_read_only)
        self._remembered = False

    def remember(self) -> None:
        if self._remembered: return
        for w in self._widgets:
            try:
                self._orig_focus_policy[w] = w.focusPolicy()
                self._orig_enabled[w] = w.isEnabled()
                if hasattr(w, 'isReadOnly') and callable(getattr(w, 'isReadOnly')):
                    self._orig_read_only[w] = bool(w.isReadOnly())
            except Exception: pass
        self._remembered = True

    def lock(self) -> None:
        self.remember()
        for w in self._widgets:
            try:
                w.setFocusPolicy(Qt.NoFocus)
                if self._lock_enabled_cfg: w.setEnabled(False)
                if isinstance(w, QLineEdit):
                    w.setReadOnly(True)
                elif isinstance(w, QComboBox):
                    w.setProperty("locked", True)
                    w.style().unpolish(w)
                    w.style().polish(w)
            except Exception: pass

    def unlock(self) -> None:
        self.remember()
        for w in self._widgets:
            try:
                w.setFocusPolicy(self._orig_focus_policy.get(w, Qt.StrongFocus))
                if self._lock_enabled_cfg: w.setEnabled(self._orig_enabled.get(w, True))
                if isinstance(w, QLineEdit):
                    w.setReadOnly(self._orig_read_only.get(w, False))
                elif isinstance(w, QComboBox):
                    w.setProperty("locked", False)
                    w.style().unpolish(w)
                    w.style().polish(w)
            except Exception: pass

    def set_locked(self, locked: bool) -> None:
        if locked: self.lock()
        else: self.unlock()

def set_focus_enabled(widgets, enabled: bool, *, remember: dict | None = None) -> dict:
    store = remember if isinstance(remember, dict) else {}
    ws = [w for w in (widgets or []) if w is not None]
    if enabled:
        for w in ws:
            try: w.setFocusPolicy(store.get(w, Qt.StrongFocus))
            except Exception: pass
        return store
    for w in ws:
        try:
            if w not in store: store[w] = w.focusPolicy()
            w.setFocusPolicy(Qt.NoFocus)
        except Exception: pass
    return store

def enforce_exclusive_lineedits(a: QLineEdit, b: QLineEdit, *, on_switch_to_a=None, on_switch_to_b=None, clear_status_label=None) -> bool:
    if not isinstance(a, QLineEdit) or not isinstance(b, QLineEdit): return False
    state = {'busy': False}
    def _safe_text(le):
        try: return (le.text() or '').strip()
        except: return ''
    def _clear(le):
        try:
            le.blockSignals(True)
            le.setText('')
        finally: le.blockSignals(False)
    def _maybe_switch(active, other, on_switch):
        if state['busy'] or not _safe_text(active) or not _safe_text(other): return
        state['busy'] = True
        try:
            _clear(other)
            if clear_status_label: ui_feedback.clear_status_label(clear_status_label)
            if callable(on_switch): on_switch()
        finally: state['busy'] = False
    try:
        a.textChanged.connect(lambda: _maybe_switch(a, b, on_switch_to_a))
        b.textChanged.connect(lambda: _maybe_switch(b, a, on_switch_to_b))
    except: return False
    return True