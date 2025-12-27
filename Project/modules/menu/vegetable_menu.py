"""Vegetable Management dialog controller for POS system.

Manages 16 vegetable slots (Veg01-Veg16) with database integration.
Pattern matches other menu controllers (admin_menu, reports_menu, product_menu).
"""
import os
from PyQt5 import uic
from PyQt5.QtCore import Qt, QDateTime, QTimer
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QLineEdit, 
    QComboBox, QLabel
)

from modules.db_operation import (
    get_product_info, get_product_full, add_product, 
    delete_product, refresh_product_cache
)
from modules.db_operation.database import DB_PATH

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
QSS_PATH = os.path.join(ASSETS_DIR, 'menu.qss')

# Vegetable slot count
VEG_SLOTS = 16


def open_vegetable_menu_dialog(host_window):
    """Open Vegetable Management dialog as a modal.
    
    DialogWrapper handles: overlay, sizing, centering, scanner blocking, cleanup, and focus restoration.
    This function only creates and returns the QDialog.
    
    Args:
        host_window: Main window instance
    
    Returns:
        QDialog instance ready for DialogWrapper.open_dialog_scanner_blocked() to execute
    """
    ui_path = os.path.join(UI_DIR, 'vegetable_menu.ui')
    if not os.path.exists(ui_path):
        print(f'vegetable_menu.ui not found at {ui_path}')
        return None

    try:
        content = uic.loadUi(ui_path)
    except Exception as e:
        print(f'Failed to load vegetable_menu.ui: {e}')
        return None

    # Wrap in QDialog if needed
    if isinstance(content, QDialog):
        dlg = content
    else:
        dlg = QDialog(host_window)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(content)

    # Frameless + modal
    dlg.setParent(host_window)
    dlg.setModal(True)
    dlg.setWindowModality(Qt.ApplicationModal)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)

    # Apply stylesheet
    if os.path.exists(QSS_PATH):
        try:
            with open(QSS_PATH, 'r', encoding='utf-8') as f:
                dlg.setStyleSheet(f.read())
        except Exception as e:
            print(f'Failed to load menu.qss: {e}')

    # Find widgets
    combo_vegetable = dlg.findChild(QComboBox, 'vegMChooseComboBox')
    input_product_code = dlg.findChild(QLineEdit, 'vegMProductCodeLineEdit')
    input_product_name = dlg.findChild(QLineEdit, 'vegMProductNameLineEdit')
    input_selling_price = dlg.findChild(QLineEdit, 'vegMSellingPriceLineEdit')
    combo_unit = dlg.findChild(QComboBox, 'vegMUnitComboBox')
    input_supplier = dlg.findChild(QLineEdit, 'vegMSupplierLineEdit')
    input_cost_price = dlg.findChild(QLineEdit, 'vegMCostPriceLineEdit')
    lbl_error = dlg.findChild(QLabel, 'vegMStatusLabel')
    btn_add = dlg.findChild(QPushButton, 'btnVegmenuOk')
    btn_remove = dlg.findChild(QPushButton, 'btnVegmenuDel')
    btn_cancel = dlg.findChild(QPushButton, 'btnVegmenuCancel')
    custom_close_btn = dlg.findChild(QPushButton, 'customCloseBtn')

    # Make product code non-focusable and read-only
    if input_product_code is not None:
        input_product_code.setFocusPolicy(Qt.NoFocus)
        input_product_code.setReadOnly(True)

    # Helper: Show error message
    def show_error(msg: str):
        if lbl_error is not None:
            lbl_error.setText(msg)
            lbl_error.setStyleSheet('color: red;')

    # Helper: Clear error message
    def clear_error():
        if lbl_error is not None:
            lbl_error.clear()

    # Populate combobox from cache
    if combo_vegetable is not None:
        combo_vegetable.clear()
        # Add placeholder item at top
        combo_vegetable.addItem('Select Vegetable to update', userData=None)
        for i in range(1, VEG_SLOTS + 1):
            code = f'Veg{i:02d}'
            found, name, price, _ = get_product_info(code)
            if found:
                combo_vegetable.addItem(name, userData=code)
            else:
                placeholder = f'VEGETABLE {i}'
                combo_vegetable.addItem(placeholder, userData=code)

    # Helper: Load selected vegetable data into form
    def load_vegetable_data(index):
        """Load data for selected vegetable slot into input fields."""
        clear_error()
        
        if combo_vegetable is None or index < 0:
            return
        
        selected_code = combo_vegetable.itemData(index)
        
        # Clear fields and remove focus if placeholder selected
        if selected_code is None:
            if input_product_code is not None:
                input_product_code.clear()
            if input_product_name is not None:
                input_product_name.clear()
                input_product_name.clearFocus()
            if input_selling_price is not None:
                input_selling_price.clear()
                input_selling_price.clearFocus()
            if combo_unit is not None:
                combo_unit.setCurrentIndex(0)
                combo_unit.clearFocus()
            if input_supplier is not None:
                input_supplier.clear()
                input_supplier.clearFocus()
            if input_cost_price is not None:
                input_cost_price.clear()
                input_cost_price.clearFocus()
            # Set focus to combobox itself
            if combo_vegetable is not None:
                combo_vegetable.setFocus()
            return
        
        # Display product code
        if input_product_code is not None:
            input_product_code.setText(selected_code)
        
        # Check if vegetable exists in database
        found, details = get_product_full(selected_code)
        
        if found and details.get('name'):
            # Populate fields with existing data
            if input_product_name is not None:
                input_product_name.setText(details.get('name', ''))
            if input_selling_price is not None:
                input_selling_price.setText(str(details.get('price', '')))
            if combo_unit is not None:
                unit = details.get('unit', '').strip().upper()  # Normalize to uppercase
                # Default to EACH if empty
                if not unit:
                    unit = 'EACH'
                idx = combo_unit.findText(unit, Qt.MatchFixedString)
                if idx >= 0:
                    combo_unit.setCurrentIndex(idx)
            if input_supplier is not None:
                input_supplier.setText(details.get('supplier', ''))
            if input_cost_price is not None:
                cost = details.get('cost', None)
                input_cost_price.setText(str(cost) if cost else '')
        else:
            # Clear fields for new entry
            if input_product_name is not None:
                input_product_name.clear()
            if input_selling_price is not None:
                input_selling_price.clear()
            if combo_unit is not None:
                combo_unit.setCurrentIndex(0)
            if input_supplier is not None:
                input_supplier.clear()
            if input_cost_price is not None:
                input_cost_price.clear()
        
        # Set focus to product name field for immediate typing
        if input_product_name is not None:
            QTimer.singleShot(0, lambda: input_product_name.setFocus())
    
    # Connect combobox selection change to load data
    if combo_vegetable is not None:
        combo_vegetable.currentIndexChanged.connect(load_vegetable_data)
        # Set to placeholder (index 0) and focus on combobox
        if combo_vegetable.count() > 0:
            combo_vegetable.setCurrentIndex(0)
            combo_vegetable.setFocus()

    # Helper: Validate mandatory fields
    def validate_inputs():
        # Validation order: Product name → Unit → Selling price
        if input_product_name is None or not input_product_name.text().strip():
            show_error('Error: Name is required')
            return False
        if combo_unit is None or combo_unit.currentIndex() <= 0:
            show_error('Error: Unit is required')
            return False
        if input_selling_price is None or not input_selling_price.text().strip():
            show_error('Error: Selling price is required')
            return False
        try:
            price = float(input_selling_price.text().strip())
            if price <= 0:
                show_error('Error: Valid selling price is required')
                return False
        except ValueError:
            show_error('Error: Invalid selling price format')
            return False
        clear_error()
        return True

    # Helper: Get current vegetables from cache
    def get_current_vegetables():
        """Returns list of dicts with vegetable data from cache."""
        vegetables = []
        for i in range(1, VEG_SLOTS + 1):
            code = f'Veg{i:02d}'
            found, details = get_product_full(code)
            if found and details.get('name'):
                vegetables.append({
                    'code': code,
                    'name': details['name'],
                    'price': details.get('price', 0.0),
                    'category': details.get('category', 'Vegetable'),
                    'supplier': details.get('supplier', ''),
                    'cost': details.get('cost', None),
                    'unit': details.get('unit', 'KG'),
                })
        return vegetables

    # Helper: Sort and reassign vegetables to database
    def sort_and_update_database(vegetables_list):
        """Sort vegetables A-Z, batch update database and cache."""
        # Sort alphabetically (case-insensitive)
        sorted_vegs = sorted(vegetables_list, key=lambda v: v['name'].casefold())
        
        # Batch delete all Veg01-Veg16
        for i in range(1, VEG_SLOTS + 1):
            delete_product(f'Veg{i:02d}')
        
        # Insert sorted vegetables sequentially
        for i, veg in enumerate(sorted_vegs, start=1):
            now_str = QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss')
            add_product(
                product_code=f'Veg{i:02d}',
                name=veg['name'],
                selling_price=veg['price'],
                category=veg.get('category', 'Vegetable'),
                supplier=veg.get('supplier'),
                cost_price=veg.get('cost'),
                unit=veg.get('unit', 'KG'),
                last_updated=now_str
            )
        
        # Refresh cache
        refresh_product_cache()

    # ADD button handler
    def on_add_clicked():
        clear_error()
        
        # Validate inputs
        if not validate_inputs():
            return
        
        # Get selected product code
        if combo_vegetable is None:
            show_error('Error: No vegetable selected')
            return
        
        selected_code = combo_vegetable.currentData()
        if not selected_code:
            show_error('Error: Invalid vegetable selection')
            return
        
        # Gather input values
        name = input_product_name.text().strip()
        try:
            price = float(input_selling_price.text().strip())
        except ValueError:
            show_error('Error: Invalid selling price')
            return
        
        unit = combo_unit.currentText().strip().upper() if combo_unit else 'EACH'
        # Ensure valid unit
        if unit not in ['KG', 'EACH']:
            unit = 'EACH'
        category = 'Vegetable'
        supplier = input_supplier.text().strip() if input_supplier and input_supplier.text().strip() else None
        
        cost = None
        if input_cost_price and input_cost_price.text().strip():
            try:
                cost = float(input_cost_price.text().strip())
            except ValueError:
                pass
        
        # Get current vegetables from cache
        vegetables = get_current_vegetables()
        
        # Check if this slot already has a vegetable and update, or add new
        existing = None
        for i, veg in enumerate(vegetables):
            if veg['code'] == selected_code:
                existing = i
                break
        
        new_veg = {
            'code': selected_code,
            'name': name,
            'price': price,
            'category': category,
            'supplier': supplier,
            'cost': cost,
            'unit': unit
        }
        
        if existing is not None:
            vegetables[existing] = new_veg
        else:
            vegetables.append(new_veg)
        
        # Sort and update database
        try:
            sort_and_update_database(vegetables)
            dlg.accept()
        except Exception as e:
            show_error(f'Error: {e}')

    # REMOVE button handler
    def on_remove_clicked():
        clear_error()
        
        # Get selected product code
        if combo_vegetable is None:
            show_error('Error: No vegetable selected')
            return
        
        selected_code = combo_vegetable.currentData()
        if not selected_code:
            show_error('Error: Invalid vegetable selection')
            return
        
        # Check if vegetable exists in cache
        found, name, price, _ = get_product_info(selected_code)
        if not found:
            # Extract placeholder number for error message
            placeholder_num = selected_code.replace('Veg', '').lstrip('0')
            show_error(f'Error: No vegetable added for VEGETABLE {placeholder_num}')
            return
        
        # Get current vegetables
        vegetables = get_current_vegetables()
        
        # Remove the selected vegetable
        vegetables = [v for v in vegetables if v['code'] != selected_code]
        
        # Sort and update database
        try:
            sort_and_update_database(vegetables)
            dlg.accept()
        except Exception as e:
            show_error(f'Error: {e}')

    # CANCEL button handler
    def on_cancel_clicked():
        dlg.reject()

    # Wire buttons
    if btn_add is not None:
        btn_add.clicked.connect(on_add_clicked)
    if btn_remove is not None:
        btn_remove.clicked.connect(on_remove_clicked)
    if btn_cancel is not None:
        btn_cancel.clicked.connect(on_cancel_clicked)
    if custom_close_btn is not None:
        custom_close_btn.clicked.connect(on_cancel_clicked)

    return dlg

