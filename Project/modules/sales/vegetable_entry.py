import os
from functools import partial
from typing import List, Dict, Optional

from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QTableWidget, QPushButton, QLabel, QLineEdit
from PyQt5.QtCore import Qt

# Centralized Utilities
from modules.ui_utils.focus_utils import FieldCoordinator
from modules.wrappers import settings as app_settings
from modules.db_operation import get_product_info, get_product_full
from modules.db_operation.database import PRODUCT_CACHE
from modules.ui_utils import ui_feedback, input_validation
from modules.table.unit_helpers import canonicalize_unit
from modules.table.table_operations import (
    setup_sales_table, get_sales_data, set_table_rows, 
    bind_status_label, bind_next_focus_widget
)

def weight_simulation() -> int:
    return 600

def open_vegetable_entry_dialog(parent):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    veg_ui = os.path.join(BASE_DIR, 'ui', 'vegetable_entry.ui')
    
    try:
        dlg = uic.loadUi(veg_ui)
        coord = FieldCoordinator(dlg)
        dlg._coord = coord 
    except Exception as e:
        print(f'Failed to load UI: {e}'); return None
    
    for btn in dlg.findChildren(QPushButton):
        btn.setAutoDefault(False)
        btn.setDefault(False)

    dlg.setParent(parent)
    dlg.setModal(True)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)

    # Styling
    qss_path = os.path.join(BASE_DIR, 'assets', 'menu.qss')
    if os.path.exists(qss_path):
        with open(qss_path, 'r', encoding='utf-8') as f: dlg.setStyleSheet(f.read())

    vtable = dlg.findChild(QTableWidget, 'vegEntryTable')
    status_lbl = dlg.findChild(QLabel, 'vegEStatusLabel')
    ok_btn = dlg.findChild(QPushButton, 'btnVegEOk')
    cancel_btn = dlg.findChild(QPushButton, 'btnVegECancel')
    close_btn = dlg.findChild(QPushButton, 'customCloseBtn')

    if vtable:
        setup_sales_table(vtable)
        bind_status_label(vtable, status_lbl)
        if ok_btn: bind_next_focus_widget(vtable, ok_btn)
        vtable.verticalHeader().setDefaultSectionSize(48)

    # Link OK button to coordinator so Enter clicks it when focused
    if ok_btn:
        coord.add_link(ok_btn, next_focus=None) # Registers it for the eventFilter

    # Initialize Veg Buttons
    for i in range(1, 17):
        btn = dlg.findChild(QPushButton, f'vegEButton{i}')
        if not btn: continue
        
        veg_code = f'Veg{i:02d}'
        found, product_name, unit_price, _ = get_product_info(veg_code)
        
        if found:
            btn.setText(product_name); btn.setEnabled(True)
            btn.setFocusPolicy(Qt.StrongFocus); btn.setProperty('state', 'active')
            _, details = get_product_full(veg_code)
            unit = details.get('unit', 'Each') if details else 'Each'
            btn.clicked.connect(partial(_handle_vegetable_button_click, dlg, status_lbl, vtable, veg_code, product_name, unit_price, unit))
        else:
            btn.setText('Not Used'); btn.setEnabled(False)
            btn.setFocusPolicy(Qt.NoFocus); btn.setProperty('state', 'unused')
        
        btn.style().unpolish(btn); btn.style().polish(btn)

    if ok_btn: ok_btn.clicked.connect(lambda: _handle_ok_all(dlg, vtable, status_lbl))
    if cancel_btn: cancel_btn.clicked.connect(dlg.reject)
    if close_btn: close_btn.clicked.connect(dlg.reject)

    return dlg

def _handle_vegetable_button_click(dlg, msg_label, vtable, code, name, price, unit):
    unit_canon = canonicalize_unit(unit)
    
    if unit_canon == 'Kg':
        ui_feedback.set_status_label(msg_label, f"Place {name} on scale...", ok=True)
        try:
            w_grams = weight_simulation()
            if w_grams <= 0:
                ui_feedback.set_status_label(msg_label, "Error: Invalid weight", ok=False); return
            
            w_kg = w_grams / 1000.0
            _add_vegetable_row(dlg, vtable, name, w_kg, price, editable=False)
            ui_feedback.set_status_label(msg_label, f"Added {name}: {w_grams}g", ok=True)
        except Exception as e:
            ui_feedback.set_status_label(msg_label, f"Scale Error: {e}", ok=False)
    else:
        _add_vegetable_row(dlg, vtable, name, 1.0, price, editable=True)
        ui_feedback.set_status_label(msg_label, f"Added {name}", ok=True)

    # Shift focus to OK
    ok_btn = dlg.findChild(QPushButton, 'btnVegEOk')
    if ok_btn: ok_btn.setFocus()

def _add_vegetable_row(dlg, vtable, name, quantity, price, editable):
    current_data = get_sales_data(vtable)
    target_unit = canonicalize_unit("Kg" if not editable else "Each")
    
    found = False
    for row in current_data:
        if (row['product_name'].strip().lower() == name.strip().lower() and row['unit'] == target_unit):
            row['quantity'] += (1.0 if editable else quantity)
            found = True; break
            
    if not found:
        current_data.append({'product_name': name, 'quantity': quantity, 'unit_price': price, 'unit': target_unit, 'editable': editable})
    
    set_table_rows(vtable, current_data)

    # CRITICAL: Register the new table editors with the Coordinator
    ok_btn = dlg.findChild(QPushButton, 'btnVegEOk')
    for r in range(vtable.rowCount()):
        qty_container = vtable.cellWidget(r, 2)
        if qty_container:
            editor = qty_container.findChild(QLineEdit, 'qtyInput')
            if editor and editor not in dlg._coord.links:
                # Link editor to OK button for focus jump
                dlg._coord.add_link(editor, next_focus=ok_btn)

def _handle_ok_all(dlg, vtable, status_lbl):
    if not vtable or vtable.rowCount() == 0:
        dlg.reject(); return

    try:
        scraped_rows = get_sales_data(vtable)
        rows_to_transfer = []
        for row in scraped_rows:
            if row['quantity'] <= 0: raise ValueError(f"Quantity for '{row['product_name']}' must be > 0")
            code = next((k for k, v in PRODUCT_CACHE.items() if v[0] == row['product_name']), row['product_name'])
            rows_to_transfer.append({'product_code': code, 'product_name': row['product_name'], 'quantity': row['quantity'], 'unit_price': row['unit_price'], 'unit': row['unit'], 'editable': row['editable']})

        dlg.vegetable_rows = rows_to_transfer
        dlg.accept()
    except ValueError as e:
        ui_feedback.set_status_label(status_lbl, str(e), ok=False)