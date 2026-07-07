import os
from functools import partial

from PyQt5.QtWidgets import QTableWidget, QPushButton, QLabel, QLineEdit
from PyQt5.QtCore import Qt

# Centralized Utilities
from modules.ui_utils.focus_utils import FieldCoordinator
from modules.db_operation import get_product_info
from modules.db_operation import PRODUCT_CACHE
from modules.ui_utils import input_validation, ui_feedback
from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui,
    build_error_fallback_dialog,
    log_exception_traceback_and_postclose_statusBar,
    require_widgets,
    set_dialog_main_status_max,
)
from modules.domain.unit_helpers import canonicalize_unit
from modules.table_ui.table_operations import (
    setup_sales_table, get_sales_data, set_table_rows, 
    bind_status_label, bind_next_focus_widget, bind_rows_changed_listener
)
from config import MAIN_STATUS_LONG_DURATION_MS, QSS_DIR, UI_DIR, VEG_KG_MANUAL_GRAMS_FALLBACK


UI_PATH = os.path.join(UI_DIR, 'vegetable_entry.ui')
QSS_PATH = os.path.join(QSS_DIR, 'dialog.qss')

def weight_simulation() -> int:
    # raise RuntimeError("Testing scale failure") # debug
    return 600  # imaginary 600g from the scale

def launch_vegetable_entry_dialog(parent, main_sales_table):
    """
    Opens the vegetable entry dialog.
    Enforces MAX_TABLE_ROWS before opening.
    """
    from config import MAX_TABLE_ROWS
    from modules.ui_utils.max_rows_dialog import open_max_rows_dialog

    # GUARD: Check if main table is already full before allowing entry
    if main_sales_table is None:
        dlg_max = open_max_rows_dialog(parent, "Internal error: main_sales_table is not available.")
        dlg_max.exec_()
        return None
    if main_sales_table.rowCount() >= MAX_TABLE_ROWS:
        dlg_max = open_max_rows_dialog(parent, f"Maximum of {MAX_TABLE_ROWS} items reached. Hold current sale or PAY to continue")
        dlg_max.exec_()
        return None

    dlg = build_dialog_from_ui(
        UI_PATH,
        host_window=parent,
        dialog_name='Vegetable Entry',
        qss_path=QSS_PATH,
    )
    if dlg is None:
        return build_error_fallback_dialog(parent, 'Vegetable Entry', QSS_PATH)

    required = {
        'table': (QTableWidget, 'vegEntryTable'),
        'status': (QLabel, 'vegEStatusLabel'),
        'ok_btn': (QPushButton, 'btnVegEOk'),
        'cancel_btn': (QPushButton, 'btnVegECancel'),
        'close_btn': (QPushButton, 'customCloseBtn'),
    }
    required.update({
        f'veg_btn_{i}': (QPushButton, f'vegEButton{i}')
        for i in range(1, 17)
    })
    widgets = require_widgets(dlg, required, hard_fail=True)

    coord = FieldCoordinator(dlg)
    dlg._coord = coord
    dlg._veg_widgets = widgets
    # Store reference to main table for row limit checks during addition
    dlg._main_sales_table = main_sales_table

    for btn in dlg.findChildren(QPushButton):
        btn.setAutoDefault(False)
        btn.setDefault(False)

    vtable = widgets['table']
    status_lbl = widgets['status']
    ok_btn = widgets['ok_btn']
    cancel_btn = widgets['cancel_btn']
    close_btn = widgets['close_btn']

    # This allows Enter key to work on dialog buttons
    for btn in [ok_btn, cancel_btn, close_btn]:
        coord.add_link(btn)

    setup_sales_table(vtable)
    bind_status_label(vtable, status_lbl)
    bind_next_focus_widget(vtable, ok_btn)
    bind_rows_changed_listener(vtable, lambda _table: _refresh_vegetable_table_state(dlg, vtable))

    # Link OK button to coordinator so Enter clicks it when focused
    coord.add_link(ok_btn, next_focus=None)

    # Initialize Veg Buttons
    for i in range(1, 17):
        btn = widgets[f'veg_btn_{i}']

        coord.add_link(btn)
        
        veg_code = f'VEG{i:02d}'
        #raise RuntimeError("Testing Vegetable Entry product lookup failure") # debug
        found, product_name, unit_price, unit = get_product_info(veg_code)
        
        if found:
            btn.setText(product_name); btn.setEnabled(True)
            unit_canon = canonicalize_unit(unit)
            btn.setFocusPolicy(Qt.StrongFocus)
            btn.setProperty('base_enabled', True)
            btn.setProperty('base_focus_policy', int(Qt.StrongFocus))
            btn.setProperty('state', 'activeKg' if unit_canon == 'Kg' else 'activeEach')
            btn.clicked.connect(partial(_handle_vegetable_button_click, dlg, status_lbl, vtable, veg_code, product_name, unit_price, unit))
        else:
            btn.setText('empty'); btn.setEnabled(False)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setProperty('base_enabled', False)
            btn.setProperty('base_focus_policy', int(Qt.NoFocus))
            btn.setProperty('state', 'empty')
        
        btn.style().unpolish(btn); btn.style().polish(btn)

    def handle_cancel():
        set_dialog_main_status_max(
            dlg,
            "Vegetable entry cancelled.",
            level="info",
        )
        dlg.reject()

    ok_btn.clicked.connect(lambda: _handle_ok_all(dlg, vtable, status_lbl))
    cancel_btn.clicked.connect(handle_cancel)
    close_btn.clicked.connect(handle_cancel)

    cancel_btn.setFocus()
    return dlg

