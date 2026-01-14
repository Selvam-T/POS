"""Product Management dialog controller (product_menu.py).

Key requirements implemented:
- Two entry routes:
  1) Menu button: full ADD/REMOVE/UPDATE tabs enabled.
  2) Sales-frame missing barcode: lands on ADD tab with product code prefilled, and REMOVE/UPDATE tabs disabled.
- Focus: whenever tab changes, focus lands on the tab's *ProductCodeLineEdit.
- Scanner: dialog is launched via dialog_wrapper.open_dialog_scanner_enabled(); barcode scans are routed via
  barcode_manager override into the active tab's *ProductCodeLineEdit, and then loaders populate fields.
- Display-only QLineEdit: readOnly + NoFocus to keep consistent UI border styling.

Notes:
- DB / cache operations use modules.db_operation functions and refresh PRODUCT_CACHE after CRUD.
- When launched from sales-frame (sale_active), a successful ADD triggers an immediate re-process of the barcode
  into the sales table via modules.table.handle_barcode_scanned (same pattern as your original controller).
"""

from __future__ import annotations

from typing import Optional, Dict, Any
import os

from PyQt5 import uic
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox, QTabWidget, QWidget, QCompleter
)
from PyQt5.QtCore import Qt, QDateTime, QTimer

from modules.db_operation import (
    add_product, update_product, delete_product,
    get_product_full, PRODUCT_CACHE
)
from modules.db_operation.product_cache import _to_camel_case
import modules.db_operation as dbop
from modules.table import handle_barcode_scanned

from modules.ui_utils import input_validation
from modules.ui_utils import ui_feedback
from modules.ui_utils.focus_utils import FieldCoordinator
from modules.ui_utils import input_handler
from modules.ui_utils import error_logger

from modules.menu.dialog_utils import load_ui_strict, report_exception

# Derive project base dir from this file location: modules/menu -> modules -> Project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
QSS_PATH = os.path.join(ASSETS_DIR, 'menu.qss')
UI_PATH = os.path.join(UI_DIR, 'product_menu.ui')

DEFAULT_UNIT = _to_camel_case('Each')
DEFAULT_CATEGORY = _to_camel_case('Other')


