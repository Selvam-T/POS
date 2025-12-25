"""Product Management dialog logic extracted from main.py.

Provides a function open_product_panel(main_window, initial_mode=None, initial_code=None)
that encapsulates all behavior for ADD / REMOVE / UPDATE tabs.

Rationale for extraction:
- Keeps main window lean
- Enables future unit testing of product panel logic
- Allows dedicated styling via product_menu.qss

Assumptions:
- main_window supplies method: _refocus_sales_table and attributes: sales_table, statusbar
- DialogWrapper handles overlay management, barcode override cleanup, and focus restoration
- Database operations available from modules.db_operation
- UI file located at ui/product_menu.ui relative to BASE_DIR/UI_DIR from config
"""
from typing import Optional
import os
from PyQt5 import uic
from PyQt5.QtWidgets import (
    QVBoxLayout, QWidget, QLabel, QPushButton, QLineEdit, QComboBox, QSlider, QTabWidget,
    QCompleter
)
## BaseMenuDialog import removed
from PyQt5.QtCore import Qt, QDateTime, QTimer

from modules.db_operation import (
    add_product, update_product, delete_product, refresh_product_cache,
    get_product_info, get_product_full, PRODUCT_CACHE
)
from modules.table import handle_barcode_scanned
# Derive project base dir from this file location: modules/menu -> modules -> Project
# __file__ = .../Project/modules/menu/product_menu.py
# dirname x1 => .../Project/modules/menu
# dirname x2 => .../Project/modules
# dirname x3 => .../Project (desired)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
QSS_PATH = os.path.join(ASSETS_DIR, 'menu.qss')


