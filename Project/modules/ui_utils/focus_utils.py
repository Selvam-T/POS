from PyQt5.QtCore import QObject, Qt, QEvent
from PyQt5.QtWidgets import QLineEdit, QComboBox, QPushButton
from modules.ui_utils import ui_feedback

class FieldCoordinator(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.links = {}

    def add_link(self, source, target_map=None, lookup_fn=None, next_focus=None, status_label=None, on_sync=None, auto_jump=False):
        """Register relationship. lookup_fn is now optional for simple focus jumps."""
        self.links[source] = {
            'targets': target_map or {},
            'lookup': lookup_fn,
            'next': next_focus,
            'status_label': status_label,
            'on_sync': on_sync,
            'auto_jump': auto_jump
        }
        
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

        result = link['lookup'](val)
        self._apply_state(source, result)

    def _apply_state(self, source, result, is_clear=False):
        link = self.links[source]
        for key, widget in link['targets'].items():
            if widget:
                widget.blockSignals(True)
                widget.setText(str(result.get(key, "")) if result else "")
                widget.blockSignals(False)

        if link['status_label']:
            if is_clear: ui_feedback.clear_status_label(link['status_label'])
            elif result: ui_feedback.set_status_label(link['status_label'], "Match Found", ok=True)
            else: ui_feedback.set_status_label(link['status_label'], "Not Found", ok=False)

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
                    result = link['lookup'](val)
                    if result:
                        self._apply_state(obj, result)
                        self._move_focus(link['next'])
                    else:
                        if link['status_label']:
                            ui_feedback.set_status_label(link['status_label'], "Invalid Entry", ok=False)
                        if hasattr(obj, 'selectAll'): obj.selectAll()
                else:
                    # Simple focus jump (Now only happens if val is NOT empty)
                    self._move_focus(link['next'])
                
                return True 
                
        return super().eventFilter(obj, event)