def _handle_vegetable_button_click(dlg, msg_label, vtable, code, name, price, unit):
    unit_canon = canonicalize_unit(unit)

    if unit_canon == 'Kg':
        # Temporary fallback path: manual whole-gram input while scale hardware is unavailable.
        if VEG_KG_MANUAL_GRAMS_FALLBACK:
            try:
                added = _add_vegetable_row(
                    dlg,
                    vtable,
                    name,
                    0.0,
                    price,
                    editable=True,
                    unit='Kg',
                    manual_kg_grams=True,
                )
            except Exception as exc:
                _report_vegetable_runtime_failure(
                    dlg,
                    msg_label,
                    f"Vegetable Entry staging table ({code}, {name})",
                    exc,
                    local_message=f"Unable to add {name} to the vegetable table.",
                    user_message="Error: Vegetable table update failed",
                )
                return
            if not added:
                return
            ui_feedback.set_status_label(msg_label, f"Enter {name} weight in grams", ok=True)
            _focus_manual_kg_editor(vtable, name)
            _sync_pending_qty_state(dlg, vtable)
            return

        ui_feedback.set_status_label(msg_label, f"Place {name} on scale...", ok=True)
        try:
            w_grams = weight_simulation()
        except Exception as exc:
            _report_vegetable_runtime_failure(
                dlg,
                msg_label,
                f"Vegetable Entry scale ({code}, {name})",
                exc,
                local_message=f"Scale error. Unable to add {name}.",
                user_message=f"Error: Unable to weigh {name}",
            )
            return

        if w_grams <= 0:
            ui_feedback.set_status_label(msg_label, "Error: Invalid weight", ok=False)
            return

        w_kg = w_grams / 1000.0
        try:
            added = _add_vegetable_row(
                dlg,
                vtable,
                name,
                w_kg,
                price,
                editable=False,
                unit='Kg',
                manual_kg_grams=False,
            )
        except Exception as exc:
            _report_vegetable_runtime_failure(
                dlg,
                msg_label,
                f"Vegetable Entry staging table ({code}, {name})",
                exc,
                local_message=f"Unable to add {name} to the vegetable table.",
                user_message="Error: Vegetable table update failed",
            )
            return
        if not added:
            return
        ui_feedback.set_status_label(msg_label, f"Added {name}: {w_grams}g", ok=True)
    else:
        # EACH rows remain editable; pending-state protection handles empty/invalid qty.
        try:
            added = _add_vegetable_row(
                dlg, vtable, name, 1.0, price, editable=True, unit='Each'
            )
        except Exception as exc:
            _report_vegetable_runtime_failure(
                dlg,
                msg_label,
                f"Vegetable Entry staging table ({code}, {name})",
                exc,
                local_message=f"Unable to add {name} to the vegetable table.",
                user_message="Error: Vegetable table update failed",
            )
            return
        if not added:
            return
        ui_feedback.set_status_label(msg_label, f"Added {name}", ok=True)

    # Shift focus to OK
    dlg._veg_widgets['ok_btn'].setFocus()
    _sync_pending_qty_state(dlg, vtable)


