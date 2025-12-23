import os
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QLineEdit, QPushButton, QLabel
from PyQt5.QtCore import Qt

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

    # Set dialog properties
    dlg.setParent(parent)
    dlg.setModal(True)
    dlg.setWindowTitle('Manual Product Input')
    dlg.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
    
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

    # OK button handler
    def handle_ok():
        # TODO: Consider creating a shared validation utility (modules/ui_utils/validation.py)
        # for consistent error messaging and field focus management across all modal dialogs.
        # This would centralize validation patterns used in manual_entry, vegetable_entry, 
        # product_menu, admin_menu, etc.
        try:
            product_name = product_name_input.text().strip() if product_name_input else ""
            quantity_str = quantity_input.text().strip() if quantity_input else ""
            unit_price_str = unit_price_input.text().strip() if unit_price_input else ""
            
            # Validate product name
            if not product_name:
                if error_label:
                    error_label.setText("⚠ Product name is required")
                    error_label.setStyleSheet("color: #ff6b6b;")
                if product_name_input:
                    product_name_input.setFocus()
                return
            
            # Validate quantity
            if not quantity_str:
                if error_label:
                    error_label.setText("⚠ Quantity is required")
                    error_label.setStyleSheet("color: #ff6b6b;")
                if quantity_input:
                    quantity_input.setFocus()
                return
            
            try:
                quantity = float(quantity_str)
                if quantity <= 0:
                    raise ValueError("Must be positive")
            except ValueError:
                if error_label:
                    error_label.setText("⚠ Quantity must be a positive number")
                    error_label.setStyleSheet("color: #ff6b6b;")
                if quantity_input:
                    quantity_input.selectAll()
                    quantity_input.setFocus()
                return
            
            # Validate unit price
            if not unit_price_str:
                if error_label:
                    error_label.setText("⚠ Unit price is required")
                    error_label.setStyleSheet("color: #ff6b6b;")
                if unit_price_input:
                    unit_price_input.setFocus()
                return
            
            try:
                unit_price = float(unit_price_str)
                if unit_price <= 0:
                    raise ValueError("Must be positive")
            except ValueError:
                if error_label:
                    error_label.setText("⚠ Unit price must be a positive number")
                    error_label.setStyleSheet("color: #ff6b6b;")
                if unit_price_input:
                    unit_price_input.selectAll()
                    unit_price_input.setFocus()
                return
            
            # Success - clear error and store result
            if error_label:
                error_label.setText("✓ Adding to sale...")
                error_label.setStyleSheet("color: #4caf50;")
            
            # Store result data on dialog object for later retrieval
            dlg.manual_entry_result = {
                'product_name': product_name,
                'quantity': quantity,
                'unit_price': unit_price
            }
            dlg.accept()
        except Exception as e:
            if error_label:
                error_label.setText(f"Error: {str(e)}")
                error_label.setStyleSheet("color: #ff6b6b;")

    # Cancel button handler
    def handle_cancel():
        dlg.reject()

    # Connect buttons
    if btn_ok:
        btn_ok.clicked.connect(handle_ok)
    if btn_cancel:
        btn_cancel.clicked.connect(handle_cancel)

    # Return QDialog for DialogWrapper to execute
    return dlg
