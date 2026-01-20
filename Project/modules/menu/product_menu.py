import os
from PyQt5.QtWidgets import QLineEdit, QPushButton, QLabel, QComboBox, QTabWidget
from PyQt5.QtCore import Qt, QTimer, QDateTime

from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui, require_widgets, set_dialog_info, set_dialog_error
)
from modules.ui_utils.focus_utils import FieldCoordinator, FocusGate, enforce_exclusive_lineedits
from modules.ui_utils import input_handler, ui_feedback
from modules.db_operation import (
    PRODUCT_CACHE, get_product_full, add_product, update_product, delete_product
)
import modules.db_operation as dbop
from modules.db_operation.product_cache import PRODUCT_CODE_DISPLAY
from modules.ui_utils.input_validation import is_reserved_vegetable_code
from modules.table import handle_barcode_scanned
from modules.table.unit_helpers import canonicalize_unit
from config import PRODUCT_CATEGORIES

# Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_PATH = os.path.join(BASE_DIR, 'ui', 'product_menu.ui')
QSS_PATH = os.path.join(BASE_DIR, 'assets', 'dialog.qss')

def open_dialog_scanner_enabled(main_window, initial_mode=None, initial_code=None):
    from modules.table.table_operations import is_transaction_active
    sale_lock = is_transaction_active(getattr(main_window, 'sales_table', None))

    dlg = build_dialog_from_ui(UI_PATH, host_window=main_window, qss_path=QSS_PATH)
    if not dlg: return None

    widgets = require_widgets(dlg, {
        'tabs': (QTabWidget, 'tabWidget'),
        'close_btn': (QPushButton, 'customCloseBtn'),

        # ADD
        'add_code': (QLineEdit, 'addProductCodeLineEdit'),
        'add_name': (QLineEdit, 'addProductNameLineEdit'),
        'add_sell': (QLineEdit, 'addSellingPriceLineEdit'),
        'add_cost': (QLineEdit, 'addCostPriceLineEdit'),
        'add_markup': (QLineEdit, 'addMarkupLineEdit'),
        'add_cat': (QComboBox, 'addCategoryComboBox'),
        'add_unit': (QLineEdit, 'addUnitLineEdit'),
        'add_supp': (QLineEdit, 'addSupplierLineEdit'),
        'add_ok': (QPushButton, 'btnAddOk'),
        'add_cancel': (QPushButton, 'btnAddCancel'),
        'add_status': (QLabel, 'addStatusLabel'),

        # REMOVE
        'rem_code': (QLineEdit, 'removeProductCodeLineEdit'),
        'rem_name': (QLineEdit, 'removeNameSearchLineEdit'),
        'rem_category': (QLineEdit, 'removeCategoryLineEdit'),
        'rem_cost': (QLineEdit, 'removeCostPriceLineEdit'),
        'rem_sell': (QLineEdit, 'removeSellingPriceLineEdit'),
        'rem_unit': (QLineEdit, 'removeUnitLineEdit'),
        'rem_supplier': (QLineEdit, 'removeSupplierLineEdit'),
        'rem_last_updated': (QLineEdit, 'removeLastUpdatedLineEdit'),
        'rem_ok': (QPushButton, 'btnRemoveOk'),
        'rem_cancel': (QPushButton, 'btnRemoveCancel'),
        'rem_status': (QLabel, 'removeStatusLabel'),

        # UPDATE
        'upd_code': (QLineEdit, 'updateProductCodeLineEdit'),
        'upd_search': (QLineEdit, 'updateNameSearchLineEdit'),
        'upd_name': (QLineEdit, 'updateProductNameLineEdit'),
        'upd_sell': (QLineEdit, 'updateSellingPriceLineEdit'),
        'upd_cost': (QLineEdit, 'updateCostPriceLineEdit'),
        'upd_markup': (QLineEdit, 'updateMarkupLineEdit'),
        'upd_cat': (QComboBox, 'updateCategoryComboBox'),
        'upd_unit': (QLineEdit, 'updateUnitLineEdit'),
        'upd_supplier': (QLineEdit, 'updateSupplierLineEdit'),
        'upd_last_updated': (QLineEdit, 'updateLastUpdatedLineEdit'),
        'upd_ok': (QPushButton, 'btnUpdateOk'),
        'upd_cancel': (QPushButton, 'btnUpdateCancel'),
        'upd_status': (QLabel, 'updateStatusLabel'),
    })

    # Remember UI-provided placeholders/defaults so we can hide them while gated
    # and restore them later without hardcoding strings.
    _ui_placeholders: dict[QLineEdit, str] = {}
    _ui_texts: dict[QLineEdit, str] = {}

    def _remember_ui_for_lineedit(le: QLineEdit) -> None:
        if le is None:
            return
        if le not in _ui_placeholders:
            try:
                _ui_placeholders[le] = le.placeholderText() or ""
            except Exception:
                _ui_placeholders[le] = ""
        if le not in _ui_texts:
            try:
                _ui_texts[le] = le.text() or ""
            except Exception:
                _ui_texts[le] = ""

    def _set_lineedit_hints_visible(le: QLineEdit, visible: bool) -> None:
        if le is None:
            return
        _remember_ui_for_lineedit(le)
        try:
            le.setPlaceholderText(_ui_placeholders.get(le, "") if visible else "")
        except Exception:
            pass
        # Only restore UI default text when becoming visible and field is empty.
        if visible:
            try:
                if not (le.text() or "").strip():
                    le.setText(_ui_texts.get(le, ""))
            except Exception:
                pass

    # --- Shared UI setup ---
    def _configure_readonly_lineedit(le: QLineEdit) -> None:
        if le is None:
            return
        try:
            le.setReadOnly(True)
        except Exception:
            pass
        try:
            le.setFocusPolicy(Qt.NoFocus)
        except Exception:
            pass

    # Markup fields are always computed (never user-editable)
    for k in ('add_markup', 'upd_markup'):
        _configure_readonly_lineedit(widgets[k])

    for k in ('rem_category', 'rem_cost', 'rem_sell', 'rem_unit', 'rem_supplier', 'rem_last_updated'):
        _configure_readonly_lineedit(widgets[k])
    _configure_readonly_lineedit(widgets['upd_last_updated'])
    _configure_readonly_lineedit(widgets['upd_unit'])
    _configure_readonly_lineedit(widgets['add_unit'])

    # Category combos: config-only categories, with a first-item placeholder.
    # Placeholder text must come from the .ui (no hardcoded strings here).
    def _init_category_combo(combo: QComboBox) -> None:
        if combo is None:
            return
        try:
            placeholder = ""
            try:
                if combo.count() > 0:
                    placeholder = combo.itemText(0) or ""
            except Exception:
                placeholder = ""

            combo.blockSignals(True)
            combo.clear()
            if placeholder:
                combo.addItem(placeholder)
            # Avoid duplicating the placeholder if config already includes it.
            items = []
            for c in list(PRODUCT_CATEGORIES or []):
                s = (c or '').strip()
                if not s:
                    continue
                if placeholder and s.strip().lower() == placeholder.strip().lower():
                    continue
                if s not in items:
                    items.append(s)
            combo.addItems(items)
            combo.setCurrentIndex(0 if placeholder else -1)
        except Exception:
            pass
        finally:
            try:
                combo.blockSignals(False)
            except Exception:
                pass

    _init_category_combo(widgets['add_cat'])
    _init_category_combo(widgets['upd_cat'])

    # --- Markup Logic (fixed wiring) ---
    def _calculate_markup(*, sell_le: QLineEdit, cost_le: QLineEdit, markup_le: QLineEdit) -> None:
        
        try:
            sell_txt = (sell_le.text() or '').strip()
            cost_txt = (cost_le.text() or '').strip()
            both_empty = not sell_txt and not cost_txt
            only_sell = sell_txt and not cost_txt
            only_cost = not sell_txt and cost_txt
            if both_empty:
                markup_le.setText("")
                return
            if only_sell:
                sell = float(sell_txt)
                markup_le.setText("NA")
                return
            if only_cost:
                cost = float(cost_txt)
                markup_le.setText("NA")
                return
            sell = float(sell_txt)
            cost = float(cost_txt)
            if cost > 0:
                pct = ((sell - cost) / cost) * 100.0
                markup_le.setText(f"{pct:.1f}%")
            else:
                markup_le.setText("")
        except Exception:
            markup_le.setText("")

    def _wire_markup(*, sell_le: QLineEdit, cost_le: QLineEdit, markup_le: QLineEdit) -> None:
        def _recalc(_text=None):
            _calculate_markup(sell_le=sell_le, cost_le=cost_le, markup_le=markup_le)
        sell_le.textChanged.connect(_recalc)
        cost_le.textChanged.connect(_recalc)
        _recalc()

    _wire_markup(sell_le=widgets['add_sell'], cost_le=widgets['add_cost'], markup_le=widgets['add_markup'])
    _wire_markup(sell_le=widgets['upd_sell'], cost_le=widgets['upd_cost'], markup_le=widgets['upd_markup'])

    # --- Search Setup ---
    # Ensure we have a full cache so completers include all products.
    try:
        if not (dbop.PRODUCT_CACHE or {}):
            dbop.load_product_cache()
    except Exception:
        pass

    def _names_from_cache() -> list:
        out = []
        try:
            for rec in (dbop.PRODUCT_CACHE or {}).values():
                if rec and rec[0]:
                    out.append(rec[0])
        except Exception:
            return []
        # stable unique list
        seen = set()
        uniq = []
        for n in out:
            key = (n or '').strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            uniq.append(n)
        return uniq

    names = _names_from_cache()

    def _refresh_name_completers() -> None:
        """Refresh REMOVE/UPDATE name completers from the current PRODUCT_CACHE.

        QCompleter models are not automatically updated when PRODUCT_CACHE changes,
        so we reattach using a fresh name list.
        """
        try:
            new_names = _names_from_cache()

            def _rem_selected(_text=None, _le=None):
                _sync_source(widgets['rem_name'])
                try:
                    widgets['rem_ok'].setFocus()
                except Exception:
                    pass

            def _upd_selected(_text=None, _le=None):
                _sync_source(widgets['upd_search'])
                try:
                    widgets['upd_cancel'].setFocus()
                except Exception:
                    pass

            input_handler.setup_name_search_lineedit(
                widgets['rem_name'],
                new_names,
                on_selected=_rem_selected,
                trigger_on_finish=False,
            )
            input_handler.setup_name_search_lineedit(
                widgets['upd_search'],
                new_names,
                on_selected=_upd_selected,
                trigger_on_finish=False,
            )
        except Exception:
            pass

    # --- Lookup engine (single normalized shape) ---
    def _lookup_code_by_name(name: str) -> str | None:
        s = (name or '').strip().lower()
        if not s:
            return None
        for c, rec in (dbop.PRODUCT_CACHE or {}).items():
            try:
                if rec and (rec[0] or '').strip().lower() == s:
                    # Return display casing from cache map (no DB query needed).
                    try:
                        return PRODUCT_CODE_DISPLAY.get(c) or c
                    except Exception:
                        return c
            except Exception:
                continue
        return None

    def _lookup_product(code: str):
        code = (code or '').strip()
        if not code:
            return None, "Empty code"
        if is_reserved_vegetable_code(code):
            return None, "Reserved vegetable code"
        found, pdata = get_product_full(code)
        if not found:
            return None, "Product not found"
        # Prefer display casing from cache map.
        key = (code or '').strip().upper()
        code_disp = PRODUCT_CODE_DISPLAY.get(key) or (pdata.get('product_code') or code)
        return {
            'code': code_disp,
            'name_search': pdata.get('name') or '',
            'name': pdata.get('name') or '',
            'category': pdata.get('category') or '',
            'cost': str(pdata.get('cost') or ''),
            'sell': str(pdata.get('price') or ''),
            'unit': pdata.get('unit') or '',
            'supplier': pdata.get('supplier') or '',
            'last_updated': pdata.get('last_updated') or '',
        }, None

    # --- Coordinator Wiring ---
    coord = FieldCoordinator(dlg)

    # IMPORTANT: Do not include the active source QLineEdit inside its own target_map.
    # Otherwise FieldCoordinator will overwrite what the user is typing on every keystroke.

    rem_display_targets = {
        'category': widgets['rem_category'],
        'cost': widgets['rem_cost'],
        'sell': widgets['rem_sell'],
        'unit': widgets['rem_unit'],
        'supplier': widgets['rem_supplier'],
        'last_updated': widgets['rem_last_updated'],
    }

    rem_targets_from_code = {
        # Fill name when code matches
        'name_search': widgets['rem_name'],
        **rem_display_targets,
    }

    rem_targets_from_name = {
        # Fill code when name matches
        'code': widgets['rem_code'],
        **rem_display_targets,
    }

    upd_lineedit_targets = {
        'name': widgets['upd_name'],
        'cost': widgets['upd_cost'],
        'sell': widgets['upd_sell'],
        'unit': widgets['upd_unit'],
        'supplier': widgets['upd_supplier'],
        'last_updated': widgets['upd_last_updated'],
    }

    upd_targets_from_code = {
        # When code matches, also backfill name-search field
        'name_search': widgets['upd_search'],
        **upd_lineedit_targets,
    }

    upd_targets_from_name = {
        # When name matches, also backfill code field
        'code': widgets['upd_code'],
        **upd_lineedit_targets,
    }

    def _apply_category_to_combo(combo: QComboBox, value: str) -> None:
        if combo is None:
            return
        s = (value or '').strip()
        if not s:
            try:
                combo.setCurrentIndex(0)
            except Exception:
                pass
            return
        try:
            i = combo.findText(s)
            combo.setCurrentIndex(i if i >= 0 else 0)
        except Exception:
            pass

    def _set_combo_blank(combo: QComboBox) -> None:
        if combo is None:
            return
        try:
            combo.setCurrentIndex(-1)
        except Exception:
            pass

    def _rem_lookup(val: str):
        return _lookup_product(val)

    def _rem_lookup_by_name(val: str):
        code = _lookup_code_by_name(val)
        if not code:
            return None, "No match"
        return _lookup_product(code)

    def _upd_lookup(val: str):
        return _lookup_product(val)

    def _upd_lookup_by_name(val: str):
        code = _lookup_code_by_name(val)
        if not code:
            return None, "No match"
        return _lookup_product(code)

    def _on_upd_sync(result):
        # Coordinator only supports QLineEdit targets; combo needs manual sync.
        if not result:
            try:
                _set_upd_inputs_enabled(False)
            except Exception:
                pass
            return

        _apply_category_to_combo(widgets['upd_cat'], result.get('category'))
        try:
            _set_upd_inputs_enabled(True)
        except Exception:
            pass
        try:
            # Snapshot the loaded record for change detection.
            _upd_loaded['code'] = (result.get('code') or '').strip()
            _upd_loaded['name'] = (result.get('name') or '').strip()
            _upd_loaded['sell'] = float((result.get('sell') or 0) or 0)
            _upd_loaded['cost'] = float((result.get('cost') or 0) or 0)
            _upd_loaded['category'] = (result.get('category') or '').strip()
            _upd_loaded['supplier'] = (result.get('supplier') or '').strip()
        except Exception:
            pass

    coord.add_link(
        source=widgets['rem_code'],
        target_map=rem_targets_from_code,
        lookup_fn=_rem_lookup,
        next_focus=widgets['rem_ok'],
        status_label=widgets['rem_status'],
        auto_jump=True,
    )
    coord.add_link(
        source=widgets['rem_name'],
        target_map=rem_targets_from_name,
        lookup_fn=_rem_lookup_by_name,
        next_focus=widgets['rem_ok'],
        status_label=widgets['rem_status'],
        auto_jump=False,
    )
    coord.add_link(
        source=widgets['upd_code'],
        target_map=upd_targets_from_code,
        lookup_fn=_upd_lookup,
        next_focus=widgets['upd_name'],
        status_label=widgets['upd_status'],
        on_sync=_on_upd_sync,
        auto_jump=True,
    )
    coord.add_link(
        source=widgets['upd_search'],
        target_map=upd_targets_from_name,
        lookup_fn=_upd_lookup_by_name,
        next_focus=widgets['upd_cancel'],
        status_label=widgets['upd_status'],
        on_sync=_on_upd_sync,
        auto_jump=False,
    )

    def _sync_source(source_widget) -> None:
        try:
            coord._sync_fields(source_widget)
        except Exception:
            pass

    def _clear_remove_display() -> None:
        for w in rem_display_targets.values():
            try:
                w.clear()
            except Exception:
                pass
        try:
            ui_feedback.clear_status_label(widgets['rem_status'])
        except Exception:
            pass

    def _clear_update_display() -> None:
        # Keep sources intact; clear stale mapped values.
        for w in upd_lineedit_targets.values():
            try:
                w.clear()
            except Exception:
                pass
        try:
            ui_feedback.clear_status_label(widgets['upd_status'])
        except Exception:
            pass
        try:
            _set_upd_inputs_enabled(False)
        except Exception:
            pass
        try:
            _upd_loaded.clear()
        except Exception:
            pass

    # Completers: ensure selection triggers coordinator sync.
    _refresh_name_completers()

    # Enter-to-commit for name search:
    # - Map values on Enter
    # - Jump focus only when a match exists
    def _commit_rem_name() -> None:
        try:
            txt = widgets['rem_name'].text() or ''
        except Exception:
            txt = ''
        try:
            result, _err = _rem_lookup_by_name(txt)
        except Exception:
            result = None
        _sync_source(widgets['rem_name'])
        if result:
            try:
                widgets['rem_ok'].setFocus()
            except Exception:
                pass

    def _commit_upd_search() -> None:
        try:
            txt = widgets['upd_search'].text() or ''
        except Exception:
            txt = ''
        try:
            result, _err = _upd_lookup_by_name(txt)
        except Exception:
            result = None
        _sync_source(widgets['upd_search'])
        if result:
            try:
                widgets['upd_cancel'].setFocus()
            except Exception:
                pass

    try:
        widgets['rem_name'].returnPressed.connect(_commit_rem_name)
    except Exception:
        pass
    try:
        widgets['upd_search'].returnPressed.connect(_commit_upd_search)
    except Exception:
        pass

    # UX clarity: code-search vs name-search are mutually exclusive.
    enforce_exclusive_lineedits(
        widgets['rem_code'],
        widgets['rem_name'],
        on_switch_to_a=_clear_remove_display,
        on_switch_to_b=_clear_remove_display,
        clear_status_label=widgets['rem_status'],
    )
    enforce_exclusive_lineedits(
        widgets['upd_code'],
        widgets['upd_search'],
        on_switch_to_a=_clear_update_display,
        on_switch_to_b=_clear_update_display,
        clear_status_label=widgets['upd_status'],
    )

    # --- UPDATE gate (lock edit fields until successful lookup) ---
    upd_gate_widgets = [
        widgets['upd_name'], widgets['upd_sell'], widgets['upd_cost'],
        widgets['upd_cat'], widgets['upd_supplier'], widgets['upd_ok'],
    ]
    upd_gate = FocusGate(upd_gate_widgets, lock_enabled=True)

    # Snapshot of loaded values for no-op update detection.
    _upd_loaded: dict = {}

    def _set_upd_inputs_enabled(enabled: bool) -> None:
        upd_gate.set_locked(not enabled)
        if not enabled:
            # Keep code/search as-is; clear the editable display fields.
            for k in ['upd_name', 'upd_sell', 'upd_cost', 'upd_supplier']:
                try:
                    widgets[k].clear()
                except Exception:
                    pass
            try:
                _set_combo_blank(widgets['upd_cat'])
            except Exception:
                pass

    # Initial locked state for UPDATE tab.
    _set_upd_inputs_enabled(False)

    # --- ADD gate (single responsibility: lock/unlock inputs) ---
    add_gate_widgets = [
        widgets['add_name'], widgets['add_sell'], widgets['add_cost'],
        widgets['add_supp'], widgets['add_unit'], widgets['add_cat'],
        widgets['add_markup'], widgets['add_ok'],
    ]
    add_gate = FocusGate(add_gate_widgets, lock_enabled=True)

    # Remember UI placeholders/defaults for gated widgets.
    for _le in [
        widgets['add_name'], widgets['add_sell'], widgets['add_cost'],
        widgets['add_supp'], widgets['add_unit'], widgets['add_markup'],
    ]:
        _remember_ui_for_lineedit(_le)

    def _set_add_inputs_enabled(enabled: bool) -> None:
        add_gate.set_locked(not enabled)

        # Hide hints and defaults while locked; restore UI-provided hints/defaults when unlocked.
        for _le in [
            widgets['add_name'], widgets['add_sell'], widgets['add_cost'],
            widgets['add_supp'], widgets['add_unit'], widgets['add_markup'],
        ]:
            _set_lineedit_hints_visible(_le, enabled)

        # Unit is fixed for Product Menu: show 'Each' once unlocked.
        try:
            if enabled:
                if not (widgets['add_unit'].text() or '').strip():
                    widgets['add_unit'].setText('Each')
            else:
                widgets['add_unit'].clear()
        except Exception:
            pass

        # Combo display text should not show while locked.
        try:
            widgets['add_cat'].setCurrentIndex(0 if enabled else -1)
        except Exception:
            pass

    def _product_code_exists(code: str) -> bool:
        s = (code or '').strip().lower()
        if not s:
            return False
        for k in (dbop.PRODUCT_CACHE or {}).keys():
            if (k or '').strip().lower() == s:
                return True
        return False

    def _update_add_gate(*_):
        code = (widgets['add_code'].text() or '').strip()
        is_reserved = is_reserved_vegetable_code(code)
        exists = _product_code_exists(code)
        valid = (len(code) >= 4) and (not is_reserved) and (not exists)

        _set_add_inputs_enabled(valid)
        if valid:
            if widgets['add_code'].hasFocus():
                try:
                    widgets['add_name'].setFocus()
                except Exception:
                    pass
        else:
            # Clear gated fields when relocking.
            for k in ['add_name', 'add_sell', 'add_cost', 'add_supp', 'add_markup', 'add_unit']:
                try:
                    widgets[k].clear()
                except Exception:
                    pass

        if is_reserved:
            ui_feedback.set_status_label(widgets['add_status'], "Not allowed. Edit Vegetables in Vegetable menu", ok=False)
        elif exists:
            ui_feedback.set_status_label(widgets['add_status'], "Error: Product Code already exists.", ok=False)
            try:
                widgets['add_code'].selectAll()
            except Exception:
                pass
        else:
            ui_feedback.clear_status_label(widgets['add_status'])

    widgets['add_code'].textChanged.connect(_update_add_gate)

    # --- ADD Enter navigation (prevents dialog from accepting on Enter) ---
    # Mandatory fields swallow Enter when empty; optional fields allow advancing.
    coord.add_link(
        source=widgets['add_code'],
        target_map=None,
        lookup_fn=None,
        next_focus=lambda: widgets['add_name'].setFocus() if widgets['add_name'].isEnabled() else None,
        status_label=widgets['add_status'],
        swallow_empty=True,
    )
    coord.add_link(
        source=widgets['add_name'],
        target_map=None,
        lookup_fn=None,
        next_focus=widgets['add_sell'],
        status_label=widgets['add_status'],
        swallow_empty=True,
        validate_fn=lambda: input_handler.handle_product_name_input(widgets['add_name']),
    )
    coord.add_link(
        source=widgets['add_sell'],
        target_map=None,
        lookup_fn=None,
        next_focus=widgets['add_cost'],
        status_label=widgets['add_status'],
        swallow_empty=True,
        validate_fn=lambda: input_handler.handle_price_input(widgets['add_sell'], price_type='Selling price'),
    )
    coord.add_link(
        source=widgets['add_cost'],
        target_map=None,
        lookup_fn=None,
        next_focus=widgets['add_supp'],
        status_label=widgets['add_status'],
        swallow_empty=False,
    )
    coord.add_link(
        source=widgets['add_supp'],
        target_map=None,
        lookup_fn=None,
        next_focus=widgets['add_cat'],
        status_label=widgets['add_status'],
        swallow_empty=False,
    )
    coord.add_link(
        source=widgets['add_cat'],
        target_map=None,
        lookup_fn=None,
        next_focus=widgets['add_ok'],
        status_label=widgets['add_status'],
        swallow_empty=False,
    )

    # --- UPDATE Enter navigation (field-to-field) ---
    # After a successful lookup, Enter should move through editable fields.
    coord.add_link(
        source=widgets['upd_name'],
        target_map=None,
        lookup_fn=None,
        next_focus=widgets['upd_sell'],
        status_label=widgets['upd_status'],
        swallow_empty=True,
        validate_fn=lambda: input_handler.handle_product_name_input(widgets['upd_name']),
    )
    coord.add_link(
        source=widgets['upd_sell'],
        target_map=None,
        lookup_fn=None,
        next_focus=widgets['upd_cost'],
        status_label=widgets['upd_status'],
        swallow_empty=True,
        validate_fn=lambda: input_handler.handle_price_input(widgets['upd_sell'], price_type='Selling price'),
    )
    coord.add_link(
        source=widgets['upd_cost'],
        target_map=None,
        lookup_fn=None,
        next_focus=widgets['upd_cat'],
        status_label=widgets['upd_status'],
        swallow_empty=False,
    )
    coord.add_link(
        source=widgets['upd_cat'],
        target_map=None,
        lookup_fn=None,
        next_focus=widgets['upd_supplier'],
        status_label=widgets['upd_status'],
        swallow_empty=False,
    )
    coord.add_link(
        source=widgets['upd_supplier'],
        target_map=None,
        lookup_fn=None,
        next_focus=widgets['upd_ok'],
        status_label=widgets['upd_status'],
        swallow_empty=False,
    )

    # --- Landing Focus Logic ---
    tab_index_for_mode = {'add': 0, 'remove': 1, 'rem': 1, 'update': 2, 'upd': 2}

    def _focus_code_for_tab(idx: int) -> None:
        le = {0: widgets['add_code'], 1: widgets['rem_code'], 2: widgets['upd_code']}.get(idx)
        if le is None:
            return
        le.setFocus()
        try:
            le.selectAll()
        except Exception:
            pass

    widgets['tabs'].currentChanged.connect(_focus_code_for_tab)

    # --- OK/Cancel Handlers ---
    def _finalize(mode: str, code: str, name: str) -> None:
        verb = {'add': 'added', 'rem': 'removed', 'upd': 'updated'}.get(mode, mode)
        ui_feedback.set_status_label(widgets[f'{mode}_status'], f"Success: {name} {verb}", ok=True)
        set_dialog_info(dlg, f"Product {name} {verb}.")
        if mode == 'add' and initial_code:
            QTimer.singleShot(10, lambda: handle_barcode_scanned(main_window.sales_table, code, main_window.statusBar()))
        QTimer.singleShot(500, dlg.accept)

    def do_add():
        # OK-time boundary validation (final safety)
        try:
            code = input_handler.handle_product_code_input(widgets['add_code'])
        except ValueError as e:
            ui_feedback.set_status_label(widgets['add_status'], str(e), ok=False)
            widgets['add_code'].setFocus()
            return

        # Product Menu-specific rule: reserved veg codes cannot be created as products.
        if is_reserved_vegetable_code(code):
            ui_feedback.set_status_label(widgets['add_status'], "Not allowed. Edit Vegetables in Vegetable menu", ok=False)
            widgets['add_code'].setFocus()
            try:
                widgets['add_code'].selectAll()
            except Exception:
                pass
            return

        # Re-check uniqueness at the boundary (user may click OK without triggering gate updates)
        if _product_code_exists(code):
            ui_feedback.set_status_label(widgets['add_status'], "Error: Product Code already exists.", ok=False)
            widgets['add_code'].setFocus()
            try:
                widgets['add_code'].selectAll()
            except Exception:
                pass
            return

        try:
            name = input_handler.handle_product_name_input(widgets['add_name'])
        except ValueError as e:
            ui_feedback.set_status_label(widgets['add_status'], str(e), ok=False)
            widgets['add_name'].setFocus()
            return

        try:
            sell_value = input_handler.handle_price_input(widgets['add_sell'], price_type='Selling price')
        except ValueError as e:
            ui_feedback.set_status_label(widgets['add_status'], str(e), ok=False)
            widgets['add_sell'].setFocus()
            return

        try:
            cost_opt = input_handler.handle_price_input_optional(widgets['add_cost'], price_type='Cost price')
        except ValueError as e:
            ui_feedback.set_status_label(widgets['add_status'], str(e), ok=False)
            widgets['add_cost'].setFocus()
            return
        cost_value = float(cost_opt or 0.0)

        try:
            supplier = input_handler.handle_supplier_input(widgets['add_supp'])
        except ValueError as e:
            ui_feedback.set_status_label(widgets['add_status'], str(e), ok=False)
            widgets['add_supp'].setFocus()
            return

        # Category UX rule:
        # - Keep placeholder visible if user didn't select.
        # - Only at save time: store canonical 'Other' when placeholder/blank.
        try:
            idx = widgets['add_cat'].currentIndex()
        except Exception:
            idx = -1
        if idx <= 0:
            cat = 'Other'
        else:
            try:
                cat = input_handler.handle_category_input_combo(widgets['add_cat'])
            except ValueError as e:
                ui_feedback.set_status_label(widgets['add_status'], str(e), ok=False)
                widgets['add_cat'].setFocus()
                return

        # Unit: show/save 'Each' by default (field is read-only).
        unit = canonicalize_unit((widgets['add_unit'].text() or 'Each'))

        ok, msg = add_product(
            code,
            name,
            sell_value,
            cat,
            supplier,
            cost_value,
            unit,
            QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss'),
        )
        if ok: _finalize('add', code, name)
        else: ui_feedback.set_status_label(widgets['add_status'], msg, ok=False)

    def do_rem():
        code = widgets['rem_code'].text()
        ok, msg = delete_product(code)
        if ok:
            _refresh_name_completers()
            _finalize('rem', code, "Product")
        else: ui_feedback.set_status_label(widgets['rem_status'], msg, ok=False)

    def do_upd():
        try:
            code = input_handler.handle_product_code_input(widgets['upd_code'])
        except ValueError as e:
            ui_feedback.set_status_label(widgets['upd_status'], str(e), ok=False)
            widgets['upd_code'].setFocus()
            return

        # Product Menu-specific rule for UPDATE lookups as well.
        if is_reserved_vegetable_code(code):
            ui_feedback.set_status_label(widgets['upd_status'], "Reserved vegetable code", ok=False)
            widgets['upd_code'].setFocus()
            try:
                widgets['upd_code'].selectAll()
            except Exception:
                pass
            return

        try:
            name = input_handler.handle_product_name_input(widgets['upd_name'])
        except ValueError as e:
            ui_feedback.set_status_label(widgets['upd_status'], str(e), ok=False)
            widgets['upd_name'].setFocus()
            return

        try:
            sell_value = input_handler.handle_price_input(widgets['upd_sell'], price_type='Selling price')
        except ValueError as e:
            ui_feedback.set_status_label(widgets['upd_status'], str(e), ok=False)
            widgets['upd_sell'].setFocus()
            return

        try:
            cost_opt = input_handler.handle_price_input_optional(widgets['upd_cost'], price_type='Cost price')
        except ValueError as e:
            ui_feedback.set_status_label(widgets['upd_status'], str(e), ok=False)
            widgets['upd_cost'].setFocus()
            return
        cost_value = float(cost_opt or 0.0)

        try:
            cur_supplier = input_handler.handle_supplier_input(widgets['upd_supplier'])
        except ValueError as e:
            ui_feedback.set_status_label(widgets['upd_status'], str(e), ok=False)
            widgets['upd_supplier'].setFocus()
            return

        try:
            idx = widgets['upd_cat'].currentIndex()
        except Exception:
            idx = -1
        if idx <= 0:
            cat = 'Other'
        else:
            try:
                cat = input_handler.handle_category_input_combo(widgets['upd_cat'])
            except ValueError as e:
                ui_feedback.set_status_label(widgets['upd_status'], str(e), ok=False)
                widgets['upd_cat'].setFocus()
                return

        # Unit is read-only in UPDATE; preserve loaded unit.
        unit = canonicalize_unit((widgets['upd_unit'].text() or 'Each'))

        # No-op update detection: only write if editable fields changed.
        changed = False
        try:
            orig = _upd_loaded or {}
            changed = (
                (str(orig.get('name', '')).strip() != str(name or '').strip())
                or (float(orig.get('sell', 0) or 0) != float(sell_value or 0))
                or (float(orig.get('cost', 0) or 0) != float(cost_value or 0))
                or (str(orig.get('category', '')).strip() != str(cat or '').strip())
                or (str(orig.get('supplier', '')).strip() != str(cur_supplier or '').strip())
            )
        except Exception:
            changed = True

        if not changed:
            dlg.accept()
            return

        ok, msg = update_product(code, name, sell_value, cat, cur_supplier, cost_value, unit)
        if ok:
            _refresh_name_completers()
            _finalize('upd', code, name)
        else: ui_feedback.set_status_label(widgets['upd_status'], msg, ok=False)

    # Auto-clear validation errors once the user corrects the last error source.
    coord.register_validator(
        widgets['add_name'],
        lambda: input_handler.handle_product_name_input(widgets['add_name']),
        status_label=widgets['add_status'],
    )
    coord.register_validator(
        widgets['add_sell'],
        lambda: input_handler.handle_price_input(widgets['add_sell'], price_type='Selling price'),
        status_label=widgets['add_status'],
    )
    coord.register_validator(
        widgets['upd_name'],
        lambda: input_handler.handle_product_name_input(widgets['upd_name']),
        status_label=widgets['upd_status'],
    )
    coord.register_validator(
        widgets['upd_sell'],
        lambda: input_handler.handle_price_input(widgets['upd_sell'], price_type='Selling price'),
        status_label=widgets['upd_status'],
    )

    # Connections
    widgets['add_ok'].clicked.connect(do_add); widgets['rem_ok'].clicked.connect(do_rem); widgets['upd_ok'].clicked.connect(do_upd)
    widgets['add_cancel'].clicked.connect(dlg.reject); widgets['rem_cancel'].clicked.connect(dlg.reject); widgets['upd_cancel'].clicked.connect(dlg.reject); widgets['close_btn'].clicked.connect(dlg.reject)

    # Barcode Override
    def barcode_override(barcode):
        idx = widgets['tabs'].currentIndex()
        le = {0: widgets['add_code'], 1: widgets['rem_code'], 2: widgets['upd_code']}.get(idx)
        if le:
            le.setText(barcode)
            _sync_source(le)
        return True

    bm = getattr(main_window, 'barcode_manager', None)
    if bm: bm.set_barcode_override(barcode_override)

    # Initialization
    if sale_lock:
        widgets['tabs'].setTabEnabled(1, False); widgets['tabs'].setTabEnabled(2, False)

    # Select initial tab.
    # Default: ADD tab (index 0). Only override when initial_mode is provided.
    # If initial_code is provided, always land on ADD so it can be applied.
    try:
        target_idx = 0
        if initial_code:
            target_idx = 0
        elif isinstance(initial_mode, str):
            idx = tab_index_for_mode.get(initial_mode.strip().lower())
            if idx is not None:
                target_idx = idx
        if sale_lock and target_idx != 0:
            target_idx = 0
        widgets['tabs'].setCurrentIndex(target_idx)
    except Exception:
        pass

    # Initial landing focus
    QTimer.singleShot(0, lambda: _focus_code_for_tab(widgets['tabs'].currentIndex()))

    if initial_code:
        widgets['add_code'].setText(initial_code)

    # Force initial gate state
    _update_add_gate()
    return dlg