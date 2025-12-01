"""Product Management dialog logic extracted from main.py.

Provides a function open_product_panel(main_window, initial_mode=None, initial_code=None)
that encapsulates all behavior for ADD / REMOVE / UPDATE tabs.

Rationale for extraction:
- Keeps main window lean
- Enables future unit testing of product panel logic
- Allows dedicated styling via product_menu.qss

Assumptions:
- main_window supplies methods: _show_dim_overlay, _hide_dim_overlay, _clear_barcode_override,
  _refocus_sales_table and attributes: sales_table, statusbar
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
from modules.sales.salesTable import handle_barcode_scanned
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


def open_product_dialog(main_window, initial_mode: Optional[str] = None, initial_code: Optional[str] = None):
    # Debug print removed
    product_ui = os.path.join(UI_DIR, 'product_menu.ui')
    if not os.path.exists(product_ui):
        # Debug print removed
        return

    # Show dim overlay
    try:
        main_window._show_dim_overlay()
    except Exception:
        pass

    try:
        content = uic.loadUi(product_ui)
    except Exception as e:
        # Debug print removed
        try: main_window._hide_dim_overlay()
        except Exception: pass
        return

    # Add predefined items to category combo box
    category_combo = content.findChild(QComboBox, 'categoryComboBox')
    if category_combo is not None:
        category_combo.clear()
        for txt in ['Other', 'Electronics', 'Food', 'Apparel']:
            category_combo.addItem(txt)

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
    try:
        content.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
        content.setModal(True)
        content.setFixedSize(dw_full, dh_full)
        content.setWindowTitle('')
        dlg = content
    except Exception:
        # Fallback to embedding in a QDialog if content is not a QDialog
        from PyQt5.QtWidgets import QDialog, QVBoxLayout
        dlg = QDialog(main_window)
        dlg.setModal(True)
        dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
        dlg.setFixedSize(dw_full, dh_full)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(content)

    # Wire custom window titlebar X button to close dialog
    custom_close_btn = content.findChild(QPushButton, 'customCloseBtn')
    if custom_close_btn is not None:
        custom_close_btn.clicked.connect(dlg.reject)

    tab_widget: QTabWidget = content.findChild(QTabWidget, 'tabWidget')

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

    code_edit: QLineEdit = None
    name_edit: QLineEdit = None
    category_combo: QComboBox = None
    cost_edit: QLineEdit = None
    sell_edit: QLineEdit = None
    unit_combo: QComboBox = None
    supplier_edit: QLineEdit = None
    last_updated_edit: QLineEdit = None
    status_lbl: QLabel = None

    search_row: QWidget = None
    search_code: QLineEdit = None
    search_name_combo: QComboBox = None
    search_slider: QSlider = None

    remove_code_display: QLabel = None
    remove_name_display: QLabel = None
    remove_category_display: QLabel = None
    remove_cost_display: QLabel = None
    remove_sell_display: QLabel = None
    remove_unit_display: QLabel = None
    remove_supplier_display: QLabel = None
    remove_last_updated_display: QLabel = None

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
        nonlocal search_row, search_code, search_name_combo, search_slider
        nonlocal remove_code_display, remove_name_display, remove_category_display, remove_cost_display, remove_sell_display, remove_unit_display, remove_supplier_display, remove_last_updated_display
        scope = _current_scope_widget()
        sub_hdr = scope.findChild(QLabel, 'subHeaderLabel')
        ok_btn = scope.findChild(QPushButton, 'okButton')
        cancel_btn = scope.findChild(QPushButton, 'cancelButton')
        code_label = scope.findChild(QLabel, 'productCodeLabel')
        name_label = scope.findChild(QLabel, 'productNameLabel')
        category_label = scope.findChild(QLabel, 'categoryLabel')
        sell_label = scope.findChild(QLabel, 'sellingPriceLabel')
        cost_label = scope.findChild(QLabel, 'costPriceLabel')
        unit_label = scope.findChild(QLabel, 'unitLabel')
        supplier_label = scope.findChild(QLabel, 'supplierLabel')
        last_updated_label = scope.findChild(QLabel, 'lastUpdatedLabel')
        code_edit = scope.findChild(QLineEdit, 'productCodeLineEdit')
        name_edit = scope.findChild(QLineEdit, 'productNameLineEdit')
        category_combo = scope.findChild(QComboBox, 'categoryComboBox')
        cost_edit = scope.findChild(QLineEdit, 'costPriceLineEdit')
        sell_edit = scope.findChild(QLineEdit, 'sellingPriceLineEdit')
        unit_combo = scope.findChild(QComboBox, 'unitComboBox')
        supplier_edit = scope.findChild(QLineEdit, 'supplierLineEdit')
        last_updated_edit = scope.findChild(QLineEdit, 'lastUpdatedLineEdit')
        status_lbl = scope.findChild(QLabel, 'statusLabel')
        search_row = scope.findChild(QWidget, 'searchRowWidget')
        search_code = scope.findChild(QLineEdit, 'searchCodeLineEdit')
        search_name_combo = scope.findChild(QComboBox, 'searchNameComboBox')
        search_slider = scope.findChild(QSlider, 'searchModeSlider')
        remove_code_display = scope.findChild(QLabel, 'productCodeDisplayLabel')
        remove_name_display = scope.findChild(QLabel, 'productNameDisplayLabel')
        remove_category_display = scope.findChild(QLabel, 'categoryDisplayLabel')
        remove_cost_display = scope.findChild(QLabel, 'costPriceDisplayLabel')
        remove_sell_display = scope.findChild(QLabel, 'sellingPriceDisplayLabel')
        remove_unit_display = scope.findChild(QLabel, 'unitDisplayLabel')
        remove_supplier_display = scope.findChild(QLabel, 'supplierDisplayLabel')
        remove_last_updated_display = scope.findChild(QLabel, 'lastUpdatedDisplayLabel')

    current_mode = {'mode': 'none'}
    mode_locked = {'locked': False}
    # Sales-active rule: if sales table has items, disallow Remove/Update
    sale_active = False
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
        if category_combo is not None and category_combo.count() > 0:
            category_combo.setCurrentIndex(0)
        if unit_combo is not None and unit_combo.count() > 0:
            unit_combo.setCurrentIndex(0)

    def _populate_search_name_combo():
        if search_name_combo is None:
            return
        names = []
        seen = set()
        for _code, (_name, _price) in PRODUCT_CACHE.items():
            n = (_name or '').strip()
            if not n: continue
            k = n.lower()
            if k in seen: continue
            seen.add(k)
            names.append(n)
        names.sort(key=lambda s: s.lower())
        try:
            search_name_combo.blockSignals(True)
            search_name_combo.clear()
            for n in names: search_name_combo.addItem(n)
            search_name_combo.setEditable(True)
            le = search_name_combo.lineEdit()
            if le: le.setPlaceholderText('Enter Product Name')
        finally:
            search_name_combo.blockSignals(False)
        try:
            comp = QCompleter(names, search_name_combo)
            comp.setCaseSensitivity(Qt.CaseInsensitive)
            search_name_combo.setCompleter(comp)
        except Exception:
            pass

    def on_name_changed(text: str):
        mode = current_mode['mode']
        if mode not in ('add','update'): return
        t = (text or '').strip()
        if not t:
            set_status('', True)
            set_ok_button_enabled(True)
            return
        low = t.lower()
        exists_cache = any((nm or '').strip().lower() == low for _code,(nm,_p) in PRODUCT_CACHE.items())
        if exists_cache:
            if mode == 'update' and code_edit is not None and code_edit.text().strip():
                existing_name = PRODUCT_CACHE.get(code_edit.text().strip().upper(), ('',0.0))[0].strip().lower()
                if existing_name == low:
                    set_status('', True)
                    set_ok_button_enabled(True)
                    return
            set_status('Error: Product name already exists.', False)
            set_ok_button_enabled(False)
            return
        # DB-level check
        try:
            import sqlite3
            from modules.db_operation.database import DB_PATH
            if os.path.exists(DB_PATH):
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                if mode == 'update' and code_edit is not None and code_edit.text().strip():
                    cur.execute("SELECT 1 FROM Product_list WHERE TRIM(name)=TRIM(?) COLLATE NOCASE AND product_code <> ?", (t, code_edit.text().strip()))
                else:
                    cur.execute("SELECT 1 FROM Product_list WHERE TRIM(name)=TRIM(?) COLLATE NOCASE", (t,))
                exists_db = cur.fetchone()
                conn.close()
                if exists_db:
                    set_status('Error: Product name already exists.', False)
                    set_ok_button_enabled(False)
                    return
        except Exception:
            pass
        set_status('', True)
        set_ok_button_enabled(True)

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
        if mode == 'remove' or mode == 'update':
            if search_row: search_row.show()
            if search_slider: search_slider.setValue(0)
            if search_code:
                search_code.clear(); search_code.setFocus()
            if search_name_combo:
                _populate_search_name_combo()
                try:
                    search_name_combo.setCurrentIndex(-1)
                    search_name_combo.setEditText('')
                except Exception: pass
        if mode == 'add':
            # hide search row implicitly (designer may not show in add tab)
            pass

    def enter_mode(mode: str):
        _bind_refs()
        current_mode['mode'] = mode
        set_status('', True)
        apply_mode(mode)
        # Wire buttons for the current tab (each tab has its own buttons)
        try:
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
        else:
            clear_fields(except_code=True)
            set_fields_enabled(False)
            if mode == 'update':
                _populate_combos_if_empty()
                if name_edit:
                    try: name_edit.textChanged.disconnect()
                    except Exception: pass
                    name_edit.textChanged.connect(on_name_changed)
                try:
                    if category_combo: category_combo.setCurrentIndex(-1)
                    if unit_combo: unit_combo.setCurrentIndex(-1)
                except Exception: pass

    def on_code_changed(text: str):
        mode = current_mode['mode']
        t = (text or '').strip()
        if mode == 'add':
            if not t:
                set_status('', True); set_code_error_style(False); set_ok_button_enabled(True); return
            c_found, _, _price = get_product_info(t)
            if c_found:
                set_status('Error: Product code already exists.', False); set_code_error_style(True); set_ok_button_enabled(False); return
            d_found, pdata_full = get_product_full(t)
            if d_found:
                set_status('Error: Product code already exists.', False); set_code_error_style(True); set_ok_button_enabled(False); return
            set_status('', True); set_code_error_style(False); set_ok_button_enabled(True); return
        if mode not in ('remove','update'):
            return
        if not t:
            clear_fields(except_code=True); set_fields_enabled(False); set_status('', True)
            for lbl in (remove_code_display, remove_name_display, remove_category_display, remove_cost_display, remove_sell_display, remove_unit_display, remove_supplier_display, remove_last_updated_display):
                if lbl: lbl.setText('')
            return
        found, pdata = get_product_full(t)
        if not found or not pdata:
            c_found, c_name, c_price = get_product_info(t)
            if not c_found:
                clear_fields(except_code=True); set_fields_enabled(False); set_status('Product not found.', False); return
            pdata = {'name': c_name,'price': c_price,'category':'','supplier':'','cost_price':None,'unit':'','last_updated':'',}
        try:
            if mode == 'remove':
                if remove_code_display: remove_code_display.setText(t)
                if remove_name_display: remove_name_display.setText(str(pdata.get('name','')))
                if remove_category_display: remove_category_display.setText(str(pdata.get('category','')))
                if remove_cost_display:
                    cp = pdata.get('cost_price', None)
                    remove_cost_display.setText('' if cp in (None,'') else str(cp))
                if remove_sell_display: remove_sell_display.setText(f"{float(pdata.get('price',0.0)):.2f}")
                if remove_unit_display: remove_unit_display.setText(str(pdata.get('unit','')))
                if remove_supplier_display: remove_supplier_display.setText(str(pdata.get('supplier','')))
                if remove_last_updated_display: remove_last_updated_display.setText(str(pdata.get('last_updated','')))
            else:
                if name_edit: name_edit.setText(str(pdata.get('name','')))
            if sell_edit: sell_edit.setText(f"{float(pdata.get('price',0.0)):.2f}")
            if cost_edit:
                cp = pdata.get('cost_price', None)
                cost_edit.setText('' if cp in (None,'') else str(cp))
            if supplier_edit: supplier_edit.setText(str(pdata.get('supplier','')))
            if last_updated_edit: last_updated_edit.setText(str(pdata.get('last_updated','')))
            if category_combo:
                val = str(pdata.get('category','')).strip().lower(); matched=False
                for i in range(category_combo.count()):
                    if category_combo.itemText(i).strip().lower() == val:
                        category_combo.setCurrentIndex(i); matched=True; break
                if not matched and category_combo.count()>0: category_combo.setCurrentIndex(0)
            if unit_combo:
                val = str(pdata.get('unit','')).strip().lower()
                norm = 'pcs' if val in ('piece','pieces','pcs','pc') else ('kg' if val in ('kg','kilogram','kilograms') else val)
                matched=False
                for i in range(unit_combo.count()):
                    if unit_combo.itemText(i).strip().lower() == norm:
                        unit_combo.setCurrentIndex(i); matched=True; break
                if not matched and unit_combo.count()>0: unit_combo.setCurrentIndex(0)
        except Exception:
            pass
        set_fields_enabled(mode == 'update')
        set_status('Product found.', True)

    def on_ok_clicked():
        mode = current_mode['mode']
        if mode == 'add':
            missing=[]
            if code_edit and not code_edit.text().strip(): missing.append('Product Code')
            if name_edit and not name_edit.text().strip(): missing.append('Product Name')
            if sell_edit and not sell_edit.text().strip(): missing.append('Selling Price')
            if missing:
                set_status('Error: Please provide ' + ', '.join(missing), False); return
            try:
                code = code_edit.text().strip()
                name_val = name_edit.text().strip() if name_edit else ''
                price = float(sell_edit.text()) if sell_edit else 0.0
                cat = category_combo.currentText().strip() if category_combo else None
                supplier = supplier_edit.text().strip() if supplier_edit else None
                cost_val = float(cost_edit.text()) if (cost_edit and cost_edit.text().strip()) else None
                unit_val = unit_combo.currentText().strip() if unit_combo else None
                now_str = QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss')
                ok, msg = add_product(code, name_val, price, cat, supplier, cost_val, unit_val, now_str)
                if not ok:
                    set_status(f'Error: {msg}', False); return
            except Exception as _e:
                set_status(f'Error: {_e}', False); return
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
            if search_code: code_to_delete = search_code.text().strip()
            if not code_to_delete and remove_code_display: code_to_delete = remove_code_display.text().strip()
            if not code_to_delete:
                set_status('Error: Provide Product Code to delete.', False); return
            try:
                ok, msg = delete_product(code_to_delete)
                if not ok:
                    set_status(f'Error: {msg}', False); return
            except Exception as _e:
                set_status(f'Error: {_e}', False); return
            try: refresh_product_cache()
            except Exception: pass
            set_status('Deleted successfully.', True)
            QTimer.singleShot(1000, dlg.accept)
        elif mode == 'update':
            if code_edit is None or not code_edit.text().strip():
                set_status('Error: Provide Product Code to update.', False); return
            try:
                price_val = float(sell_edit.text()) if (sell_edit and sell_edit.text().strip()) else None
                name_val = name_edit.text().strip() if (name_edit and name_edit.text().strip()) else None
                cat = category_combo.currentText().strip() if category_combo else None
                supplier = supplier_edit.text().strip() if (supplier_edit and supplier_edit.text().strip()) else None
                cost_val = float(cost_edit.text()) if (cost_edit and cost_edit.text().strip()) else None
                unit_val = unit_combo.currentText().strip() if unit_combo else None
                ok, msg = update_product(code_edit.text().strip(), name_val, price_val, cat, supplier, cost_val, unit_val)
                if not ok:
                    set_status(f'Error: {msg}', False); return
            except Exception as _e:
                set_status(f'Error: {_e}', False); return
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
            try:
                if current_mode['mode'] in ('remove','update'):
                    if search_code: search_code.setFocus()
                else:
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
    if search_code:
        try: search_code.returnPressed.disconnect()
        except Exception: pass
        def _search_code_enter():
            t = search_code.text().strip()
            if code_edit: code_edit.setText(t)
            on_code_changed(t)
        search_code.returnPressed.connect(_search_code_enter)
    if search_name_combo:
        try: search_name_combo.activated[str].disconnect()
        except Exception: pass
        def _on_name_selected(name_text: str):
            if not name_text: return
            code_found = None
            for k,(nm,_pr) in PRODUCT_CACHE.items():
                if (nm or '').strip().lower() == name_text.strip().lower():
                    code_found = k; break
            if code_found and code_edit:
                code_edit.setText(code_found)
                on_code_changed(code_found)
        search_name_combo.activated[str].connect(_on_name_selected)

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

    def _cleanup_overlay(_code):
        try: main_window._hide_dim_overlay()
        except Exception: pass
        try: main_window.raise_(); main_window.activateWindow()
        except Exception: pass
        try: main_window._clear_barcode_override()
        except Exception: pass
        try: main_window._refocus_sales_table()
        except Exception: pass

    dlg.finished.connect(_cleanup_overlay)

    # Scanner override routing
    try:
        from PyQt5.QtWidgets import QApplication
        def _barcode_to_product_code(code: str) -> bool:
            try:
                if not code:
                    return False
                inst = QApplication.instance()
                fw = inst.focusWidget() if inst else None
                # Accept barcode in REMOVE tab search field
                if fw is search_code and search_code is not None:
                    search_code.setText(code)
                    if code_edit:
                        code_edit.setText(code)
                    if current_mode['mode'] in ('remove','update'):
                        on_code_changed(code)
                    return True
                # Accept barcode in UPDATE tab search field (searchCodeLineEdit1)
                search_code_update = None
                try:
                    # Try to find the update tab's search code field if not already referenced
                    if tab_widget is not None:
                        update_tab = tab_widget.widget(2) if tab_widget.count() > 2 else None
                        if update_tab is not None:
                            search_code_update = update_tab.findChild(QLineEdit, 'searchCodeLineEdit1')
                except Exception:
                    pass
                if fw is search_code_update and search_code_update is not None:
                    search_code_update.setText(code)
                    if code_edit:
                        code_edit.setText(code)
                    if current_mode['mode'] in ('remove','update'):
                        on_code_changed(code)
                    return True
                if fw is code_edit and code_edit is not None:
                    code_edit.setText(code)
                    if current_mode['mode'] in ('remove','update'):
                        on_code_changed(code)
                    return True
                return False
            except Exception:
                return False
        # Set override on both main_window and barcode_manager
        main_window._barcodeOverride = _barcode_to_product_code
        if hasattr(main_window, 'barcode_manager'):
            main_window.barcode_manager._barcodeOverride = _barcode_to_product_code
    except Exception:
        pass

    # Debug print removed
    dlg.exec_()
    # Debug print removed