def _load_stylesheet() -> str:
    try:
        if os.path.exists(QSS_PATH):
            with open(QSS_PATH, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception:
        pass
    return ''


def open_dialog_scanner_enabled(main_window, initial_mode: Optional[str] = None, initial_code: Optional[str] = None):
    product_ui = os.path.join(UI_DIR, 'product_menu.ui')
    if not os.path.exists(product_ui):
        return

    try:
        content = uic.loadUi(product_ui)
    except Exception as e:
        return

    # No need to populate category combo here; handled per-tab with unique names

    # Apply dedicated stylesheet if present
    try:
        css = _load_stylesheet()
        if css:
            content.setStyleSheet(css)
    except Exception:
        pass

    # Use QDialog for the dialog container
    try:
        mw = main_window.frameGeometry().width()
        mh = main_window.frameGeometry().height()
        dw_full = max(400, int(mw * 0.6))
        dh_full = max(300, int(mh * 0.6))
    except Exception:
        dw_full, dh_full = 600, 400
    # Set frameless window flags directly on loaded content if it's a QDialog
    from PyQt5.QtWidgets import QDialog, QVBoxLayout
    dlg = QDialog(main_window)
    dlg.setModal(True)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(content)

    # Wire custom window titlebar X button to close dialog
    custom_close_btn = content.findChild(QPushButton, 'customCloseBtn')
    if custom_close_btn is not None:
        custom_close_btn.clicked.connect(dlg.reject)

    tab_widget: QTabWidget = content.findChild(QTabWidget, 'tabWidget')
    # Always land on ADD tab unless initial_mode is set
    if tab_widget is not None and (initial_mode is None or str(initial_mode).lower() not in ('add','remove','update')):
        try:
            tab_widget.setCurrentIndex(0)
        except Exception:
            pass

    # Widget refs (scoped per tab)
    sub_hdr: QLabel = None
    ok_btn: QPushButton = None
    cancel_btn: QPushButton = None
    code_label: QLabel = None
    name_label: QLabel = None
    category_label: QLabel = None
    sell_label: QLabel = None
    cost_label: QLabel = None
    unit_label: QLabel = None
    supplier_label: QLabel = None
    last_updated_label: QLabel = None

    # ADD tab
    code_edit: QLineEdit = None
    name_edit: QLineEdit = None
    category_combo: QComboBox = None
    cost_edit: QLineEdit = None
    sell_edit: QLineEdit = None
    unit_combo: QComboBox = None
    supplier_edit: QLineEdit = None
    last_updated_edit: QLineEdit = None
    status_lbl: QLabel = None

    # REMOVE tab
    remove_code_edit: QLineEdit = None
    remove_name_edit: QLineEdit = None
    remove_search_combo: QComboBox = None
    remove_category_edit: QLineEdit = None
    remove_cost_edit: QLineEdit = None
    remove_sell_edit: QLineEdit = None
    remove_unit_edit: QLineEdit = None
    remove_supplier_edit: QLineEdit = None
    remove_last_updated_edit: QLineEdit = None
    remove_status_lbl: QLabel = None

    # UPDATE tab
    update_code_edit: QLineEdit = None
    update_name_edit: QLineEdit = None
    update_search_combo: QComboBox = None
    update_category_combo: QComboBox = None
    update_cost_edit: QLineEdit = None
    update_sell_edit: QLineEdit = None
    update_unit_edit: QLineEdit = None
    update_supplier_edit: QLineEdit = None
    update_last_updated_edit: QLineEdit = None
    update_status_lbl: QLabel = None

    def _current_scope_widget():
        try:
            return tab_widget.currentWidget() if tab_widget is not None else content
        except Exception:
            return content

    def _mode_from_tab_index(idx: int) -> str:
        return 'add' if idx == 0 else ('remove' if idx == 1 else 'update')

    def _bind_refs():
        nonlocal sub_hdr, ok_btn, cancel_btn
        nonlocal code_label, name_label, category_label, sell_label, cost_label, unit_label, supplier_label, last_updated_label
        nonlocal code_edit, name_edit, category_combo, cost_edit, sell_edit, unit_combo, supplier_edit, last_updated_edit, status_lbl
        # (No longer using search_row, search_code, search_name_combo, search_slider, remove_code_display, remove_name_display, remove_category_display, remove_cost_display, remove_sell_display, remove_unit_display, remove_supplier_display, remove_last_updated_display)
        scope = _current_scope_widget()
        # ADD tab widgets
        sub_hdr = scope.findChild(QLabel, 'addSubHeaderLabel') or scope.findChild(QLabel, 'removeSubHeaderLabel') or scope.findChild(QLabel, 'updateSubHeaderLabel')
        ok_btn = scope.findChild(QPushButton, 'btnAddOk') or scope.findChild(QPushButton, 'btnRemoveOk') or scope.findChild(QPushButton, 'btnUpdateOk')
        cancel_btn = scope.findChild(QPushButton, 'btnAddCancel') or scope.findChild(QPushButton, 'btnRemoveCancel') or scope.findChild(QPushButton, 'btnUpdateCancel')
        code_label = scope.findChild(QLabel, 'addProductCodeLabel') or scope.findChild(QLabel, 'removeProductCodeLabel') or scope.findChild(QLabel, 'updateProductCodeLabel')
        name_label = scope.findChild(QLabel, 'addProductNameLabel') or scope.findChild(QLabel, 'removeProductNameLabel') or scope.findChild(QLabel, 'updateProductNameLabel')
        category_label = scope.findChild(QLabel, 'addCategoryLabel') or scope.findChild(QLabel, 'removeCategoryLabel') or scope.findChild(QLabel, 'updateCategoryLabel')
        sell_label = scope.findChild(QLabel, 'addSellingPriceLabel') or scope.findChild(QLabel, 'removeSellingPriceLabel') or scope.findChild(QLabel, 'updateSellingPriceLabel')
        cost_label = scope.findChild(QLabel, 'addCostPriceLabel') or scope.findChild(QLabel, 'removeCostPriceLabel') or scope.findChild(QLabel, 'updateCostPriceLabel')
        unit_label = scope.findChild(QLabel, 'addUnitLabel') or scope.findChild(QLabel, 'removeUnitLabel') or scope.findChild(QLabel, 'updateUnitLabel')
        supplier_label = scope.findChild(QLabel, 'addSupplierLabel') or scope.findChild(QLabel, 'removeSupplierLabel') or scope.findChild(QLabel, 'updateSupplierLabel')
        last_updated_label = scope.findChild(QLabel, 'addLastUpdatedLabel') or scope.findChild(QLabel, 'removeLastUpdatedLabel') or scope.findChild(QLabel, 'updateLastUpdatedLabel')
        # ADD tab
        code_edit = scope.findChild(QLineEdit, 'addProductCodeLineEdit')
        name_edit = scope.findChild(QLineEdit, 'addProductNameLineEdit')
        category_combo = scope.findChild(QComboBox, 'addCategoryComboBox')
        cost_edit = scope.findChild(QLineEdit, 'addCostPriceLineEdit')
        sell_edit = scope.findChild(QLineEdit, 'addSellingPriceLineEdit')
        unit_edit = scope.findChild(QLineEdit, 'addUnitLineEdit')
        supplier_edit = scope.findChild(QLineEdit, 'addSupplierLineEdit')
        last_updated_edit = scope.findChild(QLineEdit, 'addLastUpdatedLineEdit')
        status_lbl = scope.findChild(QLabel, 'addStatusLabel')
        # REMOVE tab
        remove_code_edit = scope.findChild(QLineEdit, 'removeProductCodeLineEdit')
        remove_name_edit = scope.findChild(QLineEdit, 'removeProductNameLineEdit')
        remove_search_combo = scope.findChild(QComboBox, 'removeSearchComboBox')
        remove_category_edit = scope.findChild(QLineEdit, 'removeCategoryLineEdit')
        remove_cost_edit = scope.findChild(QLineEdit, 'removeCostPriceLineEdit')
        remove_sell_edit = scope.findChild(QLineEdit, 'removeSellingPriceLineEdit')
        remove_unit_edit = scope.findChild(QLineEdit, 'removeUnitLineEdit')
        remove_supplier_edit = scope.findChild(QLineEdit, 'removeSupplieLineEdit')
        remove_last_updated_edit = scope.findChild(QLineEdit, 'removeLastUpdatedLineEdit')
        remove_status_lbl = scope.findChild(QLabel, 'removeStatusLabel')
        # UPDATE tab
        update_code_edit = scope.findChild(QLineEdit, 'updateProductCodeLineEdit')
        update_name_edit = scope.findChild(QLineEdit, 'updateProductNameLineEdit')
        update_search_combo = scope.findChild(QComboBox, 'updateSearchComboBox')
        update_category_combo = scope.findChild(QComboBox, 'updateCategoryComboBox')
        update_cost_edit = scope.findChild(QLineEdit, 'updateCostPriceLineEdit')
        update_sell_edit = scope.findChild(QLineEdit, 'updateSellingPriceLineEdit')
        update_unit_edit = scope.findChild(QLineEdit, 'updateUnitLineEdit')
        update_supplier_edit = scope.findChild(QLineEdit, 'updateSupplierLineEdit')
        update_last_updated_edit = scope.findChild(QLineEdit, 'updateLastUpdatedLineEdit')
        update_status_lbl = scope.findChild(QLabel, 'updateStatusLabel')

    current_mode = {'mode': 'none'}
    mode_locked = {'locked': False}
    # Sales-active rule: if dialog is opened due to barcode scan (non-existing code), lock to ADD tab
    sale_active = False
    # If initial_mode is None and initial_code is not None, assume scan scenario (lock tabs)
    if initial_mode is None and initial_code is not None:
        sale_active = True
    else:
        try:
            st = getattr(main_window, 'sales_table', None)
            sale_active = (st is not None and st.rowCount() > 0)
        except Exception:
            sale_active = False

    def set_mode_tabs_enabled(enabled: bool):
        if tab_widget is not None:
            try:
                # Enable/disable Remove and Update tabs explicitly
                # Tab indices: 0=ADD, 1=REMOVE, 2=UPDATE
                tab_widget.setTabEnabled(1, enabled)
                tab_widget.setTabEnabled(2, enabled)
            except Exception:
                pass

    def set_ok_button_enabled(enabled: bool):
        if ok_btn is not None:
            ok_btn.setEnabled(enabled)

    def set_code_error_style(error: bool):
        if code_edit is None:
            return
        if error:
            code_edit.setStyleSheet(code_edit.styleSheet() + '; border: 1px solid #b00020;')
        else:
            code_edit.setStyleSheet('')

    def set_status(text: str, ok: bool):
        if status_lbl is None:
            return
        status_lbl.setText(text)
        try:
            status_lbl.setStyleSheet('color: %s; font-weight: 600;' % ('#0a8f08' if ok else '#b00020'))
        except Exception:
            pass

    def set_fields_enabled(enabled: bool):
        for w in (name_edit, category_combo, cost_edit, sell_edit, unit_combo, supplier_edit):
            if w is not None:
                w.setEnabled(enabled)
        if last_updated_edit is not None:
            last_updated_edit.setEnabled(False)
            try: last_updated_edit.setReadOnly(True)
            except Exception: pass

    def clear_fields(except_code: bool = True):
        if not except_code and code_edit is not None:
            code_edit.clear()
        for le in (name_edit, sell_edit, cost_edit, supplier_edit, last_updated_edit):
            if le is not None:
                le.clear()
        if category_combo is not None:
            if hasattr(category_combo, 'count') and hasattr(category_combo, 'setCurrentIndex'):
                if category_combo.count() > 0:
                    category_combo.setCurrentIndex(0)
            elif hasattr(category_combo, 'clear'):
                category_combo.clear()
        if unit_combo is not None:
            if hasattr(unit_combo, 'count') and hasattr(unit_combo, 'setCurrentIndex'):
                if unit_combo.count() > 0:
                    unit_combo.setCurrentIndex(0)
            elif hasattr(unit_combo, 'clear'):
                unit_combo.clear()

    def _populate_search_name_combo():
        # No longer used in new UI structure
        pass

    def on_name_changed(text: str):
        mode = current_mode['mode']
        # Only search if name_edit is QComboBox and code_edit is empty
        if not name_edit or not isinstance(name_edit, QComboBox): return
        if code_edit and code_edit.text().strip(): return

        t = (text or '').strip().lower()
        if not t:
            name_edit.hidePopup()
            return

        # Filter PRODUCT_CACHE for partial matches
        matches = [v[0] for k, v in PRODUCT_CACHE.items() if v[0] and t in v[0].lower()]

        name_edit.blockSignals(True)
        name_edit.clear()
        name_edit.addItems(matches)
        name_edit.setEditText(text)
        name_edit.blockSignals(False)

        if matches:
            name_edit.showPopup()

    def _populate_combos_if_empty():
        if category_combo is not None and category_combo.count() == 0:
            for txt in ['Other','Electronics','Food','Apparel']:
                category_combo.addItem(txt)
        if unit_combo is not None and unit_combo.count() == 0:
            for txt in ['pcs','kg']:
                unit_combo.addItem(txt)

    def apply_mode(mode: str):
        if sub_hdr is not None:
            sub_hdr.setText('Add New Product' if mode == 'add' else ('Remove Product' if mode == 'remove' else 'Update / View Product'))
        if ok_btn is not None:
            ok_btn.setText('ADD' if mode == 'add' else ('DELETE' if mode == 'remove' else 'UPDATE'))
        # All search and field clearing logic is now handled in enter_mode

    def enter_mode(mode: str):
        _bind_refs()
        current_mode['mode'] = mode
        set_status('', True)
        apply_mode(mode)
        # Wire buttons for the current tab (each tab has its own buttons)
        try:
            if ok_btn:
                if ok_btn:
                    try:
                        ok_btn.clicked.disconnect()
                    except Exception:
                        pass
                    ok_btn.clicked.connect(on_ok_clicked)
                    try:
                        ok_btn.setAutoDefault(True)
                        ok_btn.setDefault(False)
                    except Exception:
                        pass
            if cancel_btn:
                try:
                    cancel_btn.clicked.disconnect()
                except Exception:
                    pass
                def _on_cancel():
                    try:
                        set_mode_tabs_enabled(True)
                    except Exception:
                        pass
                    clear_fields(except_code=False)
                    set_status('', True)
                    dlg.reject()
                cancel_btn.clicked.connect(_on_cancel)
        except Exception:
            pass
        if mode == 'add':
            set_fields_enabled(True)
            set_ok_button_enabled(True)
            set_code_error_style(False)
            _populate_combos_if_empty()
            if name_edit:
                try: name_edit.textChanged.disconnect()
                except Exception: pass
                name_edit.textChanged.connect(on_name_changed)
            if code_edit: code_edit.setFocus()
        elif mode == 'remove':
            # REMOVE: code field is editable for barcode/keyboard input, name is read-only
            if remove_code_edit:
                remove_code_edit.setReadOnly(False)
                remove_code_edit.setStyleSheet('')
            if remove_name_edit:
                remove_name_edit.setReadOnly(True)
                remove_name_edit.setStyleSheet('background:#f0f0f0;')
            # Populate search combo
            if remove_search_combo:
                remove_search_combo.clear()
                names = sorted(set((v[0] or '') for v in PRODUCT_CACHE.values() if v[0]))
                for n in names:
                    remove_search_combo.addItem(n)
                remove_search_combo.setCurrentIndex(-1)
            # Clear all fields
            for le in (remove_code_edit, remove_name_edit, remove_category_edit, remove_cost_edit, remove_sell_edit, remove_unit_edit, remove_supplier_edit, remove_last_updated_edit):
                if le: le.clear()
        elif mode == 'update':
            # UPDATE: code field is editable for barcode/keyboard input, name is editable
            if update_code_edit:
                update_code_edit.setReadOnly(False)
                update_code_edit.setStyleSheet('')
            if update_name_edit:
                update_name_edit.setReadOnly(False)
                update_name_edit.setStyleSheet('')
            # Populate search combo
            if update_search_combo:
                update_search_combo.clear()
                names = sorted(set((v[0] or '') for v in PRODUCT_CACHE.values() if v[0]))
                for n in names:
                    update_search_combo.addItem(n)
                update_search_combo.setCurrentIndex(-1)
            # Clear all fields
            for le in (update_code_edit, update_name_edit, update_category_combo, update_cost_edit, update_sell_edit, update_unit_edit, update_supplier_edit, update_last_updated_edit):
                if le: le.clear()
    # --- SEARCH COMBO LOGIC ---
    def on_remove_search_selected(name: str):
        if not name:
            return
        # Find product by name
        code = None
        for k, (nm, _pr, unit) in PRODUCT_CACHE.items():
            if (nm or '').strip().lower() == name.strip().lower():
                code = k
                break
        if not code:
            if remove_status_lbl:
                remove_status_lbl.setText('Product not found.')
            return
        pdata = get_product_full(code)[1]
        if pdata:
            remove_code_edit.setText(code)
            remove_name_edit.setText(pdata.get('name',''))
            remove_category_edit.setText(pdata.get('category',''))
            remove_cost_edit.setText(str(pdata.get('cost_price','')))
            remove_sell_edit.setText(str(pdata.get('price','')))
            remove_unit_edit.setText(pdata.get('unit',''))
            remove_supplier_edit.setText(pdata.get('supplier',''))
            remove_last_updated_edit.setText(str(pdata.get('last_updated','')))
            if remove_status_lbl:
                remove_status_lbl.setText('Product found.')

    def on_update_search_selected(name: str):
        if not name:
            return
        # Find product by name
        code = None
        for k, (nm, _pr, unit) in PRODUCT_CACHE.items():
            if (nm or '').strip().lower() == name.strip().lower():
                code = k
                break
        if not code:
            if update_status_lbl:
                update_status_lbl.setText('Product not found.')
            return
        pdata = get_product_full(code)[1]
        if pdata:
            update_code_edit.setText(code)
            update_name_edit.setText(pdata.get('name',''))
            if update_category_combo:
                idx = update_category_combo.findText(pdata.get('category',''), Qt.MatchFixedString)
                update_category_combo.setCurrentIndex(idx if idx >= 0 else 0)
            update_cost_edit.setText(str(pdata.get('cost_price','')))
            update_sell_edit.setText(str(pdata.get('price','')))
            update_unit_edit.setText(pdata.get('unit',''))
            update_supplier_edit.setText(pdata.get('supplier',''))
            update_last_updated_edit.setText(str(pdata.get('last_updated','')))
            if update_status_lbl:
                update_status_lbl.setText('Product found.')

    # Connect search combo signals
    if remove_search_combo:
        remove_search_combo.activated[str].connect(on_remove_search_selected)
    if update_search_combo:
        update_search_combo.activated[str].connect(on_update_search_selected)

    def on_code_changed(text: str):
        mode = current_mode['mode']
        t = (text or '').strip()
        if mode == 'add':
            if not t:
                set_status('', True); set_code_error_style(False); set_ok_button_enabled(True); return
            c_found, _, _price, _ = get_product_info(t)
            if c_found:
                set_status('Error: Product code already exists.', False); set_code_error_style(True); set_ok_button_enabled(False); return
            d_found, pdata_full = get_product_full(t)
            if d_found:
                set_status('Error: Product code already exists.', False); set_code_error_style(True); set_ok_button_enabled(False); return
            set_status('', True); set_code_error_style(False); set_ok_button_enabled(True); return
        # No longer used in new UI structure
        pass

    # --- Dual-mode: reverse lookup when selecting from name combo ---
    def on_name_selected_from_main(name_text: str):
        if not name_text:
            return
        # Find code for this name
        code_found = None
        for k, (nm, _pr, unit) in PRODUCT_CACHE.items():
            if (nm or '').strip().lower() == name_text.strip().lower():
                code_found = k
                break
        if code_found and code_edit:
            code_edit.setText(code_found)
            on_code_changed(code_found)

    def on_ok_clicked():
        mode = current_mode['mode']
        if mode == 'add':
            missing=[]
            if code_edit and not code_edit.text().strip(): missing.append('Product Code')
            if name_edit:
                if isinstance(name_edit, QComboBox):
                    if not name_edit.currentText().strip(): missing.append('Product Name')
                else:
                    if not name_edit.text().strip(): missing.append('Product Name')
            if sell_edit and not sell_edit.text().strip(): missing.append('Selling Price')
            if category_combo and (category_combo.currentText().strip() == '' or category_combo.currentText().strip() is None): missing.append('Category')
            if unit_combo and (unit_combo.currentText().strip() == '' or unit_combo.currentText().strip() is None): missing.append('Unit')
            if missing:
                set_status('Error: Please provide ' + ', '.join(missing), False)
                return
            try:
                code = code_edit.text().strip()
                name_val = name_edit.currentText().strip() if isinstance(name_edit, QComboBox) else name_edit.text().strip() if name_edit else ''
                price = float(sell_edit.text()) if sell_edit else 0.0
                cat = category_combo.currentText().strip() if category_combo else None
                supplier = supplier_edit.text().strip() if supplier_edit else None
                cost_val = float(cost_edit.text()) if (cost_edit and cost_edit.text().strip()) else None
                unit_val = unit_combo.currentText().strip().upper() if unit_combo and unit_combo.currentText().strip() else 'EACH'
                if unit_val not in ['KG', 'EACH']:
                    unit_val = 'EACH'
                now_str = QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss')
                ok, msg = add_product(code, name_val, price, cat, supplier, cost_val, unit_val, now_str)
                if not ok:
                    set_status(f'Error: {msg}', False)
                    return
            except Exception as _e:
                set_status(f'Error: {_e}', False)
                return
            try:
                if last_updated_edit: last_updated_edit.setText(now_str)
            except Exception: pass
            try: refresh_product_cache()
            except Exception: pass
            set_status('Added successfully.', True)
            try:
                code_to_add = str(initial_code).strip() if initial_code else (code_edit.text().strip() if code_edit else '')
                if code_to_add and getattr(main_window, 'sales_table', None) is not None:
                    status_bar = getattr(main_window, 'statusbar', None)
                    QTimer.singleShot(0, lambda c=code_to_add, sb=status_bar: handle_barcode_scanned(main_window.sales_table, c, sb))
            except Exception: pass
            QTimer.singleShot(1000, dlg.accept)
        elif mode == 'remove':
            code_to_delete = ''
            if remove_code_edit: code_to_delete = remove_code_edit.text().strip()
            if not code_to_delete:
                if remove_status_lbl:
                    remove_status_lbl.setText('Error: Provide Product Code to delete.')
                return
            try:
                ok, msg = delete_product(code_to_delete)
                if not ok:
                    if remove_status_lbl:
                        remove_status_lbl.setText(f'Error: {msg}')
                    return
            except Exception as _e:
                if remove_status_lbl:
                    remove_status_lbl.setText(f'Error: {_e}')
                return
            try: refresh_product_cache()
            except Exception: pass
            if remove_status_lbl:
                remove_status_lbl.setText('Deleted successfully.')
            QTimer.singleShot(1000, dlg.accept)
        elif mode == 'update':
            missing=[]
            if code_edit is None or not code_edit.text().strip(): missing.append('Product Code')
            name_val = None
            if name_edit:
                if isinstance(name_edit, QComboBox):
                    name_val = name_edit.currentText().strip()
                else:
                    name_val = name_edit.text().strip()
            if not name_val:
                missing.append('Product Name')
            if sell_edit and not sell_edit.text().strip(): missing.append('Selling Price')
            if category_combo and (category_combo.currentText().strip() == '' or category_combo.currentText().strip() is None): missing.append('Category')
            if unit_combo and (unit_combo.currentText().strip() == '' or unit_combo.currentText().strip() is None): missing.append('Unit')
            if missing:
                set_status('Error: Please provide ' + ', '.join(missing), False)
                return
            try:
                price_val = float(sell_edit.text()) if (sell_edit and sell_edit.text().strip()) else None
                cat = category_combo.currentText().strip() if category_combo else None
                supplier = supplier_edit.text().strip() if (supplier_edit and supplier_edit.text().strip()) else None
                cost_val = float(cost_edit.text()) if (cost_edit and cost_edit.text().strip()) else None
                unit_val = unit_combo.currentText().strip().upper() if unit_combo and unit_combo.currentText().strip() else None
                if unit_val and unit_val not in ['KG', 'EACH']:
                    unit_val = 'EACH'
                ok, msg = update_product(code_edit.text().strip(), name_val, price_val, cat, supplier, cost_val, unit_val)
                if not ok:
                    set_status(f'Error: {msg}', False)
                    return
            except Exception as _e:
                set_status(f'Error: {_e}', False)
                return
            try:
                if last_updated_edit: last_updated_edit.setText(QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss'))
            except Exception: pass
            try: refresh_product_cache()
            except Exception: pass
            set_status('Updated successfully.', True)
            QTimer.singleShot(1000, dlg.accept)

    def on_code_return_pressed():
        try:
            mode = current_mode['mode']
            if mode in ('remove','update'):
                if code_edit: on_code_changed(code_edit.text())
                if not mode_locked['locked']:
                    mode_locked['locked'] = True; set_mode_tabs_enabled(False)
                QTimer.singleShot(0, lambda: dlg.focusNextPrevChild(True))
            else:
                QTimer.singleShot(0, lambda: dlg.focusNextPrevChild(True))
        except Exception: pass

    # Wire events after initial binding
    _bind_refs()
    # Apply sales-active rule immediately
    try:
        if tab_widget is not None:
            if sale_active:
                # Disable Remove & Update tabs and force to Add
                set_mode_tabs_enabled(False)
                try:
                    tab_widget.blockSignals(True)
                    tab_widget.setCurrentIndex(0)
                    tab_widget.blockSignals(False)
                except Exception:
                    pass
                mode_locked['locked'] = True
            else:
                set_mode_tabs_enabled(True)
                mode_locked['locked'] = False
    except Exception:
        pass
    if tab_widget is not None:
        try: tab_widget.currentChanged.disconnect()
        except Exception: pass
        def _on_tab(idx: int):
            if mode_locked['locked'] and tab_widget is not None:
                prev_mode = current_mode['mode']
                desired_idx = 0 if prev_mode == 'add' else (1 if prev_mode == 'remove' else 2)
                if idx != desired_idx:
                    tab_widget.blockSignals(True)
                    tab_widget.setCurrentIndex(desired_idx)
                    tab_widget.blockSignals(False)
                    return
            enter_mode(_mode_from_tab_index(idx))
            # Focus product code QLineEdit after switching tabs
            try:
                if code_edit: code_edit.setFocus()
            except Exception: pass
        tab_widget.currentChanged.connect(_on_tab)

    if ok_btn: ok_btn.clicked.connect(on_ok_clicked)
    if cancel_btn:
        def _on_cancel():
            set_mode_tabs_enabled(True)
            try:
                print(f'[ProductPanel] Initial CANCEL clicked (mode={current_mode["mode"]})')
            except Exception:
                pass
            try:
                clear_fields(except_code=False)
                set_status('', True)
                dlg.reject()
                if dlg.isVisible():
                    dlg.close()
            except Exception:
                pass
        cancel_btn.clicked.connect(_on_cancel)
    if code_edit:
        try: code_edit.textChanged.disconnect()
        except Exception: pass
        code_edit.textChanged.connect(on_code_changed)
        try: code_edit.returnPressed.disconnect()
        except Exception: pass
        code_edit.returnPressed.connect(on_code_return_pressed)
    # (search_code and search_name_combo logic removed; replaced by remove_search_combo and update_search_combo above)

    def _wire_return_as_tab(le: QLineEdit):
        if not le: return
        try: le.returnPressed.disconnect()
        except Exception: pass
        le.returnPressed.connect(lambda: dlg.focusNextPrevChild(True))
    for le in (name_edit, cost_edit, sell_edit, supplier_edit):
        _wire_return_as_tab(le)

    # Start in current tab's mode, enforcing sale_active lock
    start_idx = tab_widget.currentIndex() if tab_widget is not None else 0
    if sale_active:
        start_idx = 0
    enter_mode(_mode_from_tab_index(start_idx))

    # Initial mode/code override
    try:
        if isinstance(initial_mode,str) and initial_mode.lower() in ('add','remove','update'):
            start_mode = initial_mode.lower()
            if tab_widget is not None:
                idx = 0 if start_mode=='add' else (1 if start_mode=='remove' else 2)
                tab_widget.blockSignals(True); tab_widget.setCurrentIndex(idx); tab_widget.blockSignals(False)
            enter_mode(start_mode)
            if initial_code and code_edit:
                code_edit.setText(str(initial_code)); code_edit.setFocus()
                if start_mode in ('remove','update'):
                    on_code_changed(str(initial_code))
    except Exception: pass



    # Scanner override routing
    try:
        from PyQt5.QtWidgets import QApplication
        def _barcode_to_product_code(code: str) -> bool:
            try:
                if not code:
                    return False
                inst = QApplication.instance()
                fw = inst.focusWidget() if inst else None
                # Accept barcode in REMOVE tab search combo
                if fw is remove_search_combo and remove_search_combo is not None and current_mode['mode'] == 'remove':
                    # Try to select the matching product by name
                    for i in range(remove_search_combo.count()):
                        if code.strip().lower() == remove_search_combo.itemText(i).strip().lower():
                            remove_search_combo.setCurrentIndex(i)
                            on_remove_search_selected(remove_search_combo.itemText(i))
                            return True
                    return False
                # Accept barcode in UPDATE tab search combo
                if fw is update_search_combo and update_search_combo is not None and current_mode['mode'] == 'update':
                    for i in range(update_search_combo.count()):
                        if code.strip().lower() == update_search_combo.itemText(i).strip().lower():
                            update_search_combo.setCurrentIndex(i)
                            on_update_search_selected(update_search_combo.itemText(i))
                            return True
                    return False
                return False
            except Exception:
                return False
        main_window._barcodeOverride = _barcode_to_product_code
        if hasattr(main_window, 'barcode_manager'):
            main_window.barcode_manager._barcodeOverride = _barcode_to_product_code
    except Exception:
        pass


    # Return QDialog to wrapper for execution
    return dlg
