import os
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QLineEdit, QPushButton, QLabel
from PyQt5.QtCore import Qt
from modules.ui_utils import input_handler

def open_manual_entry_dialog(parent):
    """Open the Manual Product Entry dialog and return QDialog for wrapper execution.
    
    DialogWrapper handles: overlay, sizing, centering, scanner blocking, cleanup, and focus restoration.
    This function only creates and returns the QDialog.
    
    Args:
        parent: Main window instance
    
    Returns:
        QDialog instance ready for DialogWrapper.open_dialog_scanner_blocked() to execute
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    UI_DIR = os.path.join(BASE_DIR, 'ui')
    manual_ui = os.path.join(UI_DIR, 'manual_entry.ui')
    
    if not os.path.exists(manual_ui):
        print('manual_entry.ui not found at', manual_ui)
        return None

    # Load dialog directly (QDialog root from .ui file)
    try:
        dlg = uic.loadUi(manual_ui)
    except Exception as e:
        print('Failed to load manual_entry.ui:', e)
        return None

    # Set dialog properties (frameless, no OS title bar)
    dlg.setParent(parent)
    dlg.setModal(True)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)

    # Apply styles
    try:
        assets_dir = os.path.join(BASE_DIR, 'assets')
        sales_qss = os.path.join(assets_dir, 'sales.qss')
        if os.path.exists(sales_qss):
            with open(sales_qss, 'r') as f:
                dlg.setStyleSheet(f.read())
    except Exception as e:
        print('Failed to load sales.qss:', e)

    # Get input fields
    product_name_input = dlg.findChild(QLineEdit, 'inputProductName')
    quantity_input = dlg.findChild(QLineEdit, 'inputQuantity')
    unit_price_input = dlg.findChild(QLineEdit, 'inputUnitPrice')
    error_label = dlg.findChild(QLabel, 'lblError')
    btn_ok = dlg.findChild(QPushButton, 'btnManualOk')
    btn_cancel = dlg.findChild(QPushButton, 'btnManualCancel')
    custom_close_btn = dlg.findChild(QPushButton, 'customCloseBtn')

    # Use input_handler for validation
    def handle_ok():
        try:
            product_name = input_handler.handle_product_name_input(product_name_input)
            quantity = input_handler.handle_quantity_input(quantity_input)
            unit_price = input_handler.handle_price_input(unit_price_input, price_type="unit price")
            if error_label:
                error_label.setText("✓ Adding to sale...")
                error_label.setStyleSheet("color: #4caf50;")
            dlg.manual_entry_result = {
                'product_name': product_name,
                'quantity': quantity,
                'unit_price': unit_price
            }
            dlg.accept()
        except Exception as e:
            if error_label:
                error_label.setText(f"⚠ {str(e)}")
                error_label.setStyleSheet("color: #ff6b6b;")

    def handle_cancel():
        dlg.reject()

    # Connect buttons
    if btn_ok:
        btn_ok.clicked.connect(handle_ok)
    if btn_cancel:
        btn_cancel.clicked.connect(handle_cancel)
    if custom_close_btn:
        custom_close_btn.clicked.connect(handle_cancel)

    # Return QDialog for DialogWrapper to execute (scanner will be blocked by wrapper)
    return dlg
