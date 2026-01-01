import os
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QLineEdit, QPushButton, QLabel, QComboBox
from PyQt5.QtCore import Qt
from modules.ui_utils import input_handler, ui_feedback
from modules.db_operation.database import PRODUCT_CACHE

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
    product_name_line = dlg.findChild(QLineEdit, 'manualProductNameLineEdit')
    product_code_line = dlg.findChild(QLineEdit, 'manualProductCodeLineEdit')
    quantity_input = dlg.findChild(QLineEdit, 'manualQuantityLineEdit')
    unit_price_input = dlg.findChild(QLineEdit, 'manualUnitPriceLineEdit') if hasattr(dlg, 'manualUnitPriceLineEdit') else None
    error_label = dlg.findChild(QLabel, 'manualStatusLabel') or dlg.findChild(QLabel, 'lblError')
    btn_ok = dlg.findChild(QPushButton, 'btnManualOk')
    btn_cancel = dlg.findChild(QPushButton, 'btnManualCancel')
    custom_close_btn = dlg.findChild(QPushButton, 'customCloseBtn')


    # --- QLineEdit + QCompleter for product name search ---
    from PyQt5.QtWidgets import QCompleter
    product_names = [v[0] for v in PRODUCT_CACHE.values() if v[0]]
    name_to_code = {v[0]: k for k, v in PRODUCT_CACHE.items() if v[0]}
    if product_name_line is not None:
        completer = QCompleter(product_names, product_name_line)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        product_name_line.setCompleter(completer)
        product_name_line.setPlaceholderText("Search Product Name")

        # When a product name is selected or editing finished, update product code field
        def update_product_code():
            name = product_name_line.text().strip()
            code = name_to_code.get(name, "")
            if product_code_line is not None:
                product_code_line.setText(code)
        product_name_line.editingFinished.connect(update_product_code)

    # Use input_handler for validation and ui_feedback for status
    def handle_ok():
        try:
            # Validate product name
            if product_name_line is None or not product_name_line.text().strip():
                ui_feedback.set_status_label(error_label, "Product name must be selected.", ok=False)
                product_name_line.setFocus()
                return
            # Validate product code
            if product_code_line is None or not product_code_line.text().strip():
                ui_feedback.set_status_label(error_label, "Product code missing.", ok=False)
                product_code_line.setFocus()
                return
            # Validate quantity
            quantity = input_handler.handle_quantity_input(quantity_input)
            # Validate unit price (if present)
            unit_price = None
            if unit_price_input is not None:
                unit_price = input_handler.handle_price_input(unit_price_input, price_type="unit price")
            # All good
            ui_feedback.set_status_label(error_label, "✓ Adding to sale...", ok=True)
            dlg.manual_entry_result = {
                'product_name': product_name_line.text().strip(),
                'product_code': product_code_line.text().strip(),
                'quantity': quantity,
                'unit_price': unit_price
            }
            dlg.accept()
        except Exception as e:
            ui_feedback.set_status_label(error_label, f"{str(e)}", ok=False)

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
