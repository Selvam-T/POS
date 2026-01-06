import os
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QLineEdit, QPushButton, QLabel
from PyQt5.QtCore import Qt
from modules.ui_utils.focus_utils import FieldCoordinator
from modules.ui_utils import input_handler, ui_feedback
from modules.db_operation.database import PRODUCT_CACHE  # Added for completer data

def open_manual_entry_dialog(parent):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    UI_DIR = os.path.join(BASE_DIR, 'ui')
    manual_ui = os.path.join(UI_DIR, 'manual_entry.ui')
    dlg = uic.loadUi(manual_ui)
    
    # Ensure custom frameless window
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
    dlg.setModal(True)

    # --- 1. Apply menu.qss Styling (Fixed Issue 1) ---
    try:
        qss_path = os.path.join(BASE_DIR, 'assets', 'menu.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r', encoding='utf-8') as f:
                dlg.setStyleSheet(f.read())
    except Exception as e:
        print(f"Failed to load menu.qss: {e}")

    # 2. Widgets
    code_in = dlg.findChild(QLineEdit, 'manualProductCodeLineEdit')
    name_in = dlg.findChild(QLineEdit, 'manualNameSearchLineEdit')
    qty_in = dlg.findChild(QLineEdit, 'manualQuantityLineEdit')
    unit_dis = dlg.findChild(QLineEdit, 'manualUnitLineEdit')
    status_lbl = dlg.findChild(QLabel, 'manualStatusLabel')
    btn_ok = dlg.findChild(QPushButton, 'btnManualOk')
    unit_lbl = dlg.findChild(QLabel, 'manualUnitFieldLbl')

    # Mark the label as read-only for styling
    unit_lbl.setProperty("readOnly", "true")

    # Refresh style to ensure the property selector applies
    unit_lbl.style().unpolish(unit_lbl)
    unit_lbl.style().polish(unit_lbl)
    unit_lbl.update()
    
    # Updated names to match QSS selectors
    close_btn = dlg.findChild(QPushButton, 'customCloseBtn') 
    cancel_btn = dlg.findChild(QPushButton, 'btnManualCancel')

    # --- 3. Setup Completer  ---
    product_names = [rec[0] for rec in PRODUCT_CACHE.values() if rec[0]]
    completer = input_handler.setup_name_search_lineedit(name_in, product_names)

    # 4. Side-Effect: Placeholder Update & Price Storage
    def on_sync_data(result):
        # Update Placeholder
        if result and result.get('unit', '').lower() == 'kg':
            qty_in.setPlaceholderText('Enter 500g as 0.5 or 1Kg as 1')
        else:
            qty_in.setPlaceholderText('Enter Quantity')
        
        # Store price on widget so handle_ok can access it
        if result:
            name_in.setProperty('last_price', result.get('price', 0))

    # 5. Setup Coordinator
    coord = FieldCoordinator(dlg)
    
    # Link Code -> Name/Unit
    coord.add_link(
        source=code_in,
        target_map={'name': name_in, 'unit': unit_dis},
        lookup_fn=lambda val: input_handler.get_coordinator_lookup(val, 'code'),
        next_focus=qty_in,
        status_label=status_lbl,
        on_sync=on_sync_data,
        auto_jump=False
    )

    # Link Name -> Code/Unit
    coord.add_link(
        source=name_in,
        target_map={'code': code_in, 'unit': unit_dis},
        lookup_fn=lambda val: input_handler.get_coordinator_lookup(val, 'name'),
        next_focus=qty_in,
        status_label=status_lbl,
        on_sync=on_sync_data,
        auto_jump=True
    )
    
    # Trigger coordinator when completer is chosen
    if completer:
        completer.activated.connect(lambda: coord._sync_fields(name_in))

    # Link Quantity -> OK Button
    coord.add_link(
        source=qty_in,
        target_map={},
        lookup_fn=lambda val: {"val": val} if val else None,
        next_focus=lambda: btn_ok.click()
    )

    # 6. Finish logic
    def handle_ok():
        unit_type = unit_dis.text().strip().lower()
        expected_type = 'kg' if unit_type == 'kg' else 'unit'
        
        try:
            qty = input_handler.handle_quantity_input(qty_in, unit_type=expected_type)
            # Validation for empty product
            if not code_in.text() or not name_in.text():
                raise ValueError("Please select a valid product first.")

            dlg.manual_entry_result = {
                'product_code': code_in.text(),
                'product_name': name_in.text(),
                'quantity': qty,
                'unit': unit_dis.text(),
                'unit_price': float(name_in.property('last_price') or 0)
            }
            dlg.accept()
        except ValueError as e:
            ui_feedback.set_status_label(status_lbl, str(e), ok=False)

    # Close/Cancel logic
    def handle_close():
        dlg.reject() # DialogWrapper handles overlay and focus

    if close_btn:
        close_btn.clicked.connect(handle_close)
    if cancel_btn:
        cancel_btn.clicked.connect(handle_close)

    btn_ok.clicked.connect(handle_ok)
    
    dlg._coord = coord 
    return dlg