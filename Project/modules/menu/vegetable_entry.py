from typing import List, Dict
from PyQt5 import QtWidgets

from modules.wrappers import settings as app_settings


# Button object names in ui/vegetable_entry.ui, in left-to-right, top-to-bottom order
VEG_BUTTON_NAMES: List[str] = [
    'btnVeg1', 'btnVeg2', 'btnVeg3', 'btnVeg4',
    'btnVeg5', 'btnVeg6', 'btnVeg7', 'btnVeg8',
    'btnVeg9', 'btnVeg10', 'btnVeg11', 'btnVeg12',
    'btnVeg13', 'btnVeg14',
]


class VegetableEntryController:
    """Applies vegetable label mapping to the entry panel buttons.

    Use with the QWidget loaded from ui/vegetable_entry.ui.
    """

    def __init__(self, panel: QtWidgets.QWidget) -> None:
        self.panel = panel
        # Cache resolved buttons (ignore missing safely)
        self.buttons: List[QtWidgets.QPushButton] = []
        for name in VEG_BUTTON_NAMES:
            btn = panel.findChild(QtWidgets.QPushButton, name)
            if btn is not None:
                self.buttons.append(btn)

    # ---------------------------- Public API ----------------------------
    def apply_from_settings(self) -> None:
        mapping = app_settings.load_vegetables()
        self.apply_mapping(mapping)

    def apply_mapping(self, mapping: Dict[str, Dict[str, str]]) -> None:
        # Map veg1..vegN to buttons in fixed order; OK/CANCEL are not in this list
        n = min(len(self.buttons), app_settings.veg_slots())
        for i in range(1, n + 1):
            btn = self.buttons[i - 1]
            entry = mapping.get(f'veg{i}', {"state": "unused", "label": "unused"})
            if entry.get('state') == 'custom':
                btn.setText(entry.get('label', ''))
                btn.setEnabled(True)
                btn.setProperty('unused', False)
            else:
                btn.setText('Not Used')
                btn.setEnabled(False)
                btn.setProperty('unused', True)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def connect_editor(self, editor_dialog: QtWidgets.QDialog) -> None:
        # editor_dialog must emit configChanged(dict)
        if hasattr(editor_dialog, 'configChanged'):
            editor_dialog.configChanged.connect(self.apply_mapping)
