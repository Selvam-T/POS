import os
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QLineEdit, QPushButton, QLabel
from PyQt5.QtCore import Qt
from modules.ui_utils.focus_utils import FieldCoordinator
from modules.ui_utils import input_handler, ui_feedback, error_logger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')
hold_sales = os.path.join(UI_DIR, 'hold_sales.ui')

def launch_hold_sales_dialog(parent=None):
    
    dlg = uic.loadUi(hold_sales)
    
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
    name_in = dlg.findChild(QLineEdit, 'holdSalesCustomerLineEdit') 
    notes_in = dlg.findChild(QLineEdit, 'holdSalesNotesTextEdit')

    # Connect buttons
    # Button names as per hold_sales.ui
    if hasattr(dlg, 'btnHoldSalesCancel'):
        dlg.btnHoldSalesCancel.clicked.connect(dlg.reject)
    if hasattr(dlg, 'btnHoldSalesOk'):
        dlg.btnHoldSalesOk.clicked.connect(dlg.accept)
    if hasattr(dlg, 'customCloseBtn'):
        dlg.customCloseBtn.clicked.connect(dlg.reject)
    
    # SET INITIAL FOCUS
    name_in.setFocus()
    return dlg
