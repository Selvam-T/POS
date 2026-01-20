import os
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QLineEdit, QPushButton, QLabel, QTableWidget, QComboBox
from PyQt5.QtCore import Qt
from modules.ui_utils.focus_utils import FieldCoordinator
from modules.ui_utils import input_handler, ui_feedback, error_logger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')
view_hold = os.path.join(UI_DIR, 'view_hold.ui')

def open_view_hold_dialog(parent=None):
    
    dlg = uic.loadUi(view_hold)
    
    # Ensure custom frameless window
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
    dlg.setModal(True)

    # --- 1. Apply dialog.qss Styling ---
    try:
        qss_path = os.path.join(BASE_DIR, 'assets', 'dialog.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r', encoding='utf-8') as f:
                dlg.setStyleSheet(f.read())
    except Exception as e:
        try:
            error_logger.log_error(f"Failed to load dialog.qss: {e}")
        except Exception:
            pass
    
    # 2. Widgets
    receipt_in = dlg.findChild(QLineEdit, 'viewHoldSearchLineEdit') 
    table_in = dlg.findChild(QTableWidget, 'viewholdNotesTextEdit')

    # Connect buttons
    # Button names as per hold_sales.ui
    if hasattr(dlg, 'btnViewHoldCancel'):
        dlg.btnViewHoldCancel.clicked.connect(dlg.reject)
    if hasattr(dlg, 'btnViewHoldOk'):
        dlg.btnViewHoldOk.clicked.connect(dlg.accept)
    if hasattr(dlg, 'customCloseBtn'):
        dlg.customCloseBtn.clicked.connect(dlg.reject)
    
    # SET INITIAL FOCUS
    receipt_in.setFocus()
    return dlg