"""Centralized focus/relationship coordinator for PyQt dialogs."""

from PyQt5.QtCore import QObject, Qt, QEvent
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

    def add_link(self, source, target_map=None, lookup_fn=None, next_focus=None, status_label=None, on_sync=None, auto_jump=False, placeholder_mode=None):
        """Register relationship (lookup optional for simple focus-jumps)."""
        reactive_placeholders = (placeholder_mode == 'reactive')
        self.links[source] = {
            'targets': target_map or {},
            'lookup': lookup_fn,
            'next': next_focus,
            'status_label': status_label,
            'on_sync': on_sync,
            'auto_jump': auto_jump,
            'reactive_placeholders': reactive_placeholders,
        }

        # Opt-in: hide placeholders at rest; only show when targets stay empty after sync.
        if reactive_placeholders:
            for _w in (target_map or {}).values():
                self._set_reactive_placeholder(_w, show=False)
        
        if isinstance(source, QLineEdit):
            source.textEdited.connect(lambda: self._sync_fields(source))
        elif isinstance(source, QComboBox):
            source.activated.connect(lambda: self._sync_fields(source))
            
        source.installEventFilter(self)

    def _sync_fields(self, source):
        link = self.links[source]
        if not link['lookup']: return # Skip if it's just a focus jump link

        val = source.text().strip() if hasattr(source, 'text') else source.currentText()
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
                val = obj.text().strip() if hasattr(obj, 'text') else obj.currentText()
                
                # --- THE SWALLOW LOGIC ---
                # If the box is empty, we "swallow" the Enter key and stay here.
                if not val:
                    if hasattr(obj, 'selectAll'):
                        obj.selectAll()
                    return True # Returns True but DOES NOT call _move_focus
                
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