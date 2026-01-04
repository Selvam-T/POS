from PyQt5.QtCore import QObject, Qt, QEvent
from PyQt5.QtWidgets import QLineEdit, QComboBox
from modules.ui_utils import ui_feedback

class FieldCoordinator(QObject):
    def __init__(self, parent):
        """Initialize the coordinator and the storage for widget links."""
        super().__init__(parent)
        self.links = {}

    def add_link(self, source, target_map, lookup_fn, next_focus=None, status_label=None, on_sync=None, auto_jump=False):
        """Register a relationship between widgets."""
        self.links[source] = {
            'targets': target_map,
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
        """Internal method to trigger lookup when user types or selects."""
        link = self.links[source]
        val = source.text().strip() if hasattr(source, 'text') else source.currentText()
        
        if not val:
            self._apply_state(source, None, is_clear=True)
            return

        result = link['lookup'](val)
        self._apply_state(source, result)

    def _apply_state(self, source, result, is_clear=False):
        """Updates UI based on lookup result."""
        link = self.links[source]
        
        # 1. Update Target Widgets
        for key, widget in link['targets'].items():
            if widget:
                widget.blockSignals(True)
                widget.setText(str(result.get(key, "")) if result else "")
                widget.blockSignals(False)

        # 2. Update Status Label
        if link['status_label']:
            if is_clear:
                ui_feedback.clear_status_label(link['status_label'])
            elif result:
                ui_feedback.set_status_label(link['status_label'], "✓ Match Found", ok=True)
            else:
                ui_feedback.set_status_label(link['status_label'], "⚠ Not Found", ok=False)

        # 3. Custom Sync Logic (like placeholders)
        if link['on_sync']:
            link['on_sync'](result)

        # 4. Auto-Jump Focus
        if not is_clear and result and link.get('auto_jump'):
            self._move_focus(link['next'])

    def _move_focus(self, target):
        """Safely moves focus or executes a callback."""
        if not target:
            return
        if callable(target):
            target()
        else:
            target.setFocus()
            if hasattr(target, 'selectAll'):
                target.selectAll()

    def eventFilter(self, obj, event):
        """Handles manual Enter key presses."""
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if obj in self.links:
                link = self.links[obj]
                val = obj.text().strip() if hasattr(obj, 'text') else obj.currentText()
                result = link['lookup'](val)
                
                if result:
                    self._move_focus(link['next'])
                return True
        return False