# ---------------------------------------------------------------------------
# Temporary KG manual-grams fallback helpers
# ---------------------------------------------------------------------------

def _focus_manual_kg_editor(vtable, name) -> None:
    for row in range(vtable.rowCount()):
        item = vtable.item(row, 1)
        qty_container = vtable.cellWidget(row, 2)
        if not (item and qty_container):
            continue
        if item.text().strip().lower() != name.strip().lower():
            continue
        editor = qty_container.findChild(QLineEdit, 'qtyInput')
        if editor and bool(editor.property('manual_kg_grams')):
            editor.setFocus()
            editor.selectAll()
            return


def _validate_vegetable_qty_editor(editor: QLineEdit) -> float:
    if bool(editor.property('manual_kg_grams')):
        text = (editor.text() or '').strip()
        if not text:
            raise ValueError("Enter weight in grams")
        if not text.isdigit():
            raise ValueError("Weight must be entered as whole grams")
        qty_kg = int(text) / 1000.0
        ok, err = input_validation.validate_quantity(str(qty_kg), unit_type='kg')
        if not ok:
            raise ValueError(err or "Invalid weight")
        return qty_kg
    from modules.ui_utils import input_handler
    return input_handler.handle_quantity_input(editor, unit_type='unit')


# ---------------------------------------------------------------------------
# Vegetable quantity pending-state protection
# ---------------------------------------------------------------------------

def _vegetable_qty_editor_is_valid(editor: QLineEdit) -> bool:
    try:
        _validate_vegetable_qty_editor(editor)
        return True
    except Exception:
        return False


def _pending_qty_editor(vtable):
    for row in range(vtable.rowCount()):
        qty_container = vtable.cellWidget(row, 2)
        if not qty_container:
            continue
        editor = qty_container.findChild(QLineEdit, 'qtyInput')
        if editor and not editor.isReadOnly() and not _vegetable_qty_editor_is_valid(editor):
            return editor
    return None


def _sync_pending_qty_state(dlg, vtable) -> None:
    pending_editor = _pending_qty_editor(vtable)
    pending = pending_editor is not None
    try:
        dlg._veg_widgets['ok_btn'].setEnabled(not pending)
        dlg._veg_widgets['ok_btn'].setFocusPolicy(Qt.NoFocus if pending else Qt.StrongFocus)
    except Exception:
        pass

    for i in range(1, 17):
        btn = dlg._veg_widgets.get(f'veg_btn_{i}')
        if btn is None:
            continue
        base_enabled = bool(btn.property('base_enabled'))
        try:
            base_focus = Qt.FocusPolicy(int(btn.property('base_focus_policy') or int(Qt.NoFocus)))
        except Exception:
            base_focus = Qt.StrongFocus if base_enabled else Qt.NoFocus
        btn.setEnabled(False if pending else base_enabled)
        btn.setFocusPolicy(Qt.NoFocus if pending else base_focus)


def _refresh_vegetable_table_state(dlg, vtable) -> None:
    ok_btn = dlg._veg_widgets['ok_btn']
    for r in range(vtable.rowCount()):
        qty_container = vtable.cellWidget(r, 2)
        if not qty_container:
            continue
        editor = qty_container.findChild(QLineEdit, 'qtyInput')
        if not editor:
            continue
        if editor not in dlg._coord.links:
            dlg._coord.add_link(
                editor,
                next_focus=ok_btn,
                validate_fn=lambda e=editor: _validate_vegetable_qty_editor(e),
                status_label=dlg._veg_widgets['status'],
            )
        if not bool(editor.property('pending_hook_connected')):
            editor.textChanged.connect(lambda _text=None, d=dlg, t=vtable: _sync_pending_qty_state(d, t))
            editor.setProperty('pending_hook_connected', True)
    _sync_pending_qty_state(dlg, vtable)


def _report_vegetable_runtime_failure(
    dlg,
    status_label,
    where: str,
    exc: Exception,
    *,
    local_message: str,
    user_message: str,
) -> None:
    ui_feedback.set_status_label(status_label, local_message, ok=False)
    log_exception_traceback_and_postclose_statusBar(
        dlg,
        where,
        exc,
        user_message=user_message,
        level="error",
        duration=MAIN_STATUS_LONG_DURATION_MS,
    )


