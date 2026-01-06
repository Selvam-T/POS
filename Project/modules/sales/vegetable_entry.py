import os
from typing import List, Dict, Optional
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QTableWidget, QPushButton, QLabel
from PyQt5.QtCore import Qt
from functools import partial

# Centralized Utilities
from modules.wrappers import settings as app_settings
from modules.db_operation import get_product_info, get_product_full
from modules.db_operation.database import PRODUCT_CACHE
from modules.ui_utils import ui_feedback, input_validation
from modules.table.unit_helpers import canonicalize_unit
from modules.table.table_operations import (
    setup_sales_table, 
    get_sales_data, 
    set_table_rows, 
    bind_status_label
)

def weight_simulation() -> int:
    """Simulates scale reading in grams (600g)."""
    return 600

def open_vegetable_entry_dialog(parent):
    """Initializes and returns the Vegetable Entry Dialog."""
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    UI_DIR = os.path.join(BASE_DIR, 'ui')
    veg_ui = os.path.join(UI_DIR, 'vegetable_entry.ui')
    
    try:
        dlg = uic.loadUi(veg_ui)
    except Exception as e:
        print(f'Failed to load UI: {e}')
        return None
    
    # 1. PREVENT GHOST CLICKS: Strip AutoDefault from ALL buttons.
    # This stops the 'Enter' key from triggering random buttons.
    for btn in dlg.findChildren(QPushButton):
        btn.setAutoDefault(False)
        btn.setDefault(False)

    dlg.setParent(parent)
    dlg.setModal(True)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)

    # 2. Apply Styling
    try:
        qss_path = os.path.join(BASE_DIR, 'assets', 'menu.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r', encoding='utf-8') as f:
                dlg.setStyleSheet(f.read())
    except Exception as e:
        print(f"QSS Load Error: {e}")

    # 3. Initialize Widgets
    vtable = dlg.findChild(QTableWidget, 'vegEntryTable')
    status_lbl = dlg.findChild(QLabel, 'vegEStatusLabel')
    
    if vtable:
        setup_sales_table(vtable)
        # Bind the status label so table errors show up here
        bind_status_label(vtable, status_lbl) 
        vtable.verticalHeader().setDefaultSectionSize(48)

    # 4. Initialize Vegetable Buttons (Veg01 - Veg16)
    for i in range(1, 17):
        btn = dlg.findChild(QPushButton, f'vegEButton{i}')
        if not btn: continue
        
        veg_code = f'Veg{i:02d}'
        found, product_name, unit_price, _ = get_product_info(veg_code)
        
        if found:
            btn.setText(product_name)
            btn.setEnabled(True)
            btn.setFocusPolicy(Qt.StrongFocus)
            btn.setProperty('state', 'active') # Matches menu.qss selector
            
            _, details = get_product_full(veg_code)
            unit = details.get('unit', 'Each') if details else 'Each'
            
            btn.clicked.connect(partial(
                _handle_vegetable_button_click, status_lbl, vtable, veg_code, product_name, unit_price, unit
            ))
        else:
            btn.setText('Not Used')
            btn.setEnabled(False)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setProperty('state', 'unused') # Matches menu.qss selector
        
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    # 5. Wire Action Buttons
    ok_btn = dlg.findChild(QPushButton, 'btnVegEOk')
    cancel_btn = dlg.findChild(QPushButton, 'btnVegECancel')
    close_btn = dlg.findChild(QPushButton, 'customCloseBtn')

    if ok_btn:
        ok_btn.clicked.connect(lambda: _handle_ok_all(dlg, vtable, status_lbl))
    if cancel_btn:
        cancel_btn.clicked.connect(dlg.reject)
    if close_btn:
        close_btn.clicked.connect(dlg.reject)

    return dlg

def _handle_vegetable_button_click(msg_label, vtable, code, name, price, unit):
    """Logic for when a vegetable button is clicked."""
    unit_canon = canonicalize_unit(unit)
    
    if unit_canon == 'Kg':
        ui_feedback.set_status_label(msg_label, f"Place {name} on scale...", ok=True)
        try:
            weight_grams = weight_simulation()
            weight_kg = weight_grams / 1000.0
            
            # Centralized Weight Validation (0.005kg to 25.0kg)
            ok, err = input_validation.validate_quantity(weight_kg, unit_type='kg')
            if not ok:
                ui_feedback.set_status_label(msg_label, err, ok=False)
                return
            
            _add_vegetable_row(vtable, name, weight_kg, price, editable=False)
            
            display_msg = f"{weight_grams}g" if weight_grams < 1000 else f"{weight_kg:.2f}kg"
            ui_feedback.set_status_label(msg_label, f"Added {name}: {display_msg}", ok=True)
        except Exception as e:
            ui_feedback.set_status_label(msg_label, f"Scale Error: {e}", ok=False)
    else:
        # 'Each' item: default quantity 1.0
        _add_vegetable_row(vtable, name, 1.0, price, editable=True)
        ui_feedback.set_status_label(msg_label, f"Added {name}", ok=True)

def _add_vegetable_row(vtable, name, quantity, price, editable):
    """Updates table: merges duplicates or adds new row."""
    current_data = get_sales_data(vtable)
    target_unit = canonicalize_unit("Kg" if not editable else "Each")
    
    found = False
    for row in current_data:
        if (row['product_name'].strip().lower() == name.strip().lower() and 
            row['unit'] == target_unit):
            # If EACH, increment by 1. If KG, add the new weight.
            row['quantity'] += (1.0 if editable else quantity)
            found = True
            break
            
    if not found:
        current_data.append({
            'product_name': name,
            'quantity': quantity,
            'unit_price': price,
            'unit': target_unit,
            'editable': editable
        })
    set_table_rows(vtable, current_data)

def _handle_ok_all(dlg, vtable, status_lbl):
    """Gateway to dlg.accept(). Blocks closure if any row is invalid (e.g. 0 or empty)."""
    if not vtable or vtable.rowCount() == 0:
        dlg.reject()
        return

    try:
        # SINGLE UI READ: Fetch data via table_operations (handles validation internally)
        scraped_rows = get_sales_data(vtable)
        
        rows_to_transfer = []
        for row in scraped_rows:
            name = row['product_name']
            
            # Final zero check (get_sales_data returns 0.0 for empty/invalid fields)
            if row['quantity'] <= 0:
                raise ValueError(f"Quantity for '{name}' must be greater than 0")

            # Resolve Code (Name -> Code)
            code = next((k for k, v in PRODUCT_CACHE.items() if v[0] == name), name)

            rows_to_transfer.append({
                'product_code': code,
                'product_name': name,
                'quantity': row['quantity'],
                'unit_price': row['unit_price'],
                'unit': row['unit'],
                'editable': row['editable']
            })

        # Success: Store data and close dialog
        dlg.vegetable_rows = rows_to_transfer
        dlg.accept()

    except ValueError as e:
        # Failure: Show error, keep dialog open
        ui_feedback.set_status_label(status_lbl, str(e), ok=False)
    except Exception as e:
        ui_feedback.set_status_label(status_lbl, f"System Error: {str(e)}", ok=False)