"""Vegetable Menu dialog controller (Veg01–Veg16)."""
import os
from PyQt5 import uic
from PyQt5.QtCore import Qt, QDateTime, QTimer
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QLineEdit, 
    QComboBox, QLabel
)
from modules.ui_utils.error_logger import log_error
from modules.ui_utils.focus_utils import FieldCoordinator
from modules.ui_utils import input_handler, input_validation, ui_feedback

from modules.ui_utils.dialog_utils import load_ui_strict, report_exception_post_close, set_dialog_main_status_max

from modules.db_operation import PRODUCT_CACHE, get_product_full, get_product_slim, add_product, delete_product
from modules.db_operation.product_cache import _to_camel_case, _norm

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
QSS_PATH = os.path.join(ASSETS_DIR, 'dialog.qss')

# Vegetable slot count
VEG_SLOTS = 16
DEFAULT_VEG_CATEGORY = 'Vegetable'


def open_vegetable_menu_dialog(host_window):
    """Create the dialog; DialogWrapper owns showing/cleanup/focus restore."""
    ui_path = os.path.join(UI_DIR, 'vegetable_menu.ui')
    content = load_ui_strict(ui_path, host_window=host_window, dialog_name='Vegetable menu')
    if content is None:
        return None

    # Wrap in QDialog if needed
    if isinstance(content, QDialog):
        dlg = content
    else:
        dlg = QDialog(host_window)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(content)

    # Modal, frameless
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
            try:
                log_error(f"Failed to load dialog.qss: {e}")
            except Exception:
                pass

    # Widgets
    combo_vegetable = dlg.findChild(QComboBox, 'vegMChooseComboBox')
    input_product_code = dlg.findChild(QLineEdit, 'vegMProductCodeLineEdit')
    input_product_name = dlg.findChild(QLineEdit, 'vegMProductNameLineEdit')
    input_selling_price = dlg.findChild(QLineEdit, 'vegMSellingPriceLineEdit')
    combo_unit = dlg.findChild(QComboBox, 'vegMUnitComboBox')
    input_supplier = dlg.findChild(QLineEdit, 'vegMSupplierLineEdit')
    input_cost_price = dlg.findChild(QLineEdit, 'vegMCostPriceLineEdit')
    input_category = dlg.findChild(QLineEdit, 'vegMCategoryLineEdit')
    lbl_error = dlg.findChild(QLabel, 'vegMStatusLabel')
    btn_add = dlg.findChild(QPushButton, 'btnVegMOk')
    btn_remove = dlg.findChild(QPushButton, 'btnVegMDel')
    btn_cancel = dlg.findChild(QPushButton, 'btnVegMCancel')
    custom_close_btn = dlg.findChild(QPushButton, 'customCloseBtn')

    # Avoid QDialog default-button auto-accept.
    for _btn in (btn_add, btn_remove, btn_cancel, custom_close_btn):
        if _btn is None:
            continue
        try:
            _btn.setAutoDefault(False)
            _btn.setDefault(False)
        except Exception:
            pass

    # Fixed display fields
    if input_product_code is not None:
        input_product_code.setFocusPolicy(Qt.NoFocus)
        input_product_code.setReadOnly(True)

    # Category is fixed for veg slots.
    if input_category is not None:
        input_category.setFocusPolicy(Qt.NoFocus)
        input_category.setReadOnly(True)
        input_category.setPlaceholderText('-- As per Vegetable selection --')
        input_category.setText('')

    # Coordinator
    coord = FieldCoordinator(dlg)
    dlg._coord = coord

    # Status helpers
    def show_error(msg: str, source=None):
        if lbl_error is not None:
            coord.set_error(source, msg, status_label=lbl_error)

    def show_ok(msg: str):
        if lbl_error is not None:
            coord.set_ok(msg, status_label=lbl_error)

    def clear_error():
        if lbl_error is not None:
            coord.clear_status(lbl_error)

    # Editable controls (enabled only when a slot is selected)
    editable_widgets = [
        input_product_name,
        input_selling_price,
        combo_unit,
        input_supplier,
        input_cost_price,
    ]

    # Preserve original focus policies so we can restore them.
    _orig_focus_policy = {}
    for w in editable_widgets:
        if w is not None:
            _orig_focus_policy[w] = w.focusPolicy()

    def set_editable_enabled(enabled: bool) -> None:
        """Enable/disable editing widgets based on whether a Veg slot is selected."""
        for w in editable_widgets:
            if w is None:
                continue

            try:
                w.setEnabled(enabled)
            except Exception:
                pass

            try:
                w.setFocusPolicy(_orig_focus_policy.get(w, Qt.StrongFocus) if enabled else Qt.NoFocus)
            except Exception:
                pass

            # Ensure line edits are actually non-editable when disabled.
            if isinstance(w, QLineEdit):
                try:
                    w.setReadOnly(not enabled)
                except Exception:
                    pass

    # Populate slot combobox
    if combo_vegetable is not None:
        combo_vegetable.clear()
        # Add placeholder item at top
        combo_vegetable.addItem('Select Vegetable to update', userData=None)

        # Add placeholders immediately so the dialog can render without waiting
        # on any DB/cache work. We fill real names lazily (below).
        _slot_indices = {}
        for i in range(1, VEG_SLOTS + 1):
            code = f'Veg{i:02d}'
            placeholder = f'VEGETABLE {i}'
            combo_vegetable.addItem(placeholder, userData=code)
            _slot_indices[code] = combo_vegetable.count() - 1

        def _refresh_slot_labels() -> None:
            if combo_vegetable is None:
                return
            db_error_reported = False
            for i in range(1, VEG_SLOTS + 1):
                code = f'Veg{i:02d}'
                idx = _slot_indices.get(code)
                if idx is None:
                    continue

                name = None
                try:
                    rec = PRODUCT_CACHE.get(_norm(code)) if PRODUCT_CACHE else None
                    if rec and rec[0]:
                        name = str(rec[0])
                except Exception:
                    name = None

                if not name:
                    try:
                        found, db_name, _price, _unit = get_product_slim(code)
                        if found and str(db_name).strip():
                            name = _to_camel_case(db_name)
                    except Exception as e:
                        if not db_error_reported:
                            report_exception_post_close(
                                dlg,
                                'VegetableMenu: get_product_slim(Veg01..Veg16)',
                                e,
                                user_message='Warning: Failed to load vegetable names',
                                level='warning',
                                duration=5000,
                            )
                            db_error_reported = True
                        break

                if name:
                    try:
                        combo_vegetable.setItemText(idx, name)
                    except Exception:
                        pass

        # Defer label refresh so the dialog isn't blocked during open.
        QTimer.singleShot(0, _refresh_slot_labels)

    def _set_unit_combo(unit_text: str, *, blank_if_missing: bool = False) -> None:
        if combo_unit is None:
            return
        txt = (unit_text or '').strip()
        if not txt:
            try:
                combo_unit.setCurrentIndex(-1 if blank_if_missing else 0)
            except Exception:
                pass
            return
        # Case-insensitive match for unit
        for i in range(combo_unit.count()):
            try:
                if combo_unit.itemText(i).strip().casefold() == txt.casefold():
                    combo_unit.setCurrentIndex(i)
                    return
            except Exception:
                continue

    def _slot_lookup(_val: str):
        """Lookup selected Veg slot and normalize to coordinator targets."""
        if combo_vegetable is None:
            return None, 'No vegetable selector'
        code = combo_vegetable.currentData()
        if not code:
            return None, 'Select a vegetable slot'
        code = str(code)

        out = {
            'code': code,
            'category': DEFAULT_VEG_CATEGORY,
            'name': '',
            'price': '',
            'supplier': '',
            'cost': '',
            'unit': '',
            '_found': False,
        }

        try:
            found, details = get_product_full(code)
        except Exception as e:
            report_exception_post_close(
                dlg,
                f'VegetableMenu: get_product_full({code})',
                e,
                user_message='Error: Failed to load vegetable details',
                level='error',
                duration=5000,
            )
            return out, 'DB error'
        if found and details and details.get('name'):
            out['_found'] = True
            out['name'] = _to_camel_case(details.get('name', '') or '')
            out['price'] = str(details.get('price', '') or '')
            out['supplier'] = _to_camel_case(details.get('supplier', '') or '')
            out['cost'] = str(details.get('cost', '') or '')
            out['unit'] = _to_camel_case(details.get('unit', '') or '')
        return out, None

    def _on_slot_sync(result: dict | None):
        def _set_blank_form() -> None:
            if input_product_code is not None:
                input_product_code.setText('')
            if input_product_name is not None:
                input_product_name.setText('')
            if input_selling_price is not None:
                input_selling_price.setText('')
            if input_cost_price is not None:
                input_cost_price.setText('')
            if input_supplier is not None:
                input_supplier.setText('')
            if input_category is not None:
                input_category.setText('')
            _set_unit_combo('', blank_if_missing=True)

        if not result:
            set_editable_enabled(False)
            clear_error()
            _set_blank_form()
            return

        set_editable_enabled(True)
        # Category is fixed for veg slots
        if input_category is not None:
            input_category.setText(DEFAULT_VEG_CATEGORY)

        _set_unit_combo(result.get('unit', '') or '', blank_if_missing=False)
        if result.get('_found'):
            show_ok('Loaded')
        else:
            clear_error()

    if combo_vegetable is not None:
        coord.add_link(
            source=combo_vegetable,
            target_map={
                'code': input_product_code,
                'name': input_product_name,
                'price': input_selling_price,
                'supplier': input_supplier,
                'cost': input_cost_price,
                'category': input_category,
            },
            lookup_fn=_slot_lookup,
            next_focus=input_product_name,
            status_label=None,
            on_sync=_on_slot_sync,
            auto_jump=True,
            placeholder_mode='reactive'
        )
    
    # Initial state
    if combo_vegetable is not None and combo_vegetable.count() > 0:
        try:
            combo_vegetable.setCurrentIndex(0)
        except Exception:
            pass
        combo_vegetable.setFocus()
    set_editable_enabled(False)
    # Ensure fields are blank until a real slot is selected
    try:
        _set_unit_combo('', blank_if_missing=True)
    except Exception:
        pass
    if input_category is not None:
        input_category.setText('')

    def vegetable_name_exists_elsewhere(selected_code: str, candidate_name: str) -> bool:
        """Return True if candidate_name already exists in another Veg slot."""
        needle = _to_camel_case(candidate_name).strip().casefold()
        if not needle:
            return False
        sel_norm = _norm(selected_code)
        for i in range(1, VEG_SLOTS + 1):
            code = f'Veg{i:02d}'
            if _norm(code) == sel_norm:
                continue
            other_name = None
            try:
                rec = PRODUCT_CACHE.get(_norm(code)) if PRODUCT_CACHE else None
                if rec and rec[0]:
                    other_name = str(rec[0])
            except Exception:
                other_name = None

            if not other_name:
                try:
                    found, db_name, _price, _unit = get_product_slim(code)
                    if found and str(db_name).strip():
                        other_name = _to_camel_case(db_name)
                except Exception:
                    # Best-effort duplicate protection; don't block saving.
                    continue

            if other_name and other_name.strip().casefold() == needle:
                return True
        return False

    def get_current_vegetables():
        """Returns list of dicts with vegetable data from cache."""
        vegetables = []
        for i in range(1, VEG_SLOTS + 1):
            code = f'Veg{i:02d}'
            try:
                found, details = get_product_full(code)
            except Exception as e:
                report_exception_post_close(
                    dlg,
                    f'VegetableMenu: get_product_full({code})',
                    e,
                    user_message='Warning: DB read failed',
                    level='warning',
                    duration=5000,
                )
                continue
            if found and details.get('name'):
                vegetables.append({
                    'code': code,
                    'name': _to_camel_case(details['name']),
                    'price': details.get('price', 0.0),
                    'category': _to_camel_case(details.get('category', 'Vegetable')),
                    'supplier': _to_camel_case(details.get('supplier', '')),
                    'cost': details.get('cost', None),
                    'unit': _to_camel_case(details.get('unit', 'Kg')),
                })
        return vegetables

    def sort_and_update_database(vegetables_list):
        """Sort vegetables A-Z and rewrite Veg01-Veg16 in the DB.

        Cache note: PRODUCT_CACHE is kept in sync in-memory because we call
        modules.db_operation.delete_product() and add_product() for each slot,
        and those functions update PRODUCT_CACHE in-place (remove/upsert).
        """
        # Sort A–Z
        sorted_vegs = sorted(vegetables_list, key=lambda v: v['name'].casefold())
        
        # Rewrite Veg01–Veg16
        try:
            for i in range(1, VEG_SLOTS + 1):
                ok, msg = delete_product(f'Veg{i:02d}')
                # "Product not found" is expected for empty slots.
                if not ok and str(msg or '').strip().lower() != 'product not found':
                    try:
                        log_error(f"VegetableMenu rewrite delete failed (Veg{i:02d}): {msg}")
                    except Exception:
                        pass
                    set_dialog_main_status_max(dlg, 'Error: Failed to rewrite vegetables', level='error', duration=5000)
                    return False, str(msg)
        except Exception as e:
            report_exception_post_close(
                dlg,
                'VegetableMenu: delete_product(Veg01..Veg16)',
                e,
                user_message='Error: Failed to rewrite vegetables',
                level='error',
                duration=5000,
            )
            return False, str(e)
        
        # Insert sorted vegetables sequentially
        try:
            for i, veg in enumerate(sorted_vegs, start=1):
                now_str = QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss')
                from modules.table.unit_helpers import canonicalize_unit
                ok, msg = add_product(
                    product_code=f'Veg{i:02d}',
                    name=_to_camel_case(veg['name']),
                    selling_price=veg['price'],
                    category=_to_camel_case(veg.get('category', 'Vegetable')),
                    supplier=_to_camel_case(veg.get('supplier')),
                    cost_price=veg.get('cost'),
                    unit=canonicalize_unit(veg.get('unit', 'Kg')),
                    last_updated=now_str
                )
                if not ok:
                    try:
                        log_error(f"VegetableMenu rewrite add failed (Veg{i:02d}): {msg}")
                    except Exception:
                        pass
                    set_dialog_main_status_max(dlg, 'Error: Failed to rewrite vegetables', level='error', duration=5000)
                    return False, str(msg)
        except Exception as e:
            report_exception_post_close(
                dlg,
                'VegetableMenu: add_product(Veg01..Veg16)',
                e,
                user_message='Error: Failed to rewrite vegetables',
                level='error',
                duration=5000,
            )
            return False, str(e)
        
        # Cache updates in-place via delete_product/add_product.
        return True, 'OK'

    # Handlers
    def on_add_clicked():
        clear_error()

        if combo_vegetable is None:
            show_error('Error: No vegetable selector', source=combo_vegetable)
            return

        selected_code = combo_vegetable.currentData()
        if not selected_code:
            show_error('Error: Select vegetable slot', source=combo_vegetable)
            combo_vegetable.setFocus()
            return
        selected_code = str(selected_code)

        # Validate
        try:
            name = input_handler.handle_product_name_input(input_product_name)
        except ValueError as e:
            show_error(f'Error: {e}', source=input_product_name)
            if input_product_name is not None:
                input_product_name.setFocus()
                input_product_name.selectAll()
            return

        try:
            unit_raw = input_handler.handle_unit_input_combo(combo_unit) if combo_unit else ''
        except ValueError as e:
            show_error(f'Error: {e}', source=combo_unit)
            if combo_unit is not None:
                combo_unit.setFocus()
            return

        try:
            price = input_handler.handle_price_input(input_selling_price, price_type='Selling price')
        except ValueError as e:
            show_error(f'Error: {e}', source=input_selling_price)
            if input_selling_price is not None:
                input_selling_price.setFocus()
                input_selling_price.selectAll()
            return

        # Disallow duplicates across slots
        try:
            if vegetable_name_exists_elsewhere(selected_code, name):
                show_error('Error: Vegetable already exists', source=input_product_name)
                if input_product_name is not None:
                    input_product_name.setFocus()
                    input_product_name.selectAll()
                return
        except Exception:
            pass

        from modules.table.unit_helpers import canonicalize_unit
        unit = canonicalize_unit(unit_raw)

        supplier = None
        try:
            supplier_raw = input_handler.handle_supplier_input(input_supplier) if input_supplier else ''
            supplier_raw = supplier_raw.strip()
            supplier = _to_camel_case(supplier_raw) if supplier_raw else None
        except ValueError as e:
            show_error(f'Error: {e}', source=input_supplier)
            if input_supplier is not None:
                input_supplier.setFocus()
                input_supplier.selectAll()
            return

        cost = None
        cost_raw = (input_cost_price.text() or '').strip() if input_cost_price else ''
        if cost_raw:
            ok, err = input_validation.validate_cost_price(cost_raw)
            if not ok:
                show_error(f'Error: {err}', source=input_cost_price)
                if input_cost_price is not None:
                    input_cost_price.setFocus()
                    input_cost_price.selectAll()
                return
            try:
                cost = float(cost_raw)
            except Exception:
                show_error('Error: Cost price must be a number', source=input_cost_price)
                if input_cost_price is not None:
                    input_cost_price.setFocus()
                    input_cost_price.selectAll()
                return
        
        # Update the set, then rewrite sorted slots
        vegetables = get_current_vegetables()
        
        # Replace or append
        existing = None
        for i, veg in enumerate(vegetables):
            if veg['code'] == selected_code:
                existing = i
                break
        
        new_veg = {
            'code': selected_code,
            'name': _to_camel_case(name),
            'price': price,
            'category': _to_camel_case(DEFAULT_VEG_CATEGORY),
            'supplier': supplier,
            'cost': cost,
            'unit': unit  # already canonical
        }
        
        if existing is not None:
            vegetables[existing] = new_veg
        else:
            vegetables.append(new_veg)
        
        ok, msg = sort_and_update_database(vegetables)
        if ok:
            dlg.accept()
            return
        show_error(f'Error: {msg}')

    def on_remove_clicked():
        clear_error()
        
        if combo_vegetable is None:
            show_error('Error: No vegetable selected', source=combo_vegetable)
            return
        
        selected_code = combo_vegetable.currentData()
        if not selected_code:
            show_error('Error: Invalid vegetable selection', source=combo_vegetable)
            if combo_vegetable is not None:
                combo_vegetable.setFocus()
            return
        
        # Check DB (slim) to confirm there's something to remove.
        try:
            found, db_name, _price, _unit = get_product_slim(str(selected_code))
        except Exception as e:
            report_exception_post_close(
                dlg,
                f'VegetableMenu: get_product_slim({selected_code})',
                e,
                user_message='Error: Failed to read vegetable',
                level='error',
                duration=5000,
            )
            show_error('Error: Failed to read vegetable', source=combo_vegetable)
            if combo_vegetable is not None:
                combo_vegetable.setFocus()
            return

        if not found or not str(db_name).strip():
            # Extract placeholder number for error message
            placeholder_num = str(selected_code).replace('Veg', '').lstrip('0')
            show_error(f'Error: No vegetable added for VEGETABLE {placeholder_num}', source=combo_vegetable)
            if combo_vegetable is not None:
                combo_vegetable.setFocus()
            return
        
        # Remove and rewrite
        vegetables = get_current_vegetables()
        
        # Remove the selected vegetable
        vegetables = [v for v in vegetables if v['code'] != selected_code]
        
        ok, msg = sort_and_update_database(vegetables)
        if ok:
            dlg.accept()
            return
        show_error(f'Error: {msg}')

    def on_cancel_clicked():
        dlg.reject()

    # Enter-to-next navigation
    if isinstance(input_product_name, QLineEdit):
        coord.add_link(source=input_product_name, lookup_fn=None, next_focus=combo_unit)
    if isinstance(combo_unit, QComboBox):
        coord.add_link(source=combo_unit, lookup_fn=None, next_focus=input_selling_price)
    if isinstance(input_selling_price, QLineEdit):
        coord.add_link(source=input_selling_price, lookup_fn=None, next_focus=input_cost_price)
    if isinstance(input_cost_price, QLineEdit):
        coord.add_link(source=input_cost_price, lookup_fn=None, next_focus=input_supplier)
    if isinstance(input_supplier, QLineEdit):
        coord.add_link(source=input_supplier, lookup_fn=None, next_focus=lambda: btn_add.click() if btn_add else None)

    # Wire buttons (defensive: disconnect .ui hooks)
    if btn_add is not None:
        try:
            btn_add.clicked.disconnect()
        except Exception:
            pass
        btn_add.clicked.connect(on_add_clicked)
    if btn_remove is not None:
        try:
            btn_remove.clicked.disconnect()
        except Exception:
            pass
        btn_remove.clicked.connect(on_remove_clicked)
    if btn_cancel is not None:
        try:
            btn_cancel.clicked.disconnect()
        except Exception:
            pass
        btn_cancel.clicked.connect(on_cancel_clicked)
    if custom_close_btn is not None:
        try:
            custom_close_btn.clicked.disconnect()
        except Exception:
            pass
        custom_close_btn.clicked.connect(on_cancel_clicked)

    # Keep sync on arrow navigation
    if combo_vegetable is not None:
        combo_vegetable.currentIndexChanged.connect(lambda _i: coord._sync_fields(combo_vegetable))

    # Auto-clear error on correction (opt-in)
    if lbl_error is not None:
        if isinstance(input_product_name, QLineEdit):
            coord.register_validator(
                input_product_name,
                lambda: input_handler.handle_product_name_input(input_product_name),
                status_label=lbl_error
            )
        if isinstance(combo_unit, QComboBox):
            coord.register_validator(
                combo_unit,
                lambda: input_handler.handle_unit_input_combo(combo_unit),
                status_label=lbl_error
            )
        if isinstance(input_selling_price, QLineEdit):
            coord.register_validator(
                input_selling_price,
                lambda: input_handler.handle_price_input(input_selling_price, price_type='Selling price'),
                status_label=lbl_error
            )
        if isinstance(input_supplier, QLineEdit):
            coord.register_validator(
                input_supplier,
                lambda: input_handler.handle_supplier_input(input_supplier),
                status_label=lbl_error
            )
        if isinstance(input_cost_price, QLineEdit):
            def _validate_cost_field():
                txt = (input_cost_price.text() or '').strip()
                if not txt:
                    return True
                ok, err = input_validation.validate_cost_price(txt)
                if not ok:
                    raise ValueError(err)
                float(txt)
                return True
            coord.register_validator(input_cost_price, _validate_cost_field, status_label=lbl_error)

    return dlg

