import os
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QVBoxLayout
from PyQt5.QtCore import Qt

def open_manual_entry_dialog(parent):
    """Open the Manual Product Entry dialog and return QDialog for wrapper execution.
    
    DialogWrapper handles: overlay, sizing, centering, scanner blocking, cleanup, and focus restoration.
    This function only creates and returns the QDialog.
    
    Args:
        parent: Main window instance
    
    Returns:
        QDialog instance ready for DialogWrapper.open_standard_dialog() to execute
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    UI_DIR = os.path.join(BASE_DIR, 'ui')
    manual_ui = os.path.join(UI_DIR, 'manual_entry.ui')
    
    if not os.path.exists(manual_ui):
        print('manual_entry.ui not found at', manual_ui)
        return None

    # Load UI content
    try:
        content = uic.loadUi(manual_ui)
    except Exception as e:
        print('Failed to load manual_entry.ui:', e)
        return None

    # Create dialog container
    dlg = QDialog(parent)
    dlg.setModal(True)
    dlg.setWindowTitle('Manual Product Input')
    dlg.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
    
    # Install content into dialog
    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(content)

    # Apply size constraints from the loaded UI to the dialog
    dlg.setMinimumSize(content.minimumSize())
    dlg.setMaximumSize(content.maximumSize())
    dlg.resize(content.size())

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
    product_name_input = content.findChild(type(content), 'inputProductName')
    quantity_input = content.findChild(type(content), 'inputQuantity')
    unit_price_input = content.findChild(type(content), 'inputUnitPrice')
    btn_ok = content.findChild(type(content), 'btnManualOk')
    btn_cancel = content.findChild(type(content), 'btnManualCancel')

    # Data container to store result
    result_data = {'accepted': False}

    # OK button handler
    def handle_ok():
        try:
            product_name = product_name_input.text().strip() if product_name_input else ""
            quantity_str = quantity_input.text().strip() if quantity_input else "0"
            unit_price_str = unit_price_input.text().strip() if unit_price_input else "0"
            
            # Validate inputs
            if not product_name:
                print("Product name cannot be empty")
                return
            
            try:
                quantity = float(quantity_str)
                unit_price = float(unit_price_str)
            except ValueError:
                print("Quantity and Unit Price must be valid numbers")
                return
            
            if quantity <= 0:
                print("Quantity must be greater than 0")
                return
            
            if unit_price <= 0:
                print("Unit Price must be greater than 0")
                return
            
            # Store result data on dialog object for later retrieval
            dlg.manual_entry_result = {
                'product_name': product_name,
                'quantity': quantity,
                'unit_price': unit_price,
                'total': quantity * unit_price
            }
            dlg.accept()
        except Exception as e:
            print('Error processing manual entry:', e)

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
