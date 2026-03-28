import os
from functools import partial
from PyQt5.QtWidgets import QLineEdit, QPushButton, QLabel, QComboBox, QTabWidget, QRadioButton
from PyQt5.QtCore import Qt, QTimer, QDateTime, QObject, QEvent

from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui,
    require_widgets,
    set_dialog_main_status_max,
    report_exception_post_close,
    log_and_set_post_close,
)
from modules.ui_utils.dialog_utils import clear_display
from modules.ui_utils.canonicalization import canonicalize_product_code
from modules.ui_utils.focus_utils import FieldCoordinator, FocusGate, enforce_exclusive_lineedits
from modules.ui_utils import input_handler, ui_feedback
from modules.ui_utils import category_service
from modules.db_operation import (
    get_product_full, add_product, update_product, delete_product
)
import modules.db_operation as dbop
from modules.db_operation.product_cache import PRODUCT_CODE_DISPLAY
from modules.ui_utils.input_validation import (
    is_reserved_vegetable_code,
    validate_product_code_format,
    product_code_exists,
    validate_category,
)
from modules.table import handle_barcode_scanned
from modules.table.unit_helpers import canonicalize_unit
from modules.date_time import format_datetime

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

        # CATEGORY
        'cat_add_radio': (QRadioButton, 'categoryAddRadioBtn'),
        'cat_remove_radio': (QRadioButton, 'categoryRemoveRadioBtn'),
        'cat_replace_radio': (QRadioButton, 'categoryReplaceRadioBtn'),
        'cat_add_le': (QLineEdit, 'categoryAddLineEdit'),
        'cat_select_combo': (QComboBox, 'categorySelectComboBox'),
        'cat_update_le': (QLineEdit, 'categoryUpdateLineEdit'),
        'cat_ok': (QPushButton, 'btnCategoryOk'),
        'cat_cancel': (QPushButton, 'btnCategoryCancel'),
        'cat_status': (QLabel, 'categoryStatusLabel'),
    })

    # Category OK should not auto-trigger on Enter when focus changes.
    try:
        widgets['cat_ok'].setDefault(False)
        widgets['cat_ok'].setAutoDefault(False)
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

    # Category combos: JSON categories, with a first-item placeholder.
    def _init_category_combo(combo: QComboBox) -> None:
        if combo is None:
            return
        try:
            placeholder = ""
            categories = []

            try:
                categories = category_service.list_categories() or []
            except Exception:
                categories = []

            # Prefer first item from JSON list as placeholder when available.
            if categories:
                placeholder = (categories[0] or '').strip()
                if placeholder.strip().lower() == 'other':
                    placeholder = ''

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
            # Avoid duplicating the placeholder if the list already includes it.
            items = []
            for c in list(categories or []):
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

    # Category tab: combo should use JSON categories (exclude 'Other'; keep placeholder).
    def _category_placeholder(items: list) -> str:
        if items:
            head = (items[0] or '').strip()
            if head and head.strip().lower() != 'other':
                return head
        return '--Select Category--'

    def _refresh_category_tab_combo() -> None:
        combo = widgets['cat_select_combo']
        if combo is None:
            return
        try:
            categories = category_service.list_categories() or []
            combo.blockSignals(True)
            combo.clear()

            items = []
            for c in categories:
                s = (c or '').strip()
                if not s:
                    continue
                if s.strip().lower() == 'other':
                    continue
                if s not in items:
                    items.append(s)
            combo.addItems(items)
            combo.setCurrentIndex(0 if items else -1)
        except Exception:
            pass
        finally:
            try:
                combo.blockSignals(False)
            except Exception:
                pass

    def _clear_category_tab_combo() -> None:
        combo = widgets['cat_select_combo']
        if combo is None:
            return
        try:
            combo.blockSignals(True)
            combo.clear()
            combo.setCurrentIndex(-1)
        except Exception:
            pass
        finally:
            try:
                combo.blockSignals(False)
            except Exception:
                pass

    # Category tab gates (match ADD tab lock/unlock visuals).
    cat_add_gate = FocusGate([widgets['cat_add_le']], lock_enabled=True)
    cat_select_gate = FocusGate([widgets['cat_select_combo']], lock_enabled=True)
    cat_update_gate = FocusGate([widgets['cat_update_le']], lock_enabled=True)

    # Gate for Category OK button.
    cat_ok_gate = FocusGate([widgets['cat_ok']], lock_enabled=True)

    try:
        cat_add_gate.remember_placeholders([widgets['cat_add_le']])
        cat_update_gate.remember_placeholders([widgets['cat_update_le']])
    except Exception:
        pass

    # Find corresponding FieldLbl widgets (may be missing in some UI variants).
    try:
        cat_add_lbl = dlg.findChild(QLabel, 'categoryAddFieldLbl')
    except Exception:
        cat_add_lbl = None
    try:
        cat_select_lbl = dlg.findChild(QLabel, 'categorySelectFieldLbl')
    except Exception:
        cat_select_lbl = None
    try:
        cat_update_lbl = dlg.findChild(QLabel, 'categoryUpdateFieldLbl')
    except Exception:
        cat_update_lbl = None

    def _set_field_locked(lbl: QLabel, locked: bool) -> None:
        """Set the dynamic 'locked' property on a FieldLbl and repolish so QSS updates.

        QSS should contain rules for QLabel[objectName$="FieldLbl"][locked="true"].
        """
        if lbl is None:
            return
        try:
            lbl.setProperty('locked', bool(locked))
            # Force style refresh so QSS picks up dynamic property change.
            try:
                lbl.style().unpolish(lbl)
                lbl.style().polish(lbl)
            except Exception:
                pass
            try:
                lbl.update()
            except Exception:
                pass
        except Exception:
            pass

    def _set_category_placeholders(add_enabled: bool, update_enabled: bool) -> None:
        try:
            # When enabled (unlocked) show the UI placeholders; when locked clear them.
            if add_enabled:
                cat_add_gate.restore_placeholders([widgets['cat_add_le']])
            else:
                cat_add_gate.hide_placeholders([widgets['cat_add_le']])
        except Exception:
            pass
        try:
            if update_enabled:
                cat_update_gate.restore_placeholders([widgets['cat_update_le']])
            else:
                cat_update_gate.hide_placeholders([widgets['cat_update_le']])
        except Exception:
            pass

    def _set_category_mode(mode: str) -> None:
        add_mode = mode == 'add'
        rem_mode = mode == 'remove'
        rep_mode = mode == 'replace'

        try:
            cat_add_gate.set_locked(not add_mode)
            _set_field_locked(cat_add_lbl, not add_mode)
            if add_mode:
                widgets['cat_add_le'].setFocus()
        except Exception:
            pass
        try:
            cat_select_gate.set_locked(not (rem_mode or rep_mode))
            _set_field_locked(cat_select_lbl, not (rem_mode or rep_mode))
        except Exception:
            pass
        try:
            # Keep update field locked until combo selection in Replace mode.
            if rep_mode:
                cat_update_gate.set_locked(True)
                _set_field_locked(cat_update_lbl, True)
            else:
                cat_update_gate.set_locked(not rep_mode)
                _set_field_locked(cat_update_lbl, not rep_mode)
        except Exception:
            pass

        # Enforce enabled state explicitly (UI defaults start disabled).
        try:
            widgets['cat_select_combo'].setEnabled(rem_mode or rep_mode)
        except Exception:
            pass
        try:
            widgets['cat_update_le'].setEnabled(rep_mode)
        except Exception:
            pass

        # OK button gating: locked by default.
        try:
            cat_ok_gate.set_locked(True)
        except Exception:
            pass

        # Reset replace selection state.
        try:
            _cat_replace_selection_valid['val'] = False
            if not rep_mode:
                cat_update_gate.set_locked(True)
                _set_field_locked(cat_update_lbl, True)
        except Exception:
            pass

        _set_category_placeholders(add_mode, rep_mode)

        # Combo population: only populate JSON items when remove/replace mode is active (unlocked).
        if rem_mode or rep_mode:
            _refresh_category_tab_combo()
        else:
            _clear_category_tab_combo()

        # Clear inputs when switching modes to avoid stale values.
        try:
            if not add_mode:
                widgets['cat_add_le'].clear()
        except Exception:
            pass
        try:
            if not rep_mode:
                widgets['cat_update_le'].clear()
        except Exception:
            pass

    def _set_category_add_mode():
        _set_category_mode('add')

    def _set_category_remove_mode():
        _set_category_mode('remove')

    def _set_category_replace_mode():
        _set_category_mode('replace')

    def _set_category_prompt(message: str) -> None:
        ui_feedback.set_status_label(widgets['cat_status'], message, ok=True)

    def _validate_category_text(text: str, focus_widget=None) -> bool:
        ok, err = validate_category(text)
        if not ok:
            ui_feedback.set_status_label(widgets['cat_status'], err, ok=False)
            try:
                if focus_widget is not None:
                    focus_widget.setFocus()
                    try:
                        if hasattr(focus_widget, 'selectAll'):
                            focus_widget.selectAll()
                    except Exception:
                        pass
            except Exception:
                pass
        return bool(ok)

    def _on_cat_add_enter() -> None:
        name = (widgets['cat_add_le'].text() or '').strip()
        if not _validate_category_text(name, focus_widget=widgets['cat_add_le']):
            return
        _set_category_prompt(f"Add new category {name} ?")
        try:
            # Unlock OK now that input validated
            cat_ok_gate.set_locked(False)
        except Exception:
            pass
        try:
            widgets['cat_ok'].setFocus()
        except Exception:
            pass

    def _on_cat_combo_activated(_idx=None) -> None:
        combo = widgets['cat_select_combo']
        if combo is None:
            return
        if combo.currentIndex() < 0:
            ui_feedback.set_status_label(widgets['cat_status'], "Select a category", ok=False)
            return
        name = (combo.currentText() or '').strip()
        if widgets['cat_remove_radio'].isChecked():
            _set_category_prompt(f"Remove category {name} ?")
            try:
                cat_ok_gate.set_locked(False)
            except Exception:
                pass
            try:
                widgets['cat_ok'].setFocus()
            except Exception:
                pass
        elif widgets['cat_replace_radio'].isChecked():
            _set_category_prompt(f"Replace category {name} ?")
            # On selection: unlock update field; OK stays locked until valid.
            try:
                _cat_replace_selection_valid['val'] = True
            except Exception:
                pass
            try:
                cat_update_gate.set_locked(False)
                _set_field_locked(cat_update_lbl, False)
            except Exception:
                pass
            try:
                # Ensure update field editable.
                try:
                    widgets['cat_update_le'].setEnabled(True)
                    widgets['cat_update_le'].setReadOnly(False)
                    widgets['cat_update_le'].setFocusPolicy(Qt.StrongFocus)
                except Exception:
                    pass
                widgets['cat_update_le'].setFocus()
            except Exception:
                pass

    def _on_cat_update_enter() -> None:
        replacement = (widgets['cat_update_le'].text() or '').strip()
        if not _validate_category_text(replacement, focus_widget=widgets['cat_update_le']):
            return
        try:
            widgets['cat_ok'].setFocus()
        except Exception:
            pass

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
            'last_updated': format_datetime(pdata.get('last_updated') or ''),
        }, None

    # --- Coordinator Wiring ---
    coord = FieldCoordinator(dlg)

    # Override category validator to register error with coordinator so
    # register_validator can auto-clear it when the user re-edits the field.
    def _validate_category_text(text: str, focus_widget=None) -> bool:
        ok, err = validate_category(text)
        if not ok:
            try:
                coord.set_error(focus_widget, err, status_label=widgets['cat_status'])
            except Exception:
                try:
                    ui_feedback.set_status_label(widgets['cat_status'], err, ok=False)
                except Exception:
                    pass
            try:
                if focus_widget is not None:
                    focus_widget.setFocus()
                    try:
                        if hasattr(focus_widget, 'selectAll'):
                            focus_widget.selectAll()
                    except Exception:
                        pass
            except Exception:
                pass
        return bool(ok)

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
        try:
            clear_display(rem_display_targets, widgets['rem_status'])
        except Exception:
            pass

    def _clear_update_display() -> None:
        def _upd_extra():
            try:
                _set_upd_inputs_enabled(False)
            except Exception:
                pass
            try:
                _upd_loaded.clear()
            except Exception:
                pass
        try:
            clear_display(upd_lineedit_targets, widgets['upd_status'], extra_post_clear=_upd_extra)
        except Exception:
            pass

    # Completers: ensure selection triggers coordinator sync.
    _refresh_name_completers()

    # Enter-to-commit for name search:
    # - Map values on Enter
    # - Jump focus only when a match exists
    def _commit_name_srch(source_le: QLineEdit, next_widget) -> None:
        try:
            txt = source_le.text() or ''
        except Exception:
            txt = ''
        try:
            result, _err = _lookup_product_by_name(txt)
        except Exception:
            result = None
        _sync_source(source_le)
        if result:
            try:
                next_widget.setFocus()
            except Exception:
                pass

    try:
        widgets['rem_name_srch'].returnPressed.connect(
            partial(_commit_name_srch, widgets['rem_name_srch'], widgets['rem_ok'])
        )
    except Exception:
        pass
    try:
        widgets['upd_name_srch'].returnPressed.connect(
            partial(_commit_name_srch, widgets['upd_name_srch'], widgets['upd_cancel'])
        )
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

    try:
        # Remember placeholders for update editable fields so we can hide/restore them.
        upd_gate.remember_placeholders([
            widgets['upd_cost'], widgets['upd_supplier']
        ])
    except Exception:
        pass

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
            try:
                upd_gate.hide_placeholders([
                    widgets['upd_cost'], widgets['upd_supplier']
                ])
            except Exception:
                pass
            return
        # when enabling, restore placeholders
        try:
            upd_gate.restore_placeholders([
                widgets['upd_cost'], widgets['upd_supplier']
            ])
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

    # Remember UI placeholders for gated widgets via FocusGate (opt-in).
    try:
        add_gate.remember_placeholders([
            widgets['add_name'], widgets['add_sell'], widgets['add_cost'],
            widgets['add_supp'], widgets['add_unit'], widgets['add_markup'],
        ])
    except Exception:
        pass

    def _set_add_inputs_enabled(enabled: bool) -> None:
        add_gate.set_locked(not enabled)

        # Hide placeholders while locked; restore placeholders when unlocked.
        try:
            if not enabled:
                add_gate.hide_placeholders([
                    widgets['add_name'], widgets['add_sell'], widgets['add_cost'],
                    widgets['add_supp'], widgets['add_unit'], widgets['add_markup'],
                ])
            else:
                add_gate.restore_placeholders([
                    widgets['add_name'], widgets['add_sell'], widgets['add_cost'],
                    widgets['add_supp'], widgets['add_unit'], widgets['add_markup'],
                ])
        except Exception:
            pass

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

    def _on_tab_changed(idx: int) -> None:
        _focus_code_for_tab(idx)
        # Refresh Category tab list when opened (only if remove/replace is active).
        if idx == 3:
            try:
                if widgets['cat_remove_radio'].isChecked():
                    _set_category_remove_mode()
                elif widgets['cat_replace_radio'].isChecked():
                    _set_category_replace_mode()
                else:
                    _set_category_add_mode()
            except Exception:
                pass

    widgets['tabs'].currentChanged.connect(_on_tab_changed)

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

    # Category tab: auto-clear validation when user fixes the field.
    # State used to gate Replace mode OK button (needs both selection + valid update)
    _cat_replace_selection_valid = {'val': False}

    def _cat_add_validator():
        txt = (widgets['cat_add_le'].text() or '').strip()
        ok, err = validate_category(txt)
        if not ok or not txt:
            # Treat empty as invalid for gating purposes
            raise ValueError(err or "Category is required")
        # Unlock OK for Add mode when valid & non-empty
        try:
            cat_ok_gate.set_locked(False)
        except Exception:
            pass
        return True

    def _cat_update_validator():
        txt = (widgets['cat_update_le'].text() or '').strip()
        ok, err = validate_category(txt)
        if not ok or not txt:
            # Treat empty as invalid for gating purposes
            raise ValueError(err or "Category is required")
        # For Replace mode: only unlock OK if a selection exists
        try:
            if _cat_replace_selection_valid.get('val'):
                cat_ok_gate.set_locked(False)
        except Exception:
            pass
        return True

    try:
        coord.register_validator(
            widgets['cat_add_le'],
            _cat_add_validator,
            status_label=widgets['cat_status'],
        )
    except Exception:
        pass

    try:
        coord.register_validator(
            widgets['cat_update_le'],
            _cat_update_validator,
            status_label=widgets['cat_status'],
        )
    except Exception:
        pass

    # Immediate-clear on typing: if the user corrects or clears the field while
    # focus remains, clear the status label right away (editingFinished only
    # fires on focus-out). This keeps the UI responsive when the user backspaces.
    try:
        def _on_cat_add_text_changed(_txt=None):
            try:
                text = (widgets['cat_add_le'].text() or '').strip()
            except Exception:
                text = ''

            # If the field is empty while typing, clear the status but keep OK locked
            if not text:
                try:
                    coord.clear_status(widgets['cat_status'])
                except Exception:
                    pass
                try:
                    cat_ok_gate.set_locked(True)
                except Exception:
                    pass
                return

            try:
                _cat_add_validator()
            except Exception:
                try:
                    cat_ok_gate.set_locked(True)
                except Exception:
                    pass
                return

            try:
                coord.clear_status(widgets['cat_status'])
                # Ensure OK unlocked when typing makes input valid
                try:
                    cat_ok_gate.set_locked(False)
                except Exception:
                    pass
            except Exception:
                pass

        widgets['cat_add_le'].textChanged.connect(_on_cat_add_text_changed)
    except Exception:
        pass

    try:
        def _on_cat_update_text_changed(_txt=None):
            try:
                text = (widgets['cat_update_le'].text() or '').strip()
            except Exception:
                text = ''

            # Clear status immediately on empty input but keep OK locked
            if not text:
                try:
                    coord.clear_status(widgets['cat_status'])
                except Exception:
                    pass
                try:
                    cat_ok_gate.set_locked(True)
                except Exception:
                    pass
                return

            try:
                _cat_update_validator()
            except Exception:
                try:
                    cat_ok_gate.set_locked(True)
                except Exception:
                    pass
                return

            try:
                coord.clear_status(widgets['cat_status'])
                # For Replace flow, validator unlocks OK when selection exists.
            except Exception:
                pass

        widgets['cat_update_le'].textChanged.connect(_on_cat_update_text_changed)
    except Exception:
        pass

    # Connections
    widgets['add_ok'].clicked.connect(do_add); widgets['rem_ok'].clicked.connect(do_rem); widgets['upd_ok'].clicked.connect(do_upd)

    def do_category_ok() -> None:
        def _finalize_category(message: str, *, show_label: bool = True) -> None:
            if show_label:
                ui_feedback.set_status_label(widgets['cat_status'], message, ok=True)
            set_dialog_main_status_max(dlg, message, level='info', duration=4000)
            try:
                dlg._skip_close_status = True
            except Exception:
                pass
            QTimer.singleShot(200, dlg.accept)

        def _selected_category() -> str | None:
            combo = widgets['cat_select_combo']
            if combo is None:
                return None
            if combo.currentIndex() < 0:
                ui_feedback.set_status_label(widgets['cat_status'], "Select a category", ok=False)
                return None
            return (combo.currentText() or '').strip()

        if widgets['cat_add_radio'].isChecked():
            name = widgets['cat_add_le'].text() or ''
            try:
                if not _validate_category_text(name, focus_widget=widgets['cat_add_le']):
                    return
                category_service.add_category(name)
                _finalize_category(f"Category '{name.strip()}' added")
            except ValueError as e:
                # Soft validation failure: keep dialog open so user can fix input.
                ui_feedback.set_status_label(widgets['cat_status'], str(e), ok=False)
            except Exception as e:
                # Hard failure: log and notify after dialog closes.
                from modules.ui_utils.error_logger import log_error
                log_error(f"Category ADD failed: {e}")
                log_and_set_post_close(
                    dlg,
                    "Category ADD failed",
                    str(e),
                    user_message=f"Error: {e}",
                    level='error',
                    duration=5000,
                )
                dlg.reject()
            return

        if widgets['cat_remove_radio'].isChecked():
            target = _selected_category()
            if not target:
                return
            try:
                products_updated, receipts_updated = category_service.delete_category(target)
                _finalize_category(
                    f"Category '{target}' removed",
                    show_label=False,
                )
            except ValueError as e:
                ui_feedback.set_status_label(widgets['cat_status'], str(e), ok=False)
            except Exception as e:
                from modules.ui_utils.error_logger import log_error
                log_error(f"Category REMOVE failed: {e}")
                log_and_set_post_close(
                    dlg,
                    "Category REMOVE failed",
                    str(e),
                    user_message=f"Error: {e}",
                    level='error',
                    duration=5000,
                )
                dlg.reject()
            return

        if widgets['cat_replace_radio'].isChecked():
            target = _selected_category()
            if not target:
                return
            replacement = widgets['cat_update_le'].text() or ''
            try:
                if not _validate_category_text(replacement, focus_widget=widgets['cat_update_le']):
                    return
                products_updated, receipts_updated = category_service.update_category(target, replacement)
                _finalize_category(
                    f"Category '{target}' replaced with '{replacement}'",
                    show_label=False,
                )
            except ValueError as e:
                ui_feedback.set_status_label(widgets['cat_status'], str(e), ok=False)
            except Exception as e:
                from modules.ui_utils.error_logger import log_error
                log_error(f"Category REPLACE failed: {e}")
                log_and_set_post_close(
                    dlg,
                    "Category REPLACE failed",
                    str(e),
                    user_message=f"Error: {e}",
                    level='error',
                    duration=5000,
                )
                dlg.reject()
            return

    widgets['cat_ok'].clicked.connect(do_category_ok)
    try:
        widgets['cat_select_combo'].activated.connect(_on_cat_combo_activated)
    except Exception:
        pass

    # Swallow Enter on Category inputs to avoid dialog auto-accept.
    class _CategoryEnterFilter(QObject):
        def eventFilter(self, obj, event):
            if event.type() == QEvent.KeyPress:
                key = event.key()
                if key in (Qt.Key_Return, Qt.Key_Enter):
                    if obj is widgets.get('cat_add_le'):
                        _on_cat_add_enter()
                        return True
                    if obj is widgets.get('cat_update_le'):
                        _on_cat_update_enter()
                        return True
                    if obj is widgets.get('cat_select_combo'):
                        # If the popup is open, let it handle selection.
                        try:
                            if obj.view().isVisible():
                                return False
                        except Exception:
                            pass
                        _on_cat_combo_activated(obj.currentIndex())
                        return True
                    if obj is widgets.get('cat_ok'):
                        do_category_ok()
                        return True
            return False

    try:
        _cat_filter = _CategoryEnterFilter(dlg)
        widgets['cat_add_le'].installEventFilter(_cat_filter)
        widgets['cat_select_combo'].installEventFilter(_cat_filter)
        widgets['cat_update_le'].installEventFilter(_cat_filter)
        widgets['cat_ok'].installEventFilter(_cat_filter)
    except Exception:
        pass

    def _cancel_close() -> None:
        # Info-level so it won't override any warning/error queued earlier.
        try:
            if getattr(dlg, '_skip_close_status', False):
                dlg.reject()
                return
        except Exception:
            pass
        try:
            if getattr(dlg, 'main_status_msg', None):
                dlg.reject()
                return
        except Exception:
            pass
        set_dialog_main_status_max(dlg, 'Product menu closed.', level='info', duration=3000)
        dlg.reject()

    widgets['add_cancel'].clicked.connect(_cancel_close)
    widgets['rem_cancel'].clicked.connect(_cancel_close)
    widgets['upd_cancel'].clicked.connect(_cancel_close)
    widgets['cat_cancel'].clicked.connect(_cancel_close)
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

    # Admin-only Category tab
    is_admin = bool(getattr(main_window, 'current_is_admin', False))
    if not is_admin:
        widgets['tabs'].setTabEnabled(3, False)

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

    # Initialize Category tab mode (Add is default in UI)
    _set_category_add_mode()

    try:
        widgets['cat_add_radio'].toggled.connect(lambda checked: checked and _set_category_add_mode())
        widgets['cat_remove_radio'].toggled.connect(lambda checked: checked and _set_category_remove_mode())
        widgets['cat_replace_radio'].toggled.connect(lambda checked: checked and _set_category_replace_mode())
    except Exception:
        pass
    return dlg