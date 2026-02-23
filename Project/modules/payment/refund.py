import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QLineEdit, QPushButton

import modules.db_operation as dbop
from modules.ui_utils import input_handler, ui_feedback
from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui,
    require_widgets,
    set_dialog_info,
    report_exception_post_close,
)
from modules.ui_utils.focus_utils import FieldCoordinator, FocusGate, enforce_exclusive_lineedits


_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))
UI_PATH = os.path.join(_PROJECT_DIR, 'ui', 'refund.ui')
QSS_PATH = os.path.join(_PROJECT_DIR, 'assets', 'dialog.qss')


def _set_error_state(widget: QLineEdit, on: bool) -> None:
    if widget is None:
        return
    try:
        widget.setProperty('error', bool(on))
        widget.style().unpolish(widget)
        widget.style().polish(widget)
    except Exception:
        pass


def launch_refund_dialog(parent=None):
    dlg = build_dialog_from_ui(
        UI_PATH,
        host_window=parent,
        dialog_name='Refund',
        qss_path=QSS_PATH,
        frameless=True,
        application_modal=True,
    )

    if not dlg:
        from modules.ui_utils.dialog_utils import build_error_fallback_dialog
        return build_error_fallback_dialog(parent, 'Refund', QSS_PATH)

    widgets = require_widgets(dlg, {
        'code': (QLineEdit, 'refundProductCodeLineEdit'),
        'name': (QLineEdit, 'refundNameSearchLineEdit'),
        'price': (QLineEdit, 'refundPriceLineEdit'),
        'qty': (QLineEdit, 'refundQtyeLineEdit'),
        'note': (QLineEdit, 'refundNoteLineEdit'),
        'amount': (QLineEdit, 'refundAmountLineEdit'),
        'status': (QLabel, 'refundStatusLabel'),
        'ok_btn': (QPushButton, 'btnRefundOk'),
        'cancel_btn': (QPushButton, 'btnRefundCancel'),
        'close_btn': (QPushButton, 'customCloseBtn'),
    })

    code = widgets['code']
    name = widgets['name']
    price = widgets['price']
    qty = widgets['qty']
    note = widgets['note']
    amount = widgets['amount']
    status = widgets['status']
    ok_btn = widgets['ok_btn']
    cancel_btn = widgets['cancel_btn']
    close_btn = widgets['close_btn']

    try:
        note_default = (note.text() or '').strip()
        if note_default:
            note.clear()
            note.setPlaceholderText(note_default)
    except Exception:
        pass

    price.setReadOnly(True)
    price.setFocusPolicy(Qt.NoFocus)
    amount.setReadOnly(True)
    amount.setFocusPolicy(Qt.NoFocus)

    gate = FocusGate([qty, note, ok_btn], lock_enabled=True)
    gate.set_locked(True)

    def _lock_inputs(clear_values: bool = True) -> None:
        gate.set_locked(True)
        if clear_values:
            price.clear()
            qty.clear()
            amount.clear()
            note.clear()

    def _unlock_inputs(result: dict) -> None:
        gate.set_locked(False)
        price_val = float(result.get('price') or 0.0)
        price.setText(f"{price_val:.2f}")
        qty_val = 1
        qty.setText(str(qty_val))
        amount_val = round(price_val * qty_val, 2)
        amount.setText(f"{amount_val:.2f}")

    def _recompute_amount() -> float:
        unit_price = float(price.text() or 0.0)
        qty_val = input_handler.handle_quantity_input(qty, unit_type='unit')
        amount_val = round(unit_price * qty_val, 2)
        amount.setText(f"{amount_val:.2f}")
        return qty_val

    coord = FieldCoordinator(dlg)

    def _lookup_by_code(val: str):
        rec = input_handler.get_coordinator_lookup(val, 'code')
        if rec:
            return rec, None
        return None, "Product Code Not Found"

    def _lookup_by_name(val: str):
        rec = input_handler.get_coordinator_lookup(val, 'name')
        if rec:
            return rec, None
        return None, "Product name not found"

    def _clear_lookup_error_style() -> None:
        _set_error_state(code, False)
        _set_error_state(name, False)

    def _on_lookup_result(source_widget: QLineEdit, result: dict | None) -> None:
        _clear_lookup_error_style()
        if result:
            _unlock_inputs(result)
            return
        _lock_inputs(clear_values=True)

    def _on_code_sync(result):
        _on_lookup_result(code, result)

    def _on_name_sync(result):
        _on_lookup_result(name, result)

    coord.add_link(
        source=code,
        target_map={'name': name, 'price': price},
        lookup_fn=_lookup_by_code,
        next_focus=note,
        status_label=status,
        on_sync=_on_code_sync,
        auto_jump=False,
    )

    coord.add_link(
        source=name,
        target_map={'code': code, 'price': price},
        lookup_fn=_lookup_by_name,
        next_focus=note,
        status_label=status,
        on_sync=_on_name_sync,
        auto_jump=True,
    )

    coord.add_link(
        source=qty,
        next_focus=ok_btn,
        status_label=status,
        swallow_empty=True,
        validate_fn=_recompute_amount,
    )

    def _validate_note() -> str:
        val = input_handler.handle_note_input(note)
        note.setText(val)
        return val

    coord.add_link(
        source=note,
        next_focus=ok_btn,
        status_label=status,
        swallow_empty=False,
        validate_fn=_validate_note,
    )

    coord.register_validator(qty, _recompute_amount, status_label=status)
    coord.register_validator(note, _validate_note, status_label=status)

    enforce_exclusive_lineedits(
        code,
        name,
        on_switch_to_a=lambda: _lock_inputs(clear_values=True),
        on_switch_to_b=lambda: _lock_inputs(clear_values=True),
    )

    code.textEdited.connect(lambda *_: _clear_lookup_error_style())
    name.textEdited.connect(lambda *_: _clear_lookup_error_style())

    product_names = [rec[0] for rec in (dbop.PRODUCT_CACHE or {}).values() if rec and rec[0]]
    input_handler.setup_name_search_lineedit(
        name,
        product_names,
        on_selected=lambda *_: coord._sync_fields(name),
    )

    def _get_cashier_name() -> str:
        for attr in ('current_user', 'cashier_name', 'logged_in_user'):
            val = getattr(parent, attr, '') if parent is not None else ''
            if str(val or '').strip():
                return str(val).strip()
        return ''

    def _handle_ok() -> None:
        try:
            if not code.text().strip() or not name.text().strip() or not price.text().strip():
                raise ValueError("Select a product first")

            _recompute_amount()
            note_text = _validate_note()
            amount_val = float(amount.text() or 0.0)
            if amount_val <= 0:
                raise ValueError("Refund amount must be greater than 0")

            dbop.ensure_cash_outflows_table()
            dbop.add_outflow(
                outflow_type='REFUND_OUT',
                amount=amount_val,
                cashier_name=_get_cashier_name(),
                note=note_text,
            )

            set_dialog_info(dlg, f"Refund recorded: ${amount_val:.2f}", duration=4000)
            dlg.accept()
        except ValueError as exc:
            ui_feedback.set_status_label(status, str(exc), ok=False)
        except Exception as exc:
            report_exception_post_close(
                dlg,
                'Refund save',
                exc,
                user_message='Error: Unable to save refund (see error.log)',
                level='error',
                duration=6000,
            )
            dlg.reject()

    def _handle_cancel() -> None:
        set_dialog_info(dlg, 'Refund cancelled.', duration=3000)
        dlg.reject()

    ok_btn.clicked.connect(_handle_ok)
    cancel_btn.clicked.connect(_handle_cancel)
    if close_btn is not None:
        close_btn.clicked.connect(_handle_cancel)

    def barcode_override(barcode: str) -> bool:
        code.setText(barcode)
        coord._sync_fields(code)
        return True

    dlg.barcode_override_handler = barcode_override

    code.setFocus(Qt.OtherFocusReason)
    code.selectAll()
    return dlg
