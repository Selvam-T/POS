# --- Vegetable Entry Dialog Controller ---
"""Vegetable Entry Dialog - allows selecting vegetables from a 4x4 grid.

Each vegetable button triggers weighing (for KG items) or increments count (for EACH items).
The dialog maintains an internal table (vegEntryTable) that accumulates selections.
Duplicate detection: uses shared table_operations functions (find_product_in_table, increment_row_quantity)
for consistent duplicate handling across barcode scanning and vegetable entry.
On OK, all rows are transferred to the main sales table with duplicate merging.
"""
import os
from typing import List, Dict, Optional
from PyQt5 import uic
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QTableWidget, QPushButton, QLabel, QHeaderView, QLineEdit, QWidget
from PyQt5.QtCore import Qt
from functools import partial

from modules.wrappers import settings as app_settings
from modules.db_operation import get_product_info, get_product_full
from modules.db_operation.database import PRODUCT_CACHE
from modules.table import setup_sales_table
from modules.table import find_product_in_table, increment_row_quantity
from modules.table.table_operations import set_table_rows


def weight_simulation() -> int:
    """Simulate weighing scale reading.
    
    Returns:
        Weight in grams (simulated as 600g)
    """
    return 600


def open_vegetable_entry_dialog(parent):
    """Open the Add Vegetable panel as a modal dialog.
    
    DialogWrapper handles: overlay, sizing, centering, scanner blocking, cleanup, and focus restoration.
    This function only creates and returns the QDialog.
    
    Args:
        parent: Main window instance
    
    Returns:
        QDialog instance ready for DialogWrapper.open_dialog_scanner_blocked() to execute
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

    # Configure the vegetable table using shared setup function
    try:
        vtable = dlg.findChild(QTableWidget, 'vegEntryTable')
        if vtable is not None:
            setup_sales_table(vtable)
            
            # Additional vegetable table settings
            vtable.setEditTriggers(QTableWidget.NoEditTriggers)
            vtable.setSelectionBehavior(QTableWidget.SelectRows)
            vtable.setSelectionMode(QTableWidget.SingleSelection)
            vtable.verticalHeader().setDefaultSectionSize(48)
    except Exception as e:
        print('Vegetable table setup failed:', e)

    # Wire keypad buttons and set up vegetable button logic
    try:
        msg = dlg.findChild(QLabel, 'vegEntryMessage2')
        vtable = dlg.findChild(QTableWidget, 'vegEntryTable')
        
        # Load vegetable products and configure buttons
        for i, name in enumerate((
            'btnVeg1','btnVeg2','btnVeg3','btnVeg4',
            'btnVeg5','btnVeg6','btnVeg7','btnVeg8',
            'btnVeg9','btnVeg10','btnVeg11','btnVeg12',
            'btnVeg13','btnVeg14','btnVeg15','btnVeg16',
        ), start=1):
            btn = dlg.findChild(QPushButton, name)
            if btn is None:
                continue
            
            # Load product info for VegXX code
            veg_code = f'Veg{i:02d}'
            found, product_name, unit_price, _ = get_product_info(veg_code)
            
            if found:
                # Product exists - set button label and enable
                btn.setText(product_name)
                btn.setEnabled(True)
                btn.setProperty('unused', False)
                
                # Get full product details for unit
                _, details = get_product_full(veg_code)
                unit = details.get('unit', 'Each') if details else 'Each'
                
                # Connect button click handler using partial to avoid lambda closure issues
                btn.clicked.connect(
                    partial(_handle_vegetable_button_click, dlg, msg, vtable, veg_code, product_name, unit_price, unit)
                )
            else:
                # Product doesn't exist - disable button
                btn.setText('Not Used')
                btn.setEnabled(False)
                btn.setProperty('unused', True)
            
            # Apply styling
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Wire OK/CANCEL buttons
        ok_btn = dlg.findChild(QPushButton, 'btnVegOk')
        cancel_btn = dlg.findChild(QPushButton, 'btnVegCancel')
        if ok_btn is not None:
            ok_btn.clicked.connect(lambda: _handle_ok_all(dlg, vtable))
        if cancel_btn is not None:
            cancel_btn.clicked.connect(lambda: dlg.reject())
    except Exception as e:
        print('Vegetable keypad wiring failed:', e)

    # Return QDialog for DialogWrapper to execute
    return dlg


def _handle_vegetable_button_click(dlg: QDialog, msg_label: Optional[QLabel], 
                                   vtable: Optional[QTableWidget], 
                                   product_code: str, product_name: str, 
                                   unit_price: float, unit: str) -> None:
    """Handle vegetable button click - add product to table based on unit type.
    
    Args:
        dlg: Dialog instance
        msg_label: Message label for user feedback
        vtable: Vegetable entry table
        product_code: Product code (e.g., Veg01)
        product_name: Product display name
        unit_price: Unit price
        unit: Unit type ('KG' or 'EA')
    """
    if vtable is None:
        return
    
    from modules.table.unit_helpers import canonicalize_unit
    unit_canon = canonicalize_unit(unit)
    if unit_canon == 'Kg':
        # KG item - need weighing scale input (simulated for now)
        if msg_label:
            msg_label.setText(f"Place {product_name} on the scale ...")
            msg_label.setStyleSheet("color: green;")
        
        # Read from weighing scale simulation
        try:
            weight_grams = weight_simulation()
        except Exception as e:
            if msg_label:
                msg_label.setText(f"Error reading scale: {e}")
                msg_label.setStyleSheet("color: red;")
            return
        
        if weight_grams <= 0:
            if msg_label:
                msg_label.setText("Error: Invalid weight from scale")
                msg_label.setStyleSheet("color: red;")
            return
        
        # Convert grams to kg for calculation
        weight_kg = weight_grams / 1000.0
        total = weight_kg * unit_price
        
        # Add row with read-only quantity (kg value stored, unit shown in unit column)
        _add_vegetable_row(vtable, product_code, product_name, weight_kg, unit_price, 
                          editable=False)
        
        if msg_label:
            # Show user-friendly weight in message
            if weight_grams < 1000:
                display_msg = f"{weight_grams} g"
            else:
                display_msg = f"{weight_kg:.2f} kg"
            msg_label.setText(f"Added {product_name}: {display_msg}")
            msg_label.setStyleSheet("color: green;")
    
    else:  # unit == 'Each'
        # EACH item - no weighing needed
        quantity = 1
        total = quantity * unit_price
        
        # Add row with editable quantity
        _add_vegetable_row(vtable, product_code, product_name, quantity, unit_price, 
                          editable=True)
        
        if msg_label:
            msg_label.setText(f"Added {product_name}")
            msg_label.setStyleSheet("color: green;")


def _add_vegetable_row(vtable: QTableWidget, product_code: str, product_name: str, 
                      quantity: float, unit_price: float, editable: bool = True) -> None:
    """Add a vegetable row to the vegEntryTable, or update if duplicate.
    
    Uses shared table_operations functions for consistent duplicate detection.
    
    If product already exists:
    - EACH items (editable): Increment quantity by 1
    - KG items (read-only): Add new weight to existing weight
    
    Args:
        vtable: Vegetable entry table
        product_code: Product code (e.g., 'Veg01')
        product_name: Product display name
        quantity: Numeric quantity (kg for weight items, count for EACH)
        unit_price: Unit price
        editable: Whether quantity is editable (True=EACH, False=KG)
    """
    from modules.table.unit_helpers import canonicalize_unit
    # Get canonical unit from product code (from cache)
    from modules.db_operation import get_product_info
    found, _, _, unit = get_product_info(product_code)
    unit_canon = canonicalize_unit(unit)
    # Check for duplicate using shared function (searches by product code and canonical unit)
    existing_row = find_product_in_table(vtable, product_code, unit_canon)
    
    if existing_row is not None:
        # Product exists - check if it's editable (EACH) or read-only (KG)
        qty_container = vtable.cellWidget(existing_row, 2)
        if qty_container:
            editor = qty_container.findChild(QtWidgets.QLineEdit, 'qtyInput')
            if editor:
                if not editor.isReadOnly():
                    # EACH item - increment by 1 (shared function handles this)
                    increment_row_quantity(vtable, existing_row)
                else:
                    # KG item - add weights together
                    numeric_val = editor.property('numeric_value')
                    if numeric_val is not None:
                        try:
                            current_qty = float(numeric_val)
                        except (ValueError, TypeError):
                            current_qty = 0.0
                    else:
                        current_qty = 0.0
                    
                    new_qty = current_qty + quantity
                    editor.setProperty('numeric_value', new_qty)
                    
                    # Update display
                    weight_grams = int(new_qty * 1000)
                    if weight_grams < 1000:
                        editor.setText(str(weight_grams))
                    else:
                        editor.setText(f"{new_qty:.2f}")
                    
                    # Update unit column
                    unit_item = vtable.item(existing_row, 3)
                    if unit_item:
                        unit_item.setText('g' if weight_grams < 1000 else 'kg')
                    
                    # Recalculate total
                    from modules.table.table_operations import recalc_row_total
                    recalc_row_total(vtable, existing_row)
        # Always return when duplicate found, even if update failed
        return
    
    # No duplicate - get current rows and add new one
    current_rows = []
    from modules.table.table_operations import display_unit
    for r in range(vtable.rowCount()):
        product_item = vtable.item(r, 1)
        if product_item is None:
            continue
        name = product_item.text()
        # Always resolve product_code for this row (from hidden property or lookup)
        found_code = None
        for code, (n, _, _) in PRODUCT_CACHE.items():
            if n == name:
                found_code = code
                break
        lookup_code = found_code if found_code else name
        # Always resolve canonical unit from product_code
        _, _, _, unit = get_product_info(lookup_code)
        # Canonicalize unit for storage
        unit_canon = 'Each' if unit and unit.upper() == 'EACH' else ('Kg' if unit and unit.upper() == 'KG' else unit)
        # Get quantity and editable state
        qty_container = vtable.cellWidget(r, 2)
        qty = 1.0
        row_editable = True
        if qty_container is not None:
            editor = qty_container.findChild(QtWidgets.QLineEdit, 'qtyInput')
            if editor is not None:
                row_editable = not editor.isReadOnly()
                numeric_val = editor.property('numeric_value')
                if numeric_val is not None:
                    try:
                        qty = float(numeric_val)
                    except (ValueError, TypeError):
                        qty = 1.0
                else:
                    try:
                        qty = float(editor.text()) if editor.text() else 1.0
                    except ValueError:
                        qty = 1.0
        # Get unit price from column 4
        price_item = vtable.item(r, 4)
        price = 0.0
        if price_item is not None:
            try:
                price = float(price_item.text())
            except ValueError:
                price = 0.0
        row_data = {
            'product_code': lookup_code,
            'product_name': name,
            'quantity': qty,
            'unit': unit_canon,
            'unit_price': price
        }
        current_rows.append(row_data)
    # Always resolve canonical unit for the new row using product_code
    _, _, _, unit_for_new = get_product_info(product_code)
    unit_for_new_canon = 'Each' if unit_for_new and unit_for_new.upper() == 'EACH' else ('Kg' if unit_for_new and unit_for_new.upper() == 'KG' else unit_for_new)
    new_row = {
        'product_code': product_code,
        'product_name': product_name,
        'quantity': quantity,
        'unit': unit_for_new_canon,
        'unit_price': unit_price
    }
    current_rows.append(new_row)
    # Rebuild table with mixed editable states (pass product_name as 'product' for display, and correct unit display)
    display_rows = [
        {
            'product': row['product_name'],
            'quantity': row['quantity'],
            'unit_price': row['unit_price'],
            'unit': display_unit(row['unit'], row['quantity']),
            'editable': (row['unit'].upper() != 'KG')
        }
        for row in current_rows
    ]
    set_table_rows(vtable, display_rows)


def _handle_ok_all(dlg: QDialog, vtable: Optional[QTableWidget]) -> None:
    """Handle OK ALL button - store vegetable rows data and close dialog.
    
    The rows will be transferred to main salesTable by the caller.
    """
    if vtable is None:
        dlg.reject()
        return
    
    # Extract all rows from vegEntryTable
    rows_to_transfer = []
    for r in range(vtable.rowCount()):
        product_item = vtable.item(r, 1)
        if product_item is None:
            continue
        name = product_item.text()
        # Find product code by matching name in PRODUCT_CACHE
        from modules.db_operation.database import PRODUCT_CACHE
        code = None
        for k, v in PRODUCT_CACHE.items():
            if v[0] == name:
                code = k
                break
        if code is None:
            code = name  # fallback, but should not happen if cache is correct
        cache_val = PRODUCT_CACHE.get(code)
        print(f"[vegetable_entry] PRODUCT_CACHE lookup for name '{name}' (code '{code}'): {cache_val}")
        found, _, _, unit = get_product_info(code)
        print(f"[vegetable_entry] get_product_info('{code}') -> found={found}, unit={unit}")
        qty_container = vtable.cellWidget(r, 2)
        qty = 1.0
        if qty_container is not None:
            editor = qty_container.findChild(QtWidgets.QLineEdit, 'qtyInput')
            if editor is not None:
                numeric_val = editor.property('numeric_value')
                if numeric_val is not None:
                    try:
                        qty = float(numeric_val)
                    except (ValueError, TypeError):
                        qty = 1.0
                else:
                    try:
                        qty = float(editor.text()) if editor.text() else 1.0
                    except ValueError:
                        qty = 1.0
        price_item = vtable.item(r, 4)
        price = 0.0
        if price_item is not None:
            try:
                price = float(price_item.text())
            except ValueError:
                price = 0.0
        row_data = {
            'product': name,  # always use product name for display
            'product_code': code,
            'product_name': name,
            'quantity': qty,
            'unit_price': price,
            'unit': unit,
            'editable': (unit.upper() != 'KG')
        }
        # Debug print removed
        rows_to_transfer.append(row_data)
    # Store rows on dialog object for retrieval by caller
    # Debug print removed
    dlg.vegetable_rows = rows_to_transfer
    dlg.accept()


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