def _add_vegetable_row(
    dlg,
    vtable,
    name,
    quantity,
    price,
    editable,
    *,
    unit=None,
    manual_kg_grams=False,
) -> bool:
    """
    Adds/Updates a row in the vegetable entry table.
    Ensures combined (Main Table + Veg Table) row count <= MAX_TABLE_ROWS.
    """
    from config import MAX_TABLE_ROWS
    from modules.ui_utils.max_rows_dialog import open_max_rows_dialog

    current_data = get_sales_data(vtable)
    target_unit = canonicalize_unit(unit or ("Kg" if not editable else "Each"))
    
    found_in_veg_dialog = False
    for row in current_data:
        # Check if product already exists in the dialog's table to update quantity
        if (row['product_name'].strip().lower() == name.strip().lower() and row['unit'] == target_unit):
            row['quantity'] += (1.0 if target_unit == 'Each' else quantity)
            if manual_kg_grams:
                row['manual_kg_grams'] = True
            found_in_veg_dialog = True
            break
            
    if not found_in_veg_dialog:
        # GLOBAL LIMIT CHECK: 
        # Combined rows = existing in main table + current rows in vegetable dialog
        main_table_count = dlg._main_sales_table.rowCount()
        veg_table_count = vtable.rowCount()
        
        if (main_table_count + veg_table_count) >= MAX_TABLE_ROWS:
            dlg_max = open_max_rows_dialog(dlg, f"Adding this item would exceed the global limit of {MAX_TABLE_ROWS} items.")
            dlg_max.exec_()
            return False

        # If limit not reached, append the new row
        current_data.append({
            'product_name': name, 
            'quantity': quantity, 
            'unit_price': price, 
            'unit': target_unit, 
            'editable': editable,
            # Fallback metadata: editable KG rows accept whole grams but store kg.
            'manual_kg_grams': bool(manual_kg_grams),
        })
    
    # Refresh the vegetable dialog table
    #raise RuntimeError("Testing vegEntryTable population failure")
    set_table_rows(vtable, current_data)

    # CRITICAL: Register the new table editors with the Coordinator
    ok_btn = dlg._veg_widgets['ok_btn']
    for r in range(vtable.rowCount()):
        qty_container = vtable.cellWidget(r, 2)
        if qty_container:
            editor = qty_container.findChild(QLineEdit, 'qtyInput')
            if editor and editor not in dlg._coord.links:
                # Link editor to OK button for focus jump
                dlg._coord.add_link(editor, next_focus=ok_btn)
    return True

def _handle_ok_all(dlg, vtable, status_lbl):
    if vtable.rowCount() == 0:
        ui_feedback.set_status_label(
            status_lbl,
            "Add at least one vegetable before continuing.",
            ok=False,
        )
        return

    try:
        scraped_rows = get_sales_data(vtable)
        rows_to_transfer = []
        for row in scraped_rows:
            if row['quantity'] <= 0: raise ValueError(f"Quantity for '{row['product_name']}' must be > 0")
            code = next((k for k, v in PRODUCT_CACHE.items() if v[0] == row['product_name']), row['product_name'])
            transfer_row = {
                'product_code': code,
                'product_name': row['product_name'],
                'quantity': row['quantity'],
                'unit_price': row['unit_price'],
                'unit': row['unit'],
                'editable': row['editable'],
            }
            if row.get('manual_kg_grams'):
                transfer_row['manual_kg_grams'] = True
            rows_to_transfer.append(transfer_row)

        dlg.vegetable_rows = rows_to_transfer
        count = len(rows_to_transfer)
        set_dialog_main_status_max(
            dlg,
            f"{count} vegetable/s added to sale.",
            level="info",
        )
        dlg.accept()
    except ValueError as e:
        ui_feedback.set_status_label(status_lbl, str(e), ok=False)
    except Exception as exc:
        _report_vegetable_runtime_failure(
            dlg,
            status_lbl,
            "Vegetable Entry prepare result",
            exc,
            local_message="Unable to prepare vegetable items.",
            user_message="Error: Unable to prepare vegetable items",
        )
