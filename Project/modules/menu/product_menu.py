import os
from PyQt5.QtWidgets import QLineEdit, QPushButton, QLabel, QComboBox, QTabWidget
from PyQt5.QtCore import Qt, QTimer, QDateTime

from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui,
    require_widgets,
    set_dialog_main_status_max,
    report_exception_post_close,
    log_and_set_post_close,
)
from modules.ui_utils.canonicalization import canonicalize_product_code
from modules.ui_utils.focus_utils import FieldCoordinator, FocusGate, enforce_exclusive_lineedits
from modules.ui_utils import input_handler, ui_feedback
from modules.db_operation import (
    get_product_full, add_product, update_product, delete_product
)
import modules.db_operation as dbop
from modules.db_operation.product_cache import PRODUCT_CODE_DISPLAY
from modules.ui_utils.input_validation import is_reserved_vegetable_code, validate_product_code_format, product_code_exists
from modules.table import handle_barcode_scanned
from modules.table.unit_helpers import canonicalize_unit
from config import PRODUCT_CATEGORIES

# Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_PATH = os.path.join(BASE_DIR, 'ui', 'product_menu.ui')
QSS_PATH = os.path.join(BASE_DIR, 'assets', 'dialog.qss')

def launch_product_dialog(main_window, initial_mode=None, initial_code=None):
    from modules.table.table_operations import is_transaction_active
    sale_lock = is_transaction_active(getattr(main_window, 'sales_table', None))

    # 1. Attempt to load the real UI
    dlg = build_dialog_from_ui(UI_PATH, host_window=main_window, dialog_name='Product menu', qss_path=QSS_PATH)
    
    # 2. If load failed, return the standardized fallback immediately
    if not dlg:
        from modules.ui_utils.dialog_utils import build_error_fallback_dialog
        return build_error_fallback_dialog(main_window, "Product Menu", QSS_PATH)

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
        'rem_name_srch': (QLineEdit, 'removeNameSearchLineEdit'),
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
        'upd_name_srch': (QLineEdit, 'updateNameSearchLineEdit'),
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
    def _init_category_combo(combo: QComboBox) -> None:
        if combo is None:
            return
        try:
            placeholder = ""
            # Prefer config placeholder (first item) so UI never defaults to a real category (e.g. 'Other').
            try:
                if isinstance(PRODUCT_CATEGORIES, (list, tuple)) and len(PRODUCT_CATEGORIES) > 0:
                    cfg0 = (PRODUCT_CATEGORIES[0] or '').strip()
                    # Only treat it as a placeholder if it looks like one.
                    if cfg0.startswith('--') and cfg0.endswith('--'):
                        placeholder = cfg0
            except Exception:
                placeholder = ""

            # Fallback to whatever the .ui provided.
            if not placeholder:
                try:
                    if combo.count() > 0:
                        placeholder = (combo.itemText(0) or '').strip()
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

    input_handler.wire_markup_logic(widgets['add_sell'], widgets['add_cost'], widgets['add_markup'])
    input_handler.wire_markup_logic(widgets['upd_sell'], widgets['upd_cost'], widgets['upd_markup'])

    # --- Search Setup ---
    # Ensure we have a full cache so completers include all products.
    try:
        if not (dbop.PRODUCT_CACHE or {}):
            dbop.load_product_cache()
    except Exception as e:
        report_exception_post_close(
            dlg,
            'ProductMenu: load_product_cache() for completers',
            e,
            user_message='Warning: Failed to load product list (suggestions may be limited)',
            level='warning',
            duration=5000,
        )

    def _post_db_success_refresh(where: str) -> None:
        """After DB CRUD succeeds, best-effort refresh cache + completers.

        This must never block or revert the DB operation; it only keeps UI
        suggestions and cache-consumers in sync.
        """
        try:
            dbop.refresh_product_cache()
        except Exception as e:
            # Log the technical failure
            from modules.ui_utils.error_logger import log_error
            log_error(f"Cache Refresh Failed after {where}: {e}")
            # Notify user after dialog closes
            report_exception_post_close(
                dlg,
                f'Product Menu: refresh_product_cache() after {where}',
                e,
                user_message='Warning: Product list may be outdated (restart if needed)',
                level='warning',
                duration=5000,
            )
        try:
            _refresh_name_completers()
        except Exception as e:
            report_exception_post_close(
                dlg,
                f'Product Menu: refresh name completers after {where}',
                e,
                user_message='Warning: Search suggestions not updated',
                level='warning',
                duration=4000,
            )

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

    def _refresh_name_completers() -> None:
        """Refresh REMOVE/UPDATE name completers from the current PRODUCT_CACHE.

        QCompleter models are not automatically updated when PRODUCT_CACHE changes,
        so we reattach using a fresh name list.
        """
        try:
            new_names = _names_from_cache()

            def _rem_selected(_text=None, _le=None):
                _sync_source(widgets['rem_name_srch'])
                try:
                    widgets['rem_ok'].setFocus()
                except Exception:
                    pass

            def _upd_selected(_text=None, _le=None):
                _sync_source(widgets['upd_name_srch'])
                try:
                    widgets['upd_cancel'].setFocus()
                except Exception:
                    pass

            input_handler.setup_name_search_lineedit(
                widgets['rem_name_srch'],
                new_names,
                on_selected=_rem_selected,
                trigger_on_finish=False,
            )
            input_handler.setup_name_search_lineedit(
                widgets['upd_name_srch'],
                new_names,
                on_selected=_upd_selected,
                trigger_on_finish=False,
            )
        except Exception as e:
            # update error logger
            from modules.ui_utils.error_logger import log_error
            log_error(f"UI Search Suggestion Error: {e}")
            # display to user after dialog closes
            report_exception_post_close(
                dlg,
                'ProductMenu: _refresh_name_completers()',
                e,
                user_message='Warning: Search suggestions not updated',
                level='warning',
                duration=4000,
            )

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
        raw = str(code) if code is not None else ''
        code_norm = canonicalize_product_code(raw)
        if not code_norm:
            return None, "Empty code"
        if is_reserved_vegetable_code(code_norm):
            return None, "Reserved vegetable code"
        found, pdata = get_product_full(code_norm)
        if not found:
            return None, "Product not found"
        # Prefer display casing from cache map.
        code_disp = PRODUCT_CODE_DISPLAY.get(code_norm) or (pdata.get('product_code') or code_norm)
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
        'name_search': widgets['rem_name_srch'],
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
        'name_search': widgets['upd_name_srch'],
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
        # Project convention: DB/cache stores 'Other' when user didn't pick a category.
        # Keep the placeholder visible instead of showing 'Other' as if it was chosen.
        if s.strip().lower() == 'other':
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

    def _lookup_product_by_name(val: str):
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

        input_handler.calculate_markup_widgets(widgets['upd_sell'], widgets['upd_cost'], widgets['upd_markup'])

    coord.add_link(
        source=widgets['rem_code'],
        target_map=rem_targets_from_code,
        lookup_fn=_lookup_product,
        next_focus=widgets['rem_ok'],
        status_label=widgets['rem_status'],
        auto_jump=False,
    )
    coord.add_link(
        source=widgets['rem_name_srch'],
        target_map=rem_targets_from_name,
        lookup_fn=_lookup_product_by_name,
        next_focus=widgets['rem_ok'],
        status_label=widgets['rem_status'],
        auto_jump=False,
    )
    coord.add_link(
        source=widgets['upd_code'],
        target_map=upd_targets_from_code,
        lookup_fn=_lookup_product,
        next_focus=widgets['upd_cancel'],
        status_label=widgets['upd_status'],
        on_sync=_on_upd_sync,
        auto_jump=False,
    )
    coord.add_link(
        source=widgets['upd_name_srch'],
        target_map=upd_targets_from_name,
        lookup_fn=_lookup_product_by_name,
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
    def _commit_rem_name_srch() -> None:
        try:
            txt = widgets['rem_name_srch'].text() or ''
        except Exception:
            txt = ''
        try:
            result, _err = _lookup_product_by_name(txt)
        except Exception:
            result = None
        _sync_source(widgets['rem_name_srch'])
        if result:
            try:
                widgets['rem_ok'].setFocus()
            except Exception:
                pass

    def _commit_upd_name_srch() -> None:
        try:
            txt = widgets['upd_name_srch'].text() or ''
        except Exception:
            txt = ''
        try:
            result, _err = _lookup_product_by_name(txt)
        except Exception:
            result = None
        _sync_source(widgets['upd_name_srch'])
        if result:
            try:
                widgets['upd_cancel'].setFocus()
            except Exception:
                pass

    try:
        widgets['rem_name_srch'].returnPressed.connect(_commit_rem_name_srch)
    except Exception:
        pass
    try:
        widgets['upd_name_srch'].returnPressed.connect(_commit_upd_name_srch)
    except Exception:
        pass

    # UX clarity: code-search vs name-search are mutually exclusive.
    enforce_exclusive_lineedits(
        widgets['rem_code'],
        widgets['rem_name_srch'],
        on_switch_to_a=_clear_remove_display,
        on_switch_to_b=_clear_remove_display,
        clear_status_label=widgets['rem_status'],
    )
    enforce_exclusive_lineedits(
        widgets['upd_code'],
        widgets['upd_name_srch'],
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
    """
    def _product_code_exists(code: str) -> bool:
        key = canonicalize_product_code(code)
        if not key:
            return False
        try:
            return key in (dbop.PRODUCT_CACHE or {})
        except Exception:
            return False """

    # --- SECTION 5: VALIDATION & GATING ---

    _ADD_CODE_ERR_RESERVED = "Not allowed. Edit Vegetables in Vegetable menu"
    _ADD_CODE_ERR_EXISTS = "Error: Product Code already exists."

    def _validate_add_product_code_policy(code: str):
        """Unified gatekeeper for Product Menu ADD codes."""
        s = canonicalize_product_code(code)
        if not s:
            return True, None, None

        # 1. Format Check (min_len, max_len, regex)
        ok_fmt, err_fmt = validate_product_code_format(s)
        if not ok_fmt:
            return False, 'format', err_fmt

        # 2. Reserved Check (veg01-16)
        if is_reserved_vegetable_code(s):
            return False, 'reserved', _ADD_CODE_ERR_RESERVED

        # 3. Collision Check (Already in DB)
        if product_code_exists(s):
            return False, 'exists', _ADD_CODE_ERR_EXISTS

        return True, None, None

    def _update_add_gate(*_):
        """Triggers every keystroke in the ADD tab code field."""
        raw_text = widgets['add_code'].text() or ''
        ok_policy, reason, msg = _validate_add_product_code_policy(raw_text)
        
        # Gate unlocks ONLY if policy passes and code isn't blank
        is_valid = ok_policy and bool(raw_text.strip())
        _set_add_inputs_enabled(is_valid)
        
        if not is_valid:
            # Keep UI clean while locked
            for k in ['add_name', 'add_sell', 'add_cost', 'add_supp', 'add_markup', 'add_unit']:
                try: widgets[k].clear()
                except: pass

        # Show feedback for specific failures (Too short, Reserved, or Exists)
        if not ok_policy and msg:
            ui_feedback.set_status_label(widgets['add_status'], msg, ok=False)
            # Only auto-highlight if the code exists (don't highlight while still typing/too short)
            if reason == 'exists':
                try: widgets['add_code'].selectAll()
                except: pass
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
        validate_fn=lambda: input_handler.handle_product_code_input(widgets['add_code']),
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
        validate_fn=lambda: input_handler.handle_selling_price(widgets['add_sell'], price_type='Selling price'),
    )

    coord.add_link(
        source=widgets['add_cost'],
        target_map=None,
        lookup_fn=None,
        next_focus=widgets['add_cat'],
        status_label=widgets['add_status'],
        swallow_empty=False,
        validate_fn=lambda: input_handler.handle_cost_price(
            widgets['add_cost'], 
            price_type='Cost price'
        ),
    )

    coord.add_link(
        source=widgets['add_cat'],
        target_map=None,
        lookup_fn=None,
        next_focus=widgets['add_supp'],
        status_label=widgets['add_status'],
        swallow_empty=False,
        validate_fn=lambda: input_handler.handle_category_input_combo(widgets['add_cat']),
    )

    coord.add_link(
        source=widgets['add_supp'],
        target_map=None,
        lookup_fn=None,
        next_focus=widgets['add_ok'],
        status_label=widgets['add_status'],
        swallow_empty=False,
        validate_fn=lambda: input_handler.handle_supplier_input(widgets['add_supp']),
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
        validate_fn=lambda: input_handler.handle_product_name_input(
            widgets['upd_name'], 
            exclude_code=widgets['upd_code'].text()
        )
    )
    coord.add_link(
        source=widgets['upd_sell'],
        target_map=None,
        lookup_fn=None,
        next_focus=widgets['upd_cost'],
        status_label=widgets['upd_status'],
        swallow_empty=True,
        validate_fn=lambda: input_handler.handle_selling_price(widgets['upd_sell'], price_type='Selling price'),
    )
    coord.add_link(
        source=widgets['upd_cost'],
        target_map=None,
        lookup_fn=None,
        next_focus=widgets['upd_cat'],
        status_label=widgets['upd_status'],
        swallow_empty=False,
        validate_fn=lambda: input_handler.handle_cost_price(
            widgets['upd_cost'], 
            price_type='Cost price'
        ),
    )

    coord.add_link(
        source=widgets['upd_cat'],
        target_map=None,
        lookup_fn=None,
        next_focus=widgets['upd_supplier'],
        status_label=widgets['upd_status'],
        swallow_empty=False,
        validate_fn=lambda: input_handler.handle_category_input_combo(widgets['upd_cat']),
    )

    coord.add_link(
        source=widgets['upd_supplier'],
        target_map=None,
        lookup_fn=None,
        next_focus=widgets['upd_ok'],
        status_label=widgets['upd_status'],
        swallow_empty=False,
        validate_fn=lambda: input_handler.handle_supplier_input(widgets['upd_supplier']),
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
    def _focus_widget(w, select_all: bool = False) -> None:
        if w is None:
            return
        try:
            w.setFocus()
        except Exception:
            return
        if select_all and isinstance(w, QLineEdit):
            try:
                w.selectAll()
            except Exception:
                pass

    def _try_value(getter_fn, *, status_label: QLabel, focus_widget=None, select_all: bool = False):
        try:
            return True, getter_fn()
        except ValueError as e:
            _focus_widget(focus_widget, select_all=select_all)
            ui_feedback.set_status_label(status_label, str(e), ok=False)
            return False, None
  
    def _resolve_category_for_save(combo: QComboBox, *, status_label: QLabel) -> str | None:
        # 1. If placeholder is selected, return empty string (No validation needed)
        if combo.currentIndex() <= 0:
            return ""
        # 2. If an actual item is selected (like '1'), run validation via _try_value
        ok, cat = _try_value(
            lambda: input_handler.handle_category_input_combo(combo),
            status_label=status_label,
            focus_widget=combo,
        )
        return cat if ok else None

    def _finalize(mode: str, code: str, name: str) -> None:
        # Update verbs to be more professional
        verb_map = {'add': 'Added', 'rem': 'Deleted', 'upd': 'Updated'}
        verb = verb_map.get(mode, 'Processed')
        
        # Natural phrasing: "Product [Name] Deleted"
        display_msg = f"Product '{name}' {verb}"
        
        # Use the coordinator for consistency (it clears error states automatically)
        ui_feedback.set_status_label(widgets[f'{mode}_status'], display_msg, ok=True)
        
        # Set the main window status (post-close message)
        set_dialog_main_status_max(dlg, display_msg, level='info', duration=4000)
        
        if mode == 'add' and initial_code:
            # If we added a product via a "Not Found" scan, add it to sales table immediately
            QTimer.singleShot(10, lambda: handle_barcode_scanned(main_window.sales_table, code, main_window.statusBar()))
        
        QTimer.singleShot(500, dlg.accept)

    # --- SECTION 6: EXECUTION HANDLERS ---

    def do_add():
        # 1. Final Policy Gate
        raw_code = widgets['add_code'].text()
        ok_p, _, p_msg = _validate_add_product_code_policy(raw_code)
        if not ok_p:
            ui_feedback.set_status_label(widgets['add_status'], p_msg, ok=False)
            _focus_widget(widgets['add_code'], select_all=True)
            return
        
        code = canonicalize_product_code(raw_code)

        # 2. Extract & Validate rest of fields
        ok, name = _try_value(lambda: input_handler.handle_product_name_input(widgets['add_name']), 
                              status_label=widgets['add_status'], focus_widget=widgets['add_name'])
        if not ok: return

        ok, sell = _try_value(lambda: input_handler.handle_selling_price(widgets['add_sell'], 'Selling price'), 
                              status_label=widgets['add_status'], focus_widget=widgets['add_sell'])
        if not ok: return

        ok, cost_opt = _try_value(lambda: input_handler.handle_cost_price(widgets['add_cost'], 'Cost price'), 
                                  status_label=widgets['add_status'], focus_widget=widgets['add_cost'])
        if not ok: return
        cost = float(cost_opt or 0.0)

        ok, supp = _try_value(lambda: input_handler.handle_supplier_input(widgets['add_supp']), 
                              status_label=widgets['add_status'], focus_widget=widgets['add_supp'])
        if not ok: return

        cat = _resolve_category_for_save(widgets['add_cat'], status_label=widgets['add_status'])
        if cat is None: return

        unit = canonicalize_unit(widgets['add_unit'].text() or 'Each')

        # 3. Save
        success, db_msg = add_product(code, name, sell, cat, supp, cost, unit, 
                                      QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss'))
        if success:
            dbop.refresh_product_cache()
            _finalize('add', code, name)
        else:
            # ERROR LOGGING
            from modules.ui_utils.error_logger import log_error
            log_error(f"DB Error (ADD Product {code}): {db_msg}")
            # STATUSBAR feedback after dialog closes
            log_and_set_post_close(
                dlg,
                f"Product Menu ADD failed (code={code})",
                str(db_msg),
                user_message=f"Error: {db_msg}",
                level='error',
                duration=5000,
            )
            # IMMEDIATE feedback in dialog
            ui_feedback.set_status_label(widgets['add_status'], db_msg, ok=False)

    def do_rem():
        code = widgets['rem_code'].text()
        name = widgets['rem_name_srch'].text().strip() or "Product"
        ok, msg = delete_product(code)
        if ok:
            _post_db_success_refresh('REMOVE')
            _finalize('rem', code, name)
        else:
            # ERROR LOGGING
            from modules.ui_utils.error_logger import log_error
            log_error(f"DB Error (REMOVE Product {code}): {msg}")
            # STATUSBAR feedback after dialog closes
            log_and_set_post_close(
                dlg,
                f"Product Menu REMOVE failed (code={code})",
                str(msg),
                user_message=f"Error: {msg}",
                level='error',
                duration=5000,
            )
            # IMMEDIATE feedback in dialog
            ui_feedback.set_status_label(widgets['rem_status'], msg, ok=False)

    def do_upd():
        """Modernized UPDATE logic with No-Op check."""
        # 1. Product Identification
        raw_code = widgets['upd_code'].text()
        code = canonicalize_product_code(raw_code)
        if is_reserved_vegetable_code(code):
            ui_feedback.set_status_label(widgets['upd_status'], "Cannot edit reserved items", ok=False)
            return

        # 2. Extract & Validate edits
        # [REDUNDANT]: Passing current code to allow product to keep its own name
        ok, name = _try_value(lambda: input_handler.handle_product_name_input(widgets['upd_name'], exclude_code=code), 
                              status_label=widgets['upd_status'], focus_widget=widgets['upd_name'])
        if not ok: return

        ok, sell = _try_value(lambda: input_handler.handle_selling_price(widgets['upd_sell'], 'Selling price'), 
                              status_label=widgets['upd_status'], focus_widget=widgets['upd_sell'])
        if not ok: return

        ok, cost_opt = _try_value(lambda: input_handler.handle_cost_price(widgets['upd_cost'], 'Cost price'), 
                                  status_label=widgets['upd_status'], focus_widget=widgets['upd_cost'])
        if not ok: return
        cost = float(cost_opt or 0.0)

        ok, supp = _try_value(lambda: input_handler.handle_supplier_input(widgets['upd_supplier']), 
                              status_label=widgets['upd_status'], focus_widget=widgets['upd_supplier'])
        if not ok: return

        cat = _resolve_category_for_save(widgets['upd_cat'], status_label=widgets['upd_status'])
        if cat is None: return

        unit = canonicalize_unit(widgets['upd_unit'].text() or 'Each')

        # 3. No-Op Check (Only save if something actually changed)
        if all([
            _upd_loaded.get('name') == name,
            _upd_loaded.get('sell') == sell,
            _upd_loaded.get('cost') == cost,
            _upd_loaded.get('category') == cat,
            _upd_loaded.get('supplier') == supp,
        ]):
            dlg.accept()
            return

        # 4. Save
        success, db_msg = update_product(code, name, sell, cat, supp, cost, unit)
        if success:
            dbop.refresh_product_cache()
            _finalize('upd', code, name)
        else:
            # ERROR LOGGING
            from modules.ui_utils.error_logger import log_error
            log_error(f"DB Error (UPDATE Product {code}): {db_msg}")
            # STATUSBAR feedback after dialog closes
            log_and_set_post_close(
                dlg,
                f"Product Menu UPDATE failed (code={code})",
                str(db_msg),
                user_message=f"Error: {db_msg}",
                level='error',
                duration=5000,
            )
            # IMMEDIATE feedback in dialog
            ui_feedback.set_status_label(widgets['upd_status'], db_msg, ok=False)

    # Auto-clear validation errors once the user corrects the last error source.
    coord.register_validator(
        widgets['add_name'],
        lambda: input_handler.handle_product_name_input(widgets['add_name']),
        status_label=widgets['add_status'],
    )
    coord.register_validator(
        widgets['add_sell'],
        lambda: input_handler.handle_selling_price(widgets['add_sell'], price_type='Selling price'),
        status_label=widgets['add_status'],
    )
    coord.register_validator(
        widgets['upd_name'],
        lambda: input_handler.handle_product_name_input(widgets['upd_name']),
        status_label=widgets['upd_status'],
    )
    coord.register_validator(
        widgets['upd_sell'],
        lambda: input_handler.handle_selling_price(widgets['upd_sell'], price_type='Selling price'),
        status_label=widgets['upd_status'],
    )

    # Connections
    widgets['add_ok'].clicked.connect(do_add); widgets['rem_ok'].clicked.connect(do_rem); widgets['upd_ok'].clicked.connect(do_upd)

    def _cancel_close() -> None:
        # Info-level so it won't override any warning/error queued earlier.
        set_dialog_main_status_max(dlg, 'Product menu closed.', level='info', duration=3000)
        dlg.reject()

    widgets['add_cancel'].clicked.connect(_cancel_close)
    widgets['rem_cancel'].clicked.connect(_cancel_close)
    widgets['upd_cancel'].clicked.connect(_cancel_close)
    widgets['close_btn'].clicked.connect(_cancel_close)

    # Barcode Override
    def barcode_override(barcode):
        idx = widgets['tabs'].currentIndex()
        le = {0: widgets['add_code'], 1: widgets['rem_code'], 2: widgets['upd_code']}.get(idx)
        if le:
            le.setText(barcode)
            _sync_source(le)
        return True

    # Wrapper convention: provide the handler; DialogWrapper installs/clears it.
    try:
        dlg.barcode_override_handler = barcode_override
    except Exception:
        pass

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