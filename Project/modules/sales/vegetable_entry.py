# --- Vegetable Entry Dialog Controller ---
import os
from typing import List, Dict
from PyQt5 import uic
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QTableWidget, QPushButton, QLabel, QHeaderView
from PyQt5.QtCore import Qt

from modules.wrappers import settings as app_settings


def open_vegetable_entry_dialog(parent):
    """Open the Add Vegetable panel as a modal dialog.
    
    DialogWrapper handles: overlay, sizing, centering, scanner blocking, cleanup, and focus restoration.
    This function only creates and returns the QDialog.
    
    Args:
        parent: Main window instance
    
    Returns:
        QDialog instance ready for DialogWrapper.open_standard_dialog() to execute
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    UI_DIR = os.path.join(BASE_DIR, 'ui')
    veg_ui = os.path.join(UI_DIR, 'vegetable_entry.ui')
    
    if not os.path.exists(veg_ui):
        print('vegetable_entry.ui not found at', veg_ui)
        return None

    # Load dialog directly (QDialog root from .ui file)
    try:
        dlg = uic.loadUi(veg_ui)
    except Exception as e:
        print('Failed to load vegetable_entry.ui:', e)
        return None

    # Set dialog properties
    dlg.setParent(parent)
    dlg.setModal(True)
    dlg.setWindowTitle('Digital Weight Input')
    dlg.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

    # Load and apply sales.qss for dialog-specific styling
    qss_path = os.path.join(BASE_DIR, 'assets', 'sales.qss')
    if os.path.exists(qss_path):
        try:
            with open(qss_path, 'r', encoding='utf-8') as f:
                dlg.setStyleSheet(f.read())
        except Exception as e:
            print('Failed to load sales.qss for vegetable entry dialog:', e)

    # Configure the vegetable table headers and behavior
    try:
        vtable = dlg.findChild(QTableWidget, 'vegEntryTable')
        if vtable is not None:
            vtable.setColumnCount(6)
            vtable.setHorizontalHeaderLabels(['No.', 'Name', 'Kilogram', 'Unit Price', 'Total', 'Del'])
            header = vtable.horizontalHeader()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.Fixed)   # No.
            header.setSectionResizeMode(1, QHeaderView.Stretch) # Item grows
            header.setSectionResizeMode(2, QHeaderView.Fixed)   # Kilogram
            header.setSectionResizeMode(3, QHeaderView.Fixed)   # Unit price
            header.setSectionResizeMode(4, QHeaderView.Fixed)   # Total
            header.setSectionResizeMode(5, QHeaderView.Fixed)   # Del
            header.resizeSection(0, 48)
            header.resizeSection(2, 125)
            header.resizeSection(3, 115)
            header.resizeSection(4, 115)
            header.resizeSection(5, 48)

            vtable.setAlternatingRowColors(True)
            vtable.setEditTriggers(QTableWidget.NoEditTriggers)
            vtable.setSelectionBehavior(QTableWidget.SelectRows)
            vtable.setSelectionMode(QTableWidget.SingleSelection)
    except Exception as e:
        print('Vegetable table setup failed:', e)

    # Wire keypad buttons to update message label and close on OK/CANCEL
    try:
        msg = dlg.findChild(QLabel, 'vegEntryMessage2')
        for name in (
            'btnVeg1','btnVeg2','btnVeg3','btnVeg4',
            'btnVeg5','btnVeg6','btnVeg7','btnVeg8',
            'btnVeg9','btnVeg10','btnVeg11','btnVeg12',
            'btnVeg13','btnVeg14','btnVeg15','btnVeg16',
        ):
            btn = dlg.findChild(QPushButton, name)
            if btn is not None and msg is not None:
                def set_green_message(_, b=btn):
                    msg.setText(f"Place {b.text()} on the scale ...")
                    msg.setStyleSheet("color: green;")
                btn.clicked.connect(set_green_message)

        ok_btn = dlg.findChild(QPushButton, 'btnVegOk')
        cancel_btn = dlg.findChild(QPushButton, 'btnVegCancel')
        if ok_btn is not None:
            ok_btn.clicked.connect(lambda: dlg.accept())
        if cancel_btn is not None:
            cancel_btn.clicked.connect(lambda: dlg.reject())
    except Exception as e:
        print('Vegetable keypad wiring failed:', e)

    # Return QDialog for DialogWrapper to execute
    return dlg


# Button object names in ui/vegetable_entry.ui, in left-to-right, top-to-bottom order
VEG_BUTTON_NAMES: List[str] = [
    'btnVeg1', 'btnVeg2', 'btnVeg3', 'btnVeg4',
    'btnVeg5', 'btnVeg6', 'btnVeg7', 'btnVeg8',
    'btnVeg9', 'btnVeg10', 'btnVeg11', 'btnVeg12',
    'btnVeg13', 'btnVeg14', 'btnVeg15', 'btnVeg16',
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