def _load_stylesheet() -> str:
    try:
        if os.path.exists(QSS_PATH):
            with open(QSS_PATH, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception:
        pass
    return ''


def open_dialog_scanner_enabled(main_window, initial_mode: Optional[str] = None, initial_code: Optional[str] = None) -> QDialog:
    """Create the Product Management dialog and return it (do not exec_ here)."""

    # Business rule: if opened from sales-frame scan and no explicit mode, lock to ADD.
    sale_active = (initial_code is not None and (initial_mode is None or str(initial_mode).strip().lower() in ('', 'add')))

    # Additional safety rule: if there are items in the current transaction, lock to ADD only.
    sale_in_progress = False
    try:
        sales_table = getattr(main_window, 'sales_table', None)
        sale_in_progress = (sales_table is not None and getattr(sales_table, 'rowCount', lambda: 0)() > 0)
    except Exception:
        sale_in_progress = False

    sale_lock = bool(sale_active or sale_in_progress)

    # ---- dialog + ui load ----
    content = load_ui_strict(UI_PATH, host_window=main_window, dialog_name='Product menu')
    if content is None:
        return None

    # Wrap in QDialog if needed (UI top-level is usually a QDialog)
    if isinstance(content, QDialog):
        dlg = content
        dlg.setParent(main_window)
    else:
        dlg = QDialog(main_window)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(content)

    dlg.setObjectName("productMenuDialog")

    # Frameless + modal (prevents OS titlebar in addition to your custom titlebar)
    dlg.setModal(True)
    dlg.setWindowModality(Qt.ApplicationModal)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)

    # Apply stylesheet (optional)
    qss = _load_stylesheet()
    if qss:
        try:
            dlg.setStyleSheet(qss)
        except Exception:
            pass

    # Wire custom window close button (if present)
    custom_close_btn = dlg.findChild(QPushButton, 'customCloseBtn')
    if custom_close_btn is not None:
        custom_close_btn.clicked.connect(dlg.reject)

    tab_widget: Optional[QTabWidget] = dlg.findChild(QTabWidget, 'tabWidget')

    # If opened from sales-frame missing barcode OR sale already has items, lock to ADD only
    if tab_widget is not None and sale_lock:
        try:
            tab_widget.setTabEnabled(1, False)  # REMOVE
            tab_widget.setTabEnabled(2, False)  # UPDATE
            tab_widget.setCurrentIndex(0)
        except Exception:
            pass


    # ---- helpers ----
    def w_line(name: str) -> Optional[QLineEdit]:
        return dlg.findChild(QLineEdit, name)

    def w_combo(name: str) -> Optional[QComboBox]:
        return dlg.findChild(QComboBox, name)

    def w_lbl(name: str) -> Optional[QLabel]:
        return dlg.findChild(QLabel, name)

    def w_btn(name: str) -> Optional[QPushButton]:
        return dlg.findChild(QPushButton, name)

    ui: Dict[str, Dict[str, Any]] = {
        'add': {
            'code': w_line('addProductCodeLineEdit'),
            'name': w_line('addProductNameLineEdit'),
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
            'name_search': w_line('removeNameSearchLineEdit'),
            'code': w_line('removeProductCodeLineEdit'),
            'category': w_line('removeCategoryLineEdit'),
            'cost': w_line('removeCostPriceLineEdit'),
            'sell': w_line('removeSellingPriceLineEdit'),
            'unit': w_line('removeUnitLineEdit'),
            'supplier': w_line('removeSupplierLineEdit'),
            'last_updated': w_line('removeLastUpdatedLineEdit'),
            'status': w_lbl('removeStatusLabel'),
            'ok': w_btn('btnRemoveOk'),
            'cancel': w_btn('btnRemoveCancel'),
        },
        'update': {
            'name_search': w_line('updateNameSearchLineEdit'),
            'code': w_line('updateProductCodeLineEdit'),
            'name': w_line('updateProductNameLineEdit'),
            'category': w_combo('updateCategoryComboBox'),
            'cost': w_line('updateCostPriceLineEdit'),
            'sell': w_line('updateSellingPriceLineEdit'),
            'unit': w_line('updateUnitLineEdit'),
            'supplier': w_line('updateSupplierLineEdit'),
            'last_updated': w_line('updateLastUpdatedLineEdit'),
            'status': w_lbl('updateStatusLabel'),
            'ok': w_btn('btnUpdateOk'),
            'cancel': w_btn('btnUpdateCancel'),
        }
    }

    # ---- ADD tab gating: block other inputs until product code is valid ----
    def set_add_inputs_enabled(enabled: bool) -> None:
        for key in ('name', 'sell', 'cost', 'category', 'supplier', 'ok'):
            w = ui['add'].get(key)
            try:
                if w is not None:
                    w.setEnabled(bool(enabled))
            except Exception:
                pass

    def add_code_validity(code: str):
        c = (code or '').strip()
        if not c:
            return False, None
        if is_forbidden_code(c):
            return False, forbidden_msg()
        # check duplicate
        try:
            if str(c).strip().casefold() in {str(k).strip().casefold() for k in (PRODUCT_CACHE or {}).keys()}:
                return False, 'Error: Product Code already exists.'
        except Exception:
            pass
        return True, None

    def update_add_code_gate() -> None:
        code_le = ui['add'].get('code')
        if not isinstance(code_le, QLineEdit):
            return
        txt = (code_le.text() or '').strip()
        ok, msg = add_code_validity(txt)
        if not txt:
            set_add_inputs_enabled(False)
            clear_status('add')
            return
        if not ok:
            set_add_inputs_enabled(False)
            if msg:
                set_status('add', msg, ok=False)
            try:
                # Keep the user anchored on code field if they tried to proceed
                if dlg.focusWidget() is not code_le:
                    QTimer.singleShot(0, lambda: code_le.setFocus(Qt.OtherFocusReason))
            except Exception:
                pass
            return
        # valid
        set_add_inputs_enabled(True)
        clear_status('add')

    # ---- basic widget policies per your table ----
    # Product code fields: allow keyboard + scanner input.
    for mode in ('add', 'remove', 'update'):
        le: Optional[QLineEdit] = ui[mode].get('code')
        if le is not None:
            le.setFocusPolicy(Qt.StrongFocus)

    # Display-only helpers
    def set_display_only(le: Optional[QLineEdit], default_text: str = ''):
        if le is None:
            return
        le.setReadOnly(True)
        le.setFocusPolicy(Qt.NoFocus)
        if default_text:
            le.setText(default_text)

    # Default value + display-only
    set_display_only(ui['add'].get('unit'), DEFAULT_UNIT)
    set_display_only(ui['update'].get('unit'), DEFAULT_UNIT)
    set_display_only(ui['update'].get('last_updated'))
    set_display_only(ui['remove'].get('category'))
    set_display_only(ui['remove'].get('cost'))
    set_display_only(ui['remove'].get('sell'))
    set_display_only(ui['remove'].get('unit'))
    set_display_only(ui['remove'].get('supplier'))
    set_display_only(ui['remove'].get('last_updated'))

    # Category combos: selection only
    for mode in ('add', 'update'):
        combo: Optional[QComboBox] = ui[mode].get('category')
        if combo is not None:
            combo.setEditable(False)

    # ---- reserved vegetable codes (managed only via vegetable_menu) ----
    def _veg_number_from_code(raw: str) -> Optional[int]:
        s = (raw or '').strip()
        if not s:
            return None
        if len(s) < 4:
            return None
        if s[:3].casefold() != 'veg':
            return None
        tail = s[3:]
        try:
            n = int(tail)
        except Exception:
            return None
        return n

    def is_forbidden_code(code: str) -> bool:
        n = _veg_number_from_code(code)
        return n is not None and 1 <= n <= 16

    def forbidden_msg() -> str:
        return 'Forbidden barcode'

    # ---- sale_active tab lock ----
    def set_mode_tabs_enabled(enabled: bool):
        if not tab_widget:
            return
        try:
            tab_widget.setTabEnabled(1, enabled)  # REMOVE
            tab_widget.setTabEnabled(2, enabled)  # UPDATE
        except Exception:
            pass

    if tab_widget is not None:
        if sale_lock:
            set_mode_tabs_enabled(False)
            try:
                tab_widget.setCurrentIndex(0)
            except Exception:
                pass
        else:
            mode = (initial_mode or '').strip().lower()
            idx = {'add': 0, 'remove': 1, 'update': 2}.get(mode, 0)
            tab_widget.setCurrentIndex(idx)

    # ---- status helpers ----
    def set_status(mode: str, msg: str, ok: bool) -> bool:
        lbl: Optional[QLabel] = ui.get(mode, {}).get('status')
        if not lbl:
            return False
        return ui_feedback.set_status_label(lbl, msg, ok)

    def clear_status(mode: str) -> bool:
        lbl: Optional[QLabel] = ui.get(mode, {}).get('status')
        if not lbl:
            return False
        return ui_feedback.clear_status_label(lbl)

    # ---- cache/name helpers ----
    def get_allowed_product_names() -> list:
        names = []
        for code, rec in (PRODUCT_CACHE or {}).items():
            if not rec:
                continue
            if is_forbidden_code(str(code)):
                continue
            nm = (rec[0] or '').strip()
            if nm:
                names.append(nm)
        return sorted(set(names), key=lambda x: x.casefold())

    def refresh_name_completers() -> Dict[str, Optional[QCompleter]]:
        names = get_allowed_product_names()
        out: Dict[str, Optional[QCompleter]] = {'remove': None, 'update': None}
        for mode in ('remove', 'update'):
            le: Optional[QLineEdit] = ui[mode].get('name_search')
            if not isinstance(le, QLineEdit):
                continue
            try:
                out[mode] = input_handler.setup_name_search_lineedit(le, names)
            except Exception:
                out[mode] = None
        return out

    def find_code_by_exact_name(name: str) -> Optional[str]:
        needle = (name or '').strip().casefold()
        if not needle:
            return None
        for code, tup in PRODUCT_CACHE.items():
            if is_forbidden_code(str(code)):
                continue
            nm = (tup[0] if tup else '') or ''
            if nm.strip().casefold() == needle:
                return str(code)
        return None

    def lookup_full_by_code(mode: str, code: str):
        c = (code or '').strip()
        if not c:
            return None, None
        if is_forbidden_code(c):
            return None, forbidden_msg()
        try:
            found, pdata = get_product_full(c)
        except Exception as e:
            report_exception(main_window, f'ProductMenu: get_product_full({c})', e, user_message='Error: DB read failed')
            return None, 'DB error'
        if not found or not pdata:
            return None, 'Product not found'
        # Normalize to coordinator keys
        out = {
            'code': str(c),
            'name_search': _to_camel_case(pdata.get('name', '')) or '',
            'name': _to_camel_case(pdata.get('name', '')) or '',
            'category': _to_camel_case(pdata.get('category', '')) or '',
            'cost': str(pdata.get('cost', '') or ''),
            'sell': str(pdata.get('price', '') or ''),
            'unit': _to_camel_case(pdata.get('unit', '')) or DEFAULT_UNIT,
            'supplier': _to_camel_case(pdata.get('supplier', '')) or '',
            'last_updated': str(pdata.get('last_updated', '') or ''),
        }
        return out, None

    def lookup_full_by_name(mode: str, name: str):
        n = (name or '').strip()
        if not n:
            return None, None
        code = find_code_by_exact_name(n)
        if not code:
            return None, 'Product not found'
        return lookup_full_by_code(mode, code)

    # ---- populate loaders (REMOVE/UPDATE) ----
    def load_product_into_remove(code: str):
        if is_forbidden_code(code):
            set_status('remove', forbidden_msg(), ok=False)
            return
        try:
            found, pdata = get_product_full(code)
        except Exception as e:
            report_exception(main_window, f'ProductMenu: get_product_full({code})', e, user_message='Error: DB read failed')
            set_status('remove', 'Error: DB read failed.', ok=False)
            return
        if not found or not pdata:
            set_status('remove', 'Product not found.', ok=False)
            return
        if ui['remove'].get('name_search'):
            ui['remove']['name_search'].setText(_to_camel_case(pdata.get('name', '')) or '')
        if ui['remove'].get('category'):
            ui['remove']['category'].setText(_to_camel_case(pdata.get('category', '')) or '')
        if ui['remove'].get('cost'):
            ui['remove']['cost'].setText(str(pdata.get('cost', '') or ''))
        if ui['remove'].get('sell'):
            ui['remove']['sell'].setText(str(pdata.get('price', '') or ''))
        if ui['remove'].get('unit'):
            ui['remove']['unit'].setText(_to_camel_case(pdata.get('unit', '')) or DEFAULT_UNIT)
        if ui['remove'].get('supplier'):
            ui['remove']['supplier'].setText(_to_camel_case(pdata.get('supplier', '')) or '')
        if ui['remove'].get('last_updated'):
            ui['remove']['last_updated'].setText(str(pdata.get('last_updated', '') or ''))
        set_status('remove', 'Product found.', ok=True)

    def load_product_into_update(code: str):
        if is_forbidden_code(code):
            set_status('update', forbidden_msg(), ok=False)
            return
        try:
            found, pdata = get_product_full(code)
        except Exception as e:
            report_exception(main_window, f'ProductMenu: get_product_full({code})', e, user_message='Error: DB read failed')
            set_status('update', 'Error: DB read failed.', ok=False)
            return
        if not found or not pdata:
            set_status('update', 'Product not found.', ok=False)
            return
        ui['update']['name'].setText(_to_camel_case(pdata.get('name', '')) or '')
        combo = ui['update'].get('category')
        if combo:
            try:
                cat_val = _to_camel_case(pdata.get('category', '')) or DEFAULT_CATEGORY
                idx = combo.findText(cat_val, Qt.MatchFixedString)
                combo.setCurrentIndex(idx if idx >= 0 else 0)
            except Exception:
                pass
        ui['update']['cost'].setText(str(pdata.get('cost', '') or ''))
        ui['update']['sell'].setText(str(pdata.get('price', '') or ''))
        ui['update']['unit'].setText(_to_camel_case(pdata.get('unit', '')) or DEFAULT_UNIT)
        ui['update']['supplier'].setText(_to_camel_case(pdata.get('supplier', '')) or '')
        ui['update']['last_updated'].setText(str(pdata.get('last_updated', '') or ''))
        set_status('update', 'Product found.', ok=True)

    # ---- reset helpers ----
    def clear_mode_fields(mode: str):
        clear_status(mode)
        if mode == 'add':
            for key in ('code', 'name', 'cost', 'sell', 'supplier'):
                le = ui['add'].get(key)
                if isinstance(le, QLineEdit):
                    le.clear()
            if ui['add'].get('unit'):
                ui['add']['unit'].setText(DEFAULT_UNIT)
            combo = ui['add'].get('category')
            if isinstance(combo, QComboBox):
                try:
                    idx = combo.findText(DEFAULT_CATEGORY, Qt.MatchFixedString)
                    combo.setCurrentIndex(idx if idx >= 0 else 0)
                except Exception:
                    combo.setCurrentIndex(0)

        elif mode == 'remove':
            le = ui['remove'].get('name_search')
            if isinstance(le, QLineEdit):
                le.clear()
            for key in ('code', 'category', 'cost', 'sell', 'supplier', 'last_updated'):
                le = ui['remove'].get(key)
                if isinstance(le, QLineEdit):
                    le.clear()
            if ui['remove'].get('unit'):
                ui['remove']['unit'].setText(DEFAULT_UNIT)

        elif mode == 'update':
            le = ui['update'].get('name_search')
            if isinstance(le, QLineEdit):
                le.clear()
            for key in ('code', 'name', 'cost', 'sell', 'supplier', 'last_updated'):
                le = ui['update'].get(key)
                if isinstance(le, QLineEdit):
                    le.clear()
            if ui['update'].get('unit'):
                ui['update']['unit'].setText(DEFAULT_UNIT)
            combo_cat = ui['update'].get('category')
            if isinstance(combo_cat, QComboBox):
                try:
                    idx = combo_cat.findText(DEFAULT_CATEGORY, Qt.MatchFixedString)
                    combo_cat.setCurrentIndex(idx if idx >= 0 else 0)
                except Exception:
                    combo_cat.setCurrentIndex(0)

    def mode_from_index(idx: int) -> str:
        return {0: 'add', 1: 'remove', 2: 'update'}.get(idx, 'add')

    def focus_code_for_mode(mode: str):
        le = ui.get(mode, {}).get('code')
        if isinstance(le, QLineEdit):
            le.setFocus(Qt.OtherFocusReason)

    # ---- CRUD handlers (uses your db_operation signatures) ----
    def parse_money(raw: str) -> Optional[float]:
        s = (raw or '').strip()
        if not s:
            return None
        return float(s)

    def do_add():
        code = (ui['add']['code'].text() or '').strip() if ui['add'].get('code') else ''
        if is_forbidden_code(code):
            set_status('add', forbidden_msg(), ok=False)
            try:
                ui['add']['code'].setFocus(Qt.OtherFocusReason)
                ui['add']['code'].selectAll()
            except Exception:
                pass
            return
        name = _to_camel_case((ui['add']['name'].text() or '').strip()) if ui['add'].get('name') else ''
        sell = (ui['add']['sell'].text() or '').strip() if ui['add'].get('sell') else ''
        cat = _to_camel_case((ui['add']['category'].currentText() or '').strip()) if ui['add'].get('category') else DEFAULT_CATEGORY
        supplier = _to_camel_case((ui['add']['supplier'].text() or '').strip()) if ui['add'].get('supplier') else ''
        cost_raw = (ui['add']['cost'].text() or '').strip() if ui['add'].get('cost') else ''
        unit = (ui['add']['unit'].text() or '').strip() if ui['add'].get('unit') else DEFAULT_UNIT
        if not unit:
            unit = DEFAULT_UNIT
        # Canonicalize unit before saving
        from modules.table.unit_helpers import canonicalize_unit
        unit = canonicalize_unit(unit)

        ok, err = input_validation.is_mandatory(code)
        if not ok:
            set_status('add', f'Error: Product Code - {err}', ok=False)
            return
        ok, err = input_validation.is_mandatory(name)
        if not ok:
            set_status('add', f'Error: Product Name - {err}', ok=False)
            return
        ok, err = input_validation.is_mandatory(sell)
        if not ok:
            set_status('add', f'Error: Selling Price - {err}', ok=False)
            return

        # Ensure code does not already exist (cache is authoritative in runtime)
        ok, err = input_validation.exists_in_memory_cache(code, code_exists_in_cache)
        if ok:
            set_status('add', 'Error: Product Code already exists.', ok=False)
            return

        ok, err = input_validation.validate_unit_price(sell)
        if not ok:
            set_status('add', f'Error: Selling Price - {err}', ok=False)
            return
        price_val = float(sell)

        cost_val = 0.0
        if cost_raw:
            ok, err = input_validation.validate_total_price(cost_raw) if hasattr(input_validation, 'validate_total_price') else (True, '')
            if not ok:
                set_status('add', f'Error: Cost Price - {err}', ok=False)
                return
            cost_val = float(cost_raw)

        if cost_raw and price_val < cost_val:
            set_status('add', 'Error: Selling Price must be >= Cost Price', ok=False)
            return

        now_str = QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss')
        try:
            ok_db, msg = add_product(code, name, price_val, cat, supplier, cost_val, unit, now_str)
            if not ok_db:
                set_status('add', f'Error: {msg}', ok=False)
                return
        except Exception as e:
            report_exception(main_window, f'ProductMenu: add_product({code})', e, user_message='Error: Failed to add product')
            set_status('add', f'Error: {e}', ok=False)
            return

        set_status('add', 'Added successfully.', ok=True)

        try:
            dlg.main_status_msg = f"Product '{code}' added."
        except Exception:
            pass

        # If launched from sales, re-run scan so item appears in transaction
        if sale_active:
            try:
                code_to_add = (str(initial_code).strip() if initial_code else code)
                if code_to_add and getattr(main_window, 'sales_table', None) is not None:
                    status_bar = getattr(main_window, 'statusbar', None)
                    QTimer.singleShot(0, lambda c=code_to_add, sb=status_bar: handle_barcode_scanned(main_window.sales_table, c, sb))
            except Exception:
                pass

        QTimer.singleShot(500, dlg.accept)

    def do_remove():
        code = (ui['remove']['code'].text() or '').strip() if ui['remove'].get('code') else ''
        if is_forbidden_code(code):
            set_status('remove', forbidden_msg(), ok=False)
            return
        ok, err = input_validation.is_mandatory(code)
        if not ok:
            set_status('remove', f'Error: Product Code - {err}', ok=False)
            return

        # Ensure code exists before delete
        ok, err = input_validation.exists_in_memory_cache(code, code_exists_in_cache)
        if not ok:
            set_status('remove', f'Error: {err}', ok=False)
            return

        try:
            ok_db, msg = delete_product(code)
            if not ok_db:
                set_status('remove', f'Error: {msg}', ok=False)
                return
        except Exception as e:
            report_exception(main_window, f'ProductMenu: delete_product({code})', e, user_message='Error: Failed to delete product')
            set_status('remove', f'Error: {e}', ok=False)
            return

        set_status('remove', 'Deleted successfully.', ok=True)
        try:
            dlg.main_status_msg = f"Product '{code}' deleted."
        except Exception:
            pass
        QTimer.singleShot(500, dlg.accept)

    def do_update():
        code = (ui['update']['code'].text() or '').strip() if ui['update'].get('code') else ''
        if is_forbidden_code(code):
            set_status('update', forbidden_msg(), ok=False)
            return
        name = _to_camel_case((ui['update']['name'].text() or '').strip()) if ui['update'].get('name') else ''
        sell = (ui['update']['sell'].text() or '').strip() if ui['update'].get('sell') else ''
        cat = _to_camel_case((ui['update']['category'].currentText() or '').strip()) if ui['update'].get('category') else DEFAULT_CATEGORY
        supplier = _to_camel_case((ui['update']['supplier'].text() or '').strip()) if ui['update'].get('supplier') else ''
        cost_raw = (ui['update']['cost'].text() or '').strip() if ui['update'].get('cost') else ''
        unit = (ui['update']['unit'].text() or '').strip() if ui['update'].get('unit') else DEFAULT_UNIT
        if not unit:
            unit = DEFAULT_UNIT

        ok, err = input_validation.is_mandatory(code)
        if not ok:
            set_status('update', f'Error: Product Code - {err}', ok=False)
            return
        ok, err = input_validation.is_mandatory(name)
        if not ok:
            set_status('update', f'Error: Product Name - {err}', ok=False)
            return
        ok, err = input_validation.is_mandatory(sell)
        if not ok:
            set_status('update', f'Error: Selling Price - {err}', ok=False)
            return

        # Ensure code exists before update
        ok, err = input_validation.exists_in_memory_cache(code, code_exists_in_cache)
        if not ok:
            set_status('update', f'Error: {err}', ok=False)
            return

        ok, err = input_validation.validate_unit_price(sell)
        if not ok:
            set_status('update', f'Error: Selling Price - {err}', ok=False)
            return
        price_val = float(sell)

        cost_val = 0.0
        if cost_raw:
            ok, err = input_validation.validate_total_price(cost_raw) if hasattr(input_validation, 'validate_total_price') else (True, '')
            if not ok:
                set_status('update', f'Error: Cost Price - {err}', ok=False)
                return
            cost_val = float(cost_raw)

        if cost_raw and price_val < cost_val:
            set_status('update', 'Error: Selling Price must be >= Cost Price', ok=False)
            return

        try:
            ok_db, msg = update_product(code, name, price_val, cat, supplier, cost_val, unit)
            if not ok_db:
                set_status('update', f'Error: {msg}', ok=False)
                return
        except Exception as e:
            report_exception(main_window, f'ProductMenu: update_product({code})', e, user_message='Error: Failed to update product')
            set_status('update', f'Error: {e}', ok=False)
            return

        # UI display only (DB layer should set last_updated)
        if ui['update'].get('last_updated'):
            ui['update']['last_updated'].setText(QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss'))

        set_status('update', 'Updated successfully.', ok=True)
        try:
            dlg.main_status_msg = f"Product '{code}' updated."
        except Exception:
            pass
        QTimer.singleShot(500, dlg.accept)

    # ---- wiring ----
    completers = refresh_name_completers()

    # Build coordinator for Enter-to-next behavior + search synchronization
    coord = FieldCoordinator(dlg)

    # Gate ADD fields based on code validity
    add_code_le = ui['add'].get('code')
    if isinstance(add_code_le, QLineEdit):
        add_code_le.textChanged.connect(lambda _=None: update_add_code_gate())

    # ADD tab: focus flow (keep validation in OK; coordinator used for navigation + enter-swallow)
    if isinstance(ui['add'].get('code'), QLineEdit):
        def _add_code_lookup(val: str):
            update_add_code_gate()
            ok, msg = add_code_validity(val)
            if ok:
                return {'ok': True}, None
            return None, msg
        # No status_label here; update_add_code_gate sets messages without "Match Found".
        coord.add_link(source=ui['add']['code'], lookup_fn=_add_code_lookup, next_focus=ui['add'].get('name'))
    if isinstance(ui['add'].get('name'), QLineEdit):
        coord.add_link(source=ui['add']['name'], lookup_fn=None, next_focus=ui['add'].get('sell'))
    if isinstance(ui['add'].get('sell'), QLineEdit):
        coord.add_link(source=ui['add']['sell'], lookup_fn=None, next_focus=ui['add'].get('cost'))
    if isinstance(ui['add'].get('cost'), QLineEdit):
        coord.add_link(source=ui['add']['cost'], lookup_fn=None, next_focus=ui['add'].get('supplier'))
    if isinstance(ui['add'].get('supplier'), QLineEdit):
        coord.add_link(source=ui['add']['supplier'], lookup_fn=None, next_focus=lambda: ui['add']['ok'].click() if ui['add'].get('ok') else None)

    # REMOVE tab: name search -> populate, auto-jump to DELETE
    if isinstance(ui['remove'].get('name_search'), QLineEdit):
        coord.add_link(
            source=ui['remove']['name_search'],
            target_map={
                'code': ui['remove'].get('code'),
                'name_search': ui['remove'].get('name_search'),
                'category': ui['remove'].get('category'),
                'cost': ui['remove'].get('cost'),
                'sell': ui['remove'].get('sell'),
                'unit': ui['remove'].get('unit'),
                'supplier': ui['remove'].get('supplier'),
                'last_updated': ui['remove'].get('last_updated'),
            },
            lookup_fn=lambda val: lookup_full_by_name('remove', val),
            next_focus=lambda: ui['remove']['ok'].click() if ui['remove'].get('ok') else None,
            status_label=ui['remove'].get('status'),
            auto_jump=True
        )
    # REMOVE tab: code -> populate, Enter-to-DELETE
    if isinstance(ui['remove'].get('code'), QLineEdit):
        coord.add_link(
            source=ui['remove']['code'],
            target_map={
                'name_search': ui['remove'].get('name_search'),
                'category': ui['remove'].get('category'),
                'cost': ui['remove'].get('cost'),
                'sell': ui['remove'].get('sell'),
                'unit': ui['remove'].get('unit'),
                'supplier': ui['remove'].get('supplier'),
                'last_updated': ui['remove'].get('last_updated'),
            },
            lookup_fn=lambda val: lookup_full_by_code('remove', val),
            next_focus=lambda: ui['remove']['ok'].click() if ui['remove'].get('ok') else None,
            status_label=ui['remove'].get('status'),
            auto_jump=False
        )

    # UPDATE tab: name search -> populate, auto-jump to UPDATE
    if isinstance(ui['update'].get('name_search'), QLineEdit):
        coord.add_link(
            source=ui['update']['name_search'],
            target_map={
                'code': ui['update'].get('code'),
                'name_search': ui['update'].get('name_search'),
                'name': ui['update'].get('name'),
                'cost': ui['update'].get('cost'),
                'sell': ui['update'].get('sell'),
                'unit': ui['update'].get('unit'),
                'supplier': ui['update'].get('supplier'),
                'last_updated': ui['update'].get('last_updated'),
            },
            lookup_fn=lambda val: lookup_full_by_name('update', val),
            next_focus=lambda: ui['update']['ok'].click() if ui['update'].get('ok') else None,
            status_label=ui['update'].get('status'),
            auto_jump=True
        )
    # UPDATE tab: code -> populate, Enter-to-UPDATE
    if isinstance(ui['update'].get('code'), QLineEdit):
        coord.add_link(
            source=ui['update']['code'],
            target_map={
                'name_search': ui['update'].get('name_search'),
                'name': ui['update'].get('name'),
                'cost': ui['update'].get('cost'),
                'sell': ui['update'].get('sell'),
                'unit': ui['update'].get('unit'),
                'supplier': ui['update'].get('supplier'),
                'last_updated': ui['update'].get('last_updated'),
            },
            lookup_fn=lambda val: lookup_full_by_code('update', val),
            next_focus=lambda: ui['update']['ok'].click() if ui['update'].get('ok') else None,
            status_label=ui['update'].get('status'),
            auto_jump=False
        )

    # If completer is chosen, trigger coordinator sync (QCompleter already sets the line edit text)
    if completers.get('remove') and isinstance(ui['remove'].get('name_search'), QLineEdit):
        le = ui['remove']['name_search']
        try:
            completers['remove'].activated[str].connect(lambda _t: coord._sync_fields(le))
        except Exception:
            completers['remove'].activated.connect(lambda _t=None: coord._sync_fields(le))

    if completers.get('update') and isinstance(ui['update'].get('name_search'), QLineEdit):
        le = ui['update']['name_search']
        try:
            completers['update'].activated[str].connect(lambda _t: coord._sync_fields(le))
        except Exception:
            completers['update'].activated.connect(lambda _t=None: coord._sync_fields(le))

    # code change wiring (trigger loaders automatically on scan/programmatic setText)
    if isinstance(ui['remove'].get('code'), QLineEdit):
        ui['remove']['code'].textChanged.connect(lambda t: t and load_product_into_remove(t.strip()))
    if isinstance(ui['update'].get('code'), QLineEdit):
        ui['update']['code'].textChanged.connect(lambda t: t and load_product_into_update(t.strip()))

    # buttons
    if ui['add'].get('ok'):
        ui['add']['ok'].clicked.connect(do_add)
    if ui['remove'].get('ok'):
        ui['remove']['ok'].clicked.connect(do_remove)
    if ui['update'].get('ok'):
        ui['update']['ok'].clicked.connect(do_update)

    def do_cancel():
        try:
            dlg.main_status_msg = 'Product management cancelled.'
        except Exception:
            pass
        dlg.reject()

    for mode in ('add', 'remove', 'update'):
        btn = ui[mode].get('cancel')
        if isinstance(btn, QPushButton):
            btn.clicked.connect(do_cancel)

    # tab focus behavior
    def on_tab_changed(idx: int):
        mode = mode_from_index(idx)
        clear_status(mode)
        focus_code_for_mode(mode)

    if tab_widget is not None:
        tab_widget.currentChanged.connect(on_tab_changed)

    
    def code_exists_in_cache(code: str) -> bool:
        c = (code or '').strip().casefold()
        if not c:
            return False
        cache = getattr(dbop, 'PRODUCT_CACHE', None)
        if not cache:
            return False
        for k in cache:
            if str(k).strip().casefold() == c:
                return True
        return False

# ---- barcode override: route scans into active tab product code ----
    def barcode_override(barcode: str) -> bool:
        code = (barcode or '').strip()
        if not code:
            return False

        if is_forbidden_code(code):
            # Always report forbidden in the current mode
            mode = 'add'
            if tab_widget is not None:
                mode = mode_from_index(tab_widget.currentIndex())
            set_status(mode, forbidden_msg(), ok=False)
            try:
                focus_code_for_mode(mode)
                le = ui.get(mode, {}).get('code')
                if isinstance(le, QLineEdit):
                    le.selectAll()
            except Exception:
                pass
            return True

        # Determine current mode/tab
        mode = 'add'
        if tab_widget is not None:
            mode = mode_from_index(tab_widget.currentIndex())

        # If dialog opened due to a missing code from sales, always land on ADD
        if initial_code and tab_widget is not None:
            try:
                tab_widget.setCurrentIndex(0)
                mode = 'add'
            except Exception:
                pass

        le = ui.get(mode, {}).get('code')
        if not isinstance(le, QLineEdit):
            return False

        le.setText(code)

        if mode == 'add':
            if code_exists_in_cache(code):
                set_status('add', 'Error: Product Code already exists.', ok=False)
                update_add_code_gate()
                try:
                    le.setFocus(Qt.OtherFocusReason)
                    le.selectAll()
                except Exception:
                    pass
            else:
                clear_status('add')
                update_add_code_gate()
                name_le = ui['add'].get('name')
                if isinstance(name_le, QLineEdit):
                    try:
                        name_le.setFocus(Qt.OtherFocusReason)
                    except Exception:
                        pass
                else:
                    try:
                        le.deselect()
                        le.setCursorPosition(len(code))
                    except Exception:
                        pass
            return True

        # REMOVE/UPDATE: keep focus and allow loaders to populate (scan does not back-fill search combobox)
        try:
            le.setFocus(Qt.OtherFocusReason)
            le.deselect()
            le.setCursorPosition(len(code))
        except Exception:
            pass
        return True

    try:
        bm = getattr(main_window, 'barcode_manager', None)
        if bm is not None:
            if hasattr(bm, 'set_barcode_override'):
                bm.set_barcode_override(barcode_override)
            else:
                setattr(bm, '_barcodeOverride', barcode_override)
    except Exception:
        pass

    # ---- initial reset + landing ----
    clear_mode_fields('add')
    clear_mode_fields('remove')
    clear_mode_fields('update')

    # Initial gate state for ADD tab
    try:
        update_add_code_gate()
    except Exception:
        pass

    # Populate REMOVE/UPDATE search dropdowns once at dialog open
    try:
        refresh_name_completers()
        QTimer.singleShot(0, refresh_name_completers)
    except Exception:
        pass

    # Landing page always ADD + product code focus
    if tab_widget is not None:
        try:
            tab_widget.setCurrentIndex(0)
        except Exception:
            pass

    # If opened from sales scan, prefill product code in ADD
    if initial_code:
        try:
            barcode_override(str(initial_code))
        except Exception:
            pass

    if tab_widget is not None:
        focus_code_for_mode(mode_from_index(tab_widget.currentIndex()))
    else:
        focus_code_for_mode('add')

    return dlg
