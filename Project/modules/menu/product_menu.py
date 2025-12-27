"""Product Management dialog logic.

This is the fixed version of the former product_menuOLD.py, intended to be used with product_menu.ui.
"""

from typing import Optional, Dict, Any, Tuple
import os

from PyQt5 import uic
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QTabWidget, QCompleter
)
from PyQt5.QtCore import Qt, QDateTime, QTimer

from modules.db_operation import (
    add_product, update_product, delete_product, refresh_product_cache,
    get_product_info, get_product_full, PRODUCT_CACHE
)
from modules.table import handle_barcode_scanned


# Derive project base dir from this file location: modules/menu -> modules -> Project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
QSS_PATH = os.path.join(ASSETS_DIR, 'product_menu.qss')


def _load_stylesheet() -> str:
    try:
        if os.path.exists(QSS_PATH):
            with open(QSS_PATH, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception:
        pass
    return ''


def open_dialog_scanner_enabled(main_window, initial_mode: Optional[str] = None, initial_code: Optional[str] = None):
    """Open the Product Management dialog.

    initial_mode: 'add' | 'remove' | 'update' (optional)
    initial_code: product code coming from a barcode scan (optional)
    """
    # ---------------- UI LOAD ----------------
    # Prefer product_menu.ui, but keep a fallback for older deployments.
    ui_candidates = [
        os.path.join(UI_DIR, 'product_menu.ui'),
        os.path.join(UI_DIR, 'product_menuOLD.ui'),
    ]
    product_ui = next((p for p in ui_candidates if os.path.exists(p)), None)
    if not product_ui:
        return None

    try:
        content = uic.loadUi(product_ui)
    except Exception:
        return None

    dlg = QDialog(main_window)
    dlg.setModal(True)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)

    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(content)

    # Apply stylesheet (optional)
    qss = _load_stylesheet()
    if qss:
        try:
            dlg.setStyleSheet(qss)
        except Exception:
            pass

    # Wire custom window close button (if present)
    custom_close_btn = content.findChild(QPushButton, 'customCloseBtn')
    if custom_close_btn is not None:
        custom_close_btn.clicked.connect(dlg.reject)

    tab_widget: QTabWidget = content.findChild(QTabWidget, 'tabWidget')

    # ---------------- WIDGET BINDING (GLOBAL, NOT TAB-SCOPED) ----------------
    def w_line(name: str) -> Optional[QLineEdit]:
        return content.findChild(QLineEdit, name)

    def w_combo(name: str) -> Optional[QComboBox]:
        return content.findChild(QComboBox, name)

    def w_btn(name: str) -> Optional[QPushButton]:
        return content.findChild(QPushButton, name)

    def w_lbl(name: str) -> Optional[QLabel]:
        return content.findChild(QLabel, name)

    ui: Dict[str, Dict[str, Any]] = {
        'add': {
            'code': w_line('addProductCodeLineEdit'),
            'name': w_line('addProductNameLineEdit') or w_combo('addProductNameComboBox'),
            'category': w_combo('addCategoryComboBox'),
            'cost': w_line('addCostPriceLineEdit'),
            'sell': w_line('addSellingPriceLineEdit'),
            'unit': w_line('addUnitLineEdit'),
            'supplier': w_line('addSupplierLineEdit'),
            'status': w_lbl('addStatusLabel'),
            'ok': w_btn('btnAddOk'),
            'cancel': w_btn('btnAddCancel'),
        },
        'remove': {
            'code': w_line('removeProductCodeLineEdit'),
            'name': w_line('removeProductNameLineEdit'),
            'search': w_combo('removeSearchComboBox'),
            'category': w_line('removeCategoryLineEdit'),
            'cost': w_line('removeCostPriceLineEdit'),
            'sell': w_line('removeSellingPriceLineEdit'),
            'unit': w_line('removeUnitLineEdit'),
            'supplier': w_line('removeSupplierLineEdit') or w_line('removeSupplieLineEdit'),
            'last_updated': w_line('removeLastUpdatedLineEdit'),
            'status': w_lbl('removeStatusLabel'),
            'ok': w_btn('btnRemoveOk'),
            'cancel': w_btn('btnRemoveCancel'),
        },
        'update': {
            'code': w_line('updateProductCodeLineEdit'),
            'name': w_line('updateProductNameLineEdit'),
            'search': w_combo('updateSearchComboBox'),
            'category': w_combo('updateCategoryComboBox'),
            'cost': w_line('updateCostPriceLineEdit'),
            'sell': w_line('updateSellingPriceLineEdit'),
            'unit': w_line('updateUnitLineEdit'),
            'supplier': w_line('updateSupplierLineEdit'),
            'last_updated': w_line('updateLastUpdatedLineEdit'),
            'status': w_lbl('updateStatusLabel'),
            'ok': w_btn('btnUpdateOk'),
            'cancel': w_btn('btnUpdateCancel'),
        },
    }

    # ---------------- HELPERS ----------------
    def set_status(mode: str, text: str, ok: bool = True):
        lbl = ui.get(mode, {}).get('status')
        if not lbl:
            return
        try:
            lbl.setText(text or '')
            lbl.setStyleSheet('color: #1b5e20;' if ok else 'color: #b71c1c;')
        except Exception:
            pass

    def norm_unit(raw: str) -> str:
        u = (raw or '').strip().upper()
        if not u:
            return ''
        if u in ('KG', 'KGS', 'KILOGRAM', 'KILOGRAMS'):
            return 'KG'
        if u in ('EACH', 'EA', 'PCS', 'PC', 'PIECE', 'PIECES'):
            return 'EACH'
        # keep it permissive but stable; default to EACH
        return 'EACH'

    def parse_money(raw: str) -> Optional[float]:
        s = (raw or '').strip()
        if not s:
            return None
        return float(s)

    def populate_categories(combo: Optional[QComboBox]):
        if not combo:
            return
        try:
            if combo.count() == 0:
                for txt in ['Other', 'Electronics', 'Food', 'Apparel']:
                    combo.addItem(txt)
        except Exception:
            pass

    def refresh_search_combos():
        # Product cache is assumed to be {code: (name, price, unit)} or compatible.
        names = sorted(set((v[0] or '').strip() for v in PRODUCT_CACHE.values() if v and v[0]))
        for mode in ('remove', 'update'):
            combo: QComboBox = ui[mode].get('search')
            if not combo:
                continue
            try:
                combo.blockSignals(True)
                combo.setEditable(True)
                combo.setInsertPolicy(QComboBox.NoInsert)
                combo.setEnabled(True)
                combo.clear()
                combo.addItems(names)
                combo.setCurrentIndex(-1)
                le = combo.lineEdit()
                if le:
                    le.setPlaceholderText('Search product name…')
                completer = QCompleter(names)
                completer.setCaseSensitivity(Qt.CaseInsensitive)
                completer.setFilterMode(Qt.MatchContains)
                combo.setCompleter(completer)
                combo.blockSignals(False)
            except Exception:
                try:
                    combo.blockSignals(False)
                except Exception:
                    pass

    def find_code_by_name(name: str) -> Optional[str]:
        if not name:
            return None
        needle = name.strip().lower()
        for code, tup in PRODUCT_CACHE.items():
            nm = (tup[0] if tup else '') or ''
            if nm.strip().lower() == needle:
                return str(code)
        return None

    def load_product_into_remove(code: str):
        found, pdata = get_product_full(code)
        if not found or not pdata:
            set_status('remove', 'Product not found.', ok=False)
            return
        ui['remove']['code'].setText(code)
        ui['remove']['name'].setText(pdata.get('name', ''))
        ui['remove']['category'].setText(pdata.get('category', ''))
        ui['remove']['cost'].setText(str(pdata.get('cost_price', '') or ''))
        ui['remove']['sell'].setText(str(pdata.get('price', '') or ''))
        ui['remove']['unit'].setText(pdata.get('unit', '') or '')
        if ui['remove'].get('supplier'):
            ui['remove']['supplier'].setText(pdata.get('supplier', '') or '')
        if ui['remove'].get('last_updated'):
            ui['remove']['last_updated'].setText(str(pdata.get('last_updated', '') or ''))
        set_status('remove', 'Product found.', ok=True)

    def load_product_into_update(code: str):
        found, pdata = get_product_full(code)
        if not found or not pdata:
            set_status('update', 'Product not found.', ok=False)
            return
        ui['update']['code'].setText(code)
        ui['update']['name'].setText(pdata.get('name', ''))
        combo = ui['update'].get('category')
        if combo:
            try:
                idx = combo.findText(pdata.get('category', ''), Qt.MatchFixedString)
                combo.setCurrentIndex(idx if idx >= 0 else 0)
            except Exception:
                pass
        ui['update']['cost'].setText(str(pdata.get('cost_price', '') or ''))
        ui['update']['sell'].setText(str(pdata.get('price', '') or ''))
        ui['update']['unit'].setText(pdata.get('unit', '') or '')
        ui['update']['supplier'].setText(pdata.get('supplier', '') or '')
        if ui['update'].get('last_updated'):
            ui['update']['last_updated'].setText(str(pdata.get('last_updated', '') or ''))
        set_status('update', 'Product found.', ok=True)

    def clear_mode_fields(mode: str, keep_code: bool = False):
        if mode == 'add':
            if not keep_code and ui['add']['code']:
                ui['add']['code'].clear()
            namew = ui['add']['name']
            if isinstance(namew, QLineEdit):
                namew.clear()
            elif isinstance(namew, QComboBox):
                namew.setCurrentIndex(-1)
            for k in ('cost', 'sell', 'unit', 'supplier'):
                le = ui['add'].get(k)
                if le:
                    le.clear()
            if ui['add'].get('category'):
                try:
                    ui['add']['category'].setCurrentIndex(0)
                except Exception:
                    pass
        elif mode in ('remove', 'update'):
            for k, w in ui[mode].items():
                if k in ('ok', 'cancel', 'search', 'status', 'category'):
                    continue
                if keep_code and k == 'code':
                    continue
                if isinstance(w, QLineEdit):
                    w.clear()
            # reset category combo for update
            if mode == 'update' and ui['update'].get('category'):
                try:
                    ui['update']['category'].setCurrentIndex(0)
                except Exception:
                    pass
            # clear search box selection too
            combo = ui[mode].get('search')
            if combo:
                try:
                    combo.setCurrentIndex(-1)
                    if combo.lineEdit():
                        combo.lineEdit().clear()
                except Exception:
                    pass

        set_status(mode, '', ok=True)

    # ---------------- ADD MODE: CODE DUPLICATE CHECK ----------------
    def set_add_code_error_state(is_error: bool, msg: str = ''):
        le = ui['add']['code']
        okbtn = ui['add'].get('ok')
        if le:
            try:
                le.setStyleSheet('border: 2px solid #b71c1c;' if is_error else '')
            except Exception:
                pass
        if okbtn:
            try:
                okbtn.setEnabled(not is_error)
            except Exception:
                pass
        if msg:
            set_status('add', msg, ok=not is_error)
        else:
            if is_error:
                set_status('add', 'Error: Product code already exists.', ok=False)
            else:
                set_status('add', '', ok=True)

    def on_add_code_changed(text: str):
        code = (text or '').strip()
        if not code:
            set_add_code_error_state(False, '')
            return
        try:
            c_found, *_ = get_product_info(code)
            if c_found:
                set_add_code_error_state(True)
                return
        except Exception:
            pass
        try:
            d_found, _pdata = get_product_full(code)
            if d_found:
                set_add_code_error_state(True)
                return
        except Exception:
            pass
        set_add_code_error_state(False, '')

    # ---------------- SEARCH COMBOS: REMOVE/UPDATE ----------------
    def on_remove_search_selected(name: str):
        code = find_code_by_name(name)
        if not code:
            set_status('remove', 'Product not found.', ok=False)
            return
        load_product_into_remove(code)

    def on_update_search_selected(name: str):
        code = find_code_by_name(name)
        if not code:
            set_status('update', 'Product not found.', ok=False)
            return
        load_product_into_update(code)

    def wire_search_combo(combo: Optional[QComboBox], handler):
        if not combo:
            return
        try:
            combo.activated[str].connect(handler)
        except Exception:
            pass
        # Enter key on editable line edit
        try:
            le = combo.lineEdit()
            if le:
                le.returnPressed.connect(lambda c=combo: handler(c.currentText()))
        except Exception:
            pass
        # completer selection
        try:
            comp = combo.completer()
            if comp:
                comp.activated[str].connect(handler)
        except Exception:
            pass

    # ---------------- OK ACTIONS ----------------
    def do_add():
        code_le = ui['add']['code']
        if not code_le:
            return
        code = (code_le.text() or '').strip()
        namew = ui['add']['name']
        name = ''
        if isinstance(namew, QLineEdit):
            name = (namew.text() or '').strip()
        elif isinstance(namew, QComboBox):
            name = (namew.currentText() or '').strip()

        sell = (ui['add']['sell'].text() or '').strip() if ui['add'].get('sell') else ''
        cat = (ui['add']['category'].currentText() or '').strip() if ui['add'].get('category') else ''
        unit = norm_unit(ui['add']['unit'].text() if ui['add'].get('unit') else '')

        missing = []
        if not code:
            missing.append('Product Code')
        if not name:
            missing.append('Product Name')
        if not sell:
            missing.append('Selling Price')
        if not cat:
            missing.append('Category')
        if not unit:
            missing.append('Unit')

        if missing:
            set_status('add', 'Error: Please provide ' + ', '.join(missing), ok=False)
            return

        try:
            price_val = parse_money(sell)
            if price_val is None:
                raise ValueError('Invalid Selling Price')
        except Exception:
            set_status('add', 'Error: Selling Price must be a number.', ok=False)
            return

        cost_raw = (ui['add']['cost'].text() or '').strip() if ui['add'].get('cost') else ''
        cost_val = 0.0
        if cost_raw:
            try:
                cost_val = float(cost_raw)
            except Exception:
                set_status('add', 'Error: Cost Price must be a number.', ok=False)
                return

        supplier = (ui['add']['supplier'].text() or '').strip() if ui['add'].get('supplier') else ''

        now_str = QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss')
        try:
            ok, msg = add_product(code, name, price_val, cat, supplier, cost_val, unit, now_str)
            if not ok:
                set_status('add', f'Error: {msg}', ok=False)
                return
        except Exception as e:
            set_status('add', f'Error: {e}', ok=False)
            return

        try:
            refresh_product_cache()
        except Exception:
            pass
        refresh_search_combos()

        set_status('add', 'Added successfully.', ok=True)

        # If dialog was launched due to scan during sales, auto-add to sales table
        try:
            code_to_add = (str(initial_code).strip() if initial_code else code)
            if code_to_add and getattr(main_window, 'sales_table', None) is not None:
                status_bar = getattr(main_window, 'statusbar', None)
                QTimer.singleShot(0, lambda c=code_to_add, sb=status_bar: handle_barcode_scanned(main_window.sales_table, c, sb))
        except Exception:
            pass

        QTimer.singleShot(800, dlg.accept)

    def do_remove():
        code = (ui['remove']['code'].text() or '').strip() if ui['remove'].get('code') else ''
        if not code:
            set_status('remove', 'Error: Provide Product Code to delete.', ok=False)
            return
        try:
            ok, msg = delete_product(code)
            if not ok:
                set_status('remove', f'Error: {msg}', ok=False)
                return
        except Exception as e:
            set_status('remove', f'Error: {e}', ok=False)
            return

        try:
            refresh_product_cache()
        except Exception:
            pass
        refresh_search_combos()

        set_status('remove', 'Deleted successfully.', ok=True)
        QTimer.singleShot(800, dlg.accept)

    def do_update():
        code = (ui['update']['code'].text() or '').strip() if ui['update'].get('code') else ''
        name = (ui['update']['name'].text() or '').strip() if ui['update'].get('name') else ''
        sell = (ui['update']['sell'].text() or '').strip() if ui['update'].get('sell') else ''
        cat = (ui['update']['category'].currentText() or '').strip() if ui['update'].get('category') else ''
        unit = norm_unit(ui['update']['unit'].text() if ui['update'].get('unit') else '')

        missing = []
        if not code:
            missing.append('Product Code')
        if not name:
            missing.append('Product Name')
        if not sell:
            missing.append('Selling Price')
        if not cat:
            missing.append('Category')
        if not unit:
            missing.append('Unit')
        if missing:
            set_status('update', 'Error: Please provide ' + ', '.join(missing), ok=False)
            return

        # ensure exists before update
        try:
            exists, _pdata = get_product_full(code)
            if not exists:
                set_status('update', 'Error: Product code not found.', ok=False)
                return
        except Exception:
            pass

        try:
            price_val = parse_money(sell)
            if price_val is None:
                raise ValueError('Invalid Selling Price')
        except Exception:
            set_status('update', 'Error: Selling Price must be a number.', ok=False)
            return

        cost_raw = (ui['update']['cost'].text() or '').strip() if ui['update'].get('cost') else ''
        cost_val = 0.0
        if cost_raw:
            try:
                cost_val = float(cost_raw)
            except Exception:
                set_status('update', 'Error: Cost Price must be a number.', ok=False)
                return

        supplier = (ui['update']['supplier'].text() or '').strip() if ui['update'].get('supplier') else ''

        try:
            ok, msg = update_product(code, name, price_val, cat, supplier, cost_val, unit)
            if not ok:
                set_status('update', f'Error: {msg}', ok=False)
                return
        except Exception as e:
            set_status('update', f'Error: {e}', ok=False)
            return

        # update last updated field in UI (if present)
        if ui['update'].get('last_updated'):
            try:
                ui['update']['last_updated'].setText(QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss'))
            except Exception:
                pass

        try:
            refresh_product_cache()
        except Exception:
            pass
        refresh_search_combos()

        set_status('update', 'Updated successfully.', ok=True)
        QTimer.singleShot(800, dlg.accept)

    # ---------------- WIRING ----------------
    # Category combos
    populate_categories(ui['add'].get('category'))
    populate_categories(ui['update'].get('category'))

    # Search combos
    refresh_search_combos()
    wire_search_combo(ui['remove'].get('search'), on_remove_search_selected)
    wire_search_combo(ui['update'].get('search'), on_update_search_selected)

    # Buttons: connect once per button (no tab-scoped rebinding)
    def safe_connect(btn: Optional[QPushButton], fn):
        if not btn:
            return
        try:
            btn.clicked.disconnect()
        except Exception:
            pass
        try:
            btn.clicked.connect(fn)
        except Exception:
            pass

    safe_connect(ui['add'].get('ok'), do_add)
    safe_connect(ui['remove'].get('ok'), do_remove)
    safe_connect(ui['update'].get('ok'), do_update)

    safe_connect(ui['add'].get('cancel'), lambda: (clear_mode_fields('add', keep_code=False), dlg.reject()))
    safe_connect(ui['remove'].get('cancel'), lambda: (clear_mode_fields('remove', keep_code=False), dlg.reject()))
    safe_connect(ui['update'].get('cancel'), lambda: (clear_mode_fields('update', keep_code=False), dlg.reject()))

    # Add code validation
    if ui['add'].get('code'):
        try:
            ui['add']['code'].textChanged.disconnect()
        except Exception:
            pass
        ui['add']['code'].textChanged.connect(on_add_code_changed)

    # Return pressed on remove/update code fields to load product
    if ui['remove'].get('code'):
        ui['remove']['code'].returnPressed.connect(lambda: load_product_into_remove(ui['remove']['code'].text().strip()))
    if ui['update'].get('code'):
        ui['update']['code'].returnPressed.connect(lambda: load_product_into_update(ui['update']['code'].text().strip()))

    # Tab switching: focus appropriate code field
    def mode_from_index(idx: int) -> str:
        return 'add' if idx == 0 else ('remove' if idx == 1 else 'update')

    def focus_code_for_mode(mode: str):
        le = ui[mode].get('code')
        if le:
            try:
                le.setFocus()
                le.selectAll()
            except Exception:
                pass

    # Sales-active rule: if opened from barcode scan with no explicit mode, lock to ADD.
    sale_active = (initial_mode is None and initial_code is not None)

    def set_mode_tabs_enabled(enabled: bool):
        if not tab_widget:
            return
        try:
            # keep Add enabled always
            tab_widget.setTabEnabled(1, enabled)
            tab_widget.setTabEnabled(2, enabled)
        except Exception:
            pass

    if tab_widget is not None:
        if sale_active:
            set_mode_tabs_enabled(False)
            try:
                tab_widget.setCurrentIndex(0)
            except Exception:
                pass
        else:
            # choose initial tab by initial_mode if given
            m = (initial_mode or '').strip().lower()
            idx = 0 if m == 'add' else (1 if m == 'remove' else (2 if m == 'update' else 0))
            try:
                tab_widget.setCurrentIndex(idx)
            except Exception:
                pass

        def _on_tab(idx: int):
            if sale_active and idx != 0:
                try:
                    tab_widget.blockSignals(True)
                    tab_widget.setCurrentIndex(0)
                    tab_widget.blockSignals(False)
                except Exception:
                    pass
                return
            focus_code_for_mode(mode_from_index(idx))

        tab_widget.currentChanged.connect(_on_tab)

    # Initial code injection
    if initial_code:
        code = str(initial_code).strip()
        if sale_active:
            if ui['add'].get('code'):
                ui['add']['code'].setText(code)
        else:
            m = (initial_mode or '').strip().lower()
            if m == 'remove':
                if ui['remove'].get('code'):
                    ui['remove']['code'].setText(code)
                    load_product_into_remove(code)
            elif m == 'update':
                if ui['update'].get('code'):
                    ui['update']['code'].setText(code)
                    load_product_into_update(code)
            else:
                if ui['add'].get('code'):
                    ui['add']['code'].setText(code)

    # Barcode override: only for search combos (by name) when those widgets are focused
    prev_override = getattr(main_window, '_barcodeOverride', None)
    prev_mgr_override = None
    try:
        if hasattr(main_window, 'barcode_manager'):
            prev_mgr_override = getattr(main_window.barcode_manager, '_barcodeOverride', None)
    except Exception:
        prev_mgr_override = None

    def _barcode_to_product_name(raw: str) -> bool:
        try:
            if not raw:
                return False
            inst = QApplication.instance()
            fw = inst.focusWidget() if inst else None
            txt = raw.strip()
            # If focus is on search combo line edit, try to select matching name
            for mode, handler in (('remove', on_remove_search_selected), ('update', on_update_search_selected)):
                combo = ui[mode].get('search')
                if not combo:
                    continue
                le = combo.lineEdit()
                if fw is combo or fw is le:
                    for i in range(combo.count()):
                        if txt.lower() == combo.itemText(i).strip().lower():
                            combo.setCurrentIndex(i)
                            handler(combo.itemText(i))
                            return True
            return False
        except Exception:
            return False

    try:
        main_window._barcodeOverride = _barcode_to_product_name
        if hasattr(main_window, 'barcode_manager'):
            main_window.barcode_manager._barcodeOverride = _barcode_to_product_name
    except Exception:
        pass

    def _restore_overrides():
        try:
            main_window._barcodeOverride = prev_override
        except Exception:
            pass
        try:
            if hasattr(main_window, 'barcode_manager'):
                main_window.barcode_manager._barcodeOverride = prev_mgr_override
        except Exception:
            pass

    dlg.finished.connect(lambda _=None: _restore_overrides())

    # Focus initial
    if tab_widget is not None:
        focus_code_for_mode(mode_from_index(tab_widget.currentIndex()))
    else:
        focus_code_for_mode('add')

    return dlg
