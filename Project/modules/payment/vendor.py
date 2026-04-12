import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QLineEdit, QPushButton

import modules.db_operation as dbop
from modules.ui_utils import input_handler, ui_feedback
from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui,
    require_widgets,
    set_dialog_info,
    log_exception_traceback_and_postclose_statusBar,
)
from modules.ui_utils.focus_utils import FieldCoordinator, FocusGate

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))
UI_PATH = os.path.join(_PROJECT_DIR, 'ui', 'vendor.ui')
QSS_PATH = os.path.join(_PROJECT_DIR, 'assets', 'dialog.qss')


def launch_vendor_dialog(parent=None):
    dlg = build_dialog_from_ui(
        UI_PATH,
        host_window=parent,
        dialog_name='Vendor',
        qss_path=QSS_PATH,
        frameless=True,
        application_modal=True,
    )

    if not dlg:
        from modules.ui_utils.dialog_utils import build_error_fallback_dialog
        return build_error_fallback_dialog(parent, 'Vendor', QSS_PATH)

    widgets = require_widgets(dlg, {
        'name': (QLineEdit, 'vendorNameLineEdit'),
        'amount': (QLineEdit, 'vendorAmountLineEdit'),
        'note': (QLineEdit, 'vendorNoteLineEdit'),
        'status': (QLabel, 'vendorStatusLabel'),
        'ok_btn': (QPushButton, 'btnVendorOk'),
        'cancel_btn': (QPushButton, 'btnVendorCancel'),
        'close_btn': (QPushButton, 'customCloseBtn'),
    })

    name = widgets['name']
    amount = widgets['amount']
    note = widgets['note']
    status = widgets['status']
    ok_btn = widgets['ok_btn']
    cancel_btn = widgets['cancel_btn']
    close_btn = widgets['close_btn']

    # Ensure name is editable even if ui file marks it readOnly
    try:
        name.setReadOnly(False)
    except Exception:
        pass

    # Gate: lock amount and note until name is valid
    gate = FocusGate([amount, note, ok_btn], lock_enabled=True)
    try:
        gate.remember_placeholders([note, amount])
        gate.hide_placeholders([note, amount])
    except Exception:
        pass
    gate.set_locked(True)

    coord = FieldCoordinator(dlg)

    # Validation is delegated directly to input_handler via lambdas.

    def _lock_vendor_targets(clear_values: bool = True) -> None:
        try:
            gate.hide_placeholders([note, amount])
        except Exception:
            pass
        gate.set_locked(True)
        if clear_values:
            try:
                amount.clear()
            except Exception:
                pass
            try:
                note.clear()
            except Exception:
                pass

    def _validate_name_and_unlock():
        val = input_handler.handle_customer_input(name)
        try:
            gate.restore_placeholders([note, amount])
        except Exception:
            pass
        gate.set_locked(False)
        return val

    coord.add_link(
        source=name,
        next_focus=amount,
        status_label=status,
        swallow_empty=False,
        validate_fn=_validate_name_and_unlock,
    )

    coord.add_link(
        source=amount,
        next_focus=note,
        status_label=status,
        swallow_empty=False,
        validate_fn=lambda: input_handler.handle_currency_input(amount, asset_type='Amount'),
    )

    coord.add_link(
        source=note,
        next_focus=ok_btn,
        status_label=status,
        swallow_empty=False,
        validate_fn=lambda: input_handler.handle_note_input(note),
    )

    coord.register_validator(name, _validate_name_and_unlock, status_label=status)
    coord.register_validator(amount, lambda: input_handler.handle_currency_input(amount, asset_type='Amount'), status_label=status)

    def _on_name_text_edited(_txt=None) -> None:
        if (name.text() or '').strip():
            return
        _lock_vendor_targets(clear_values=True)
        try:
            ui_feedback.clear_status_label(status)
        except Exception:
            pass

    try:
        name.textEdited.connect(_on_name_text_edited)
    except Exception:
        pass

    # NOTE: rely on `parent.current_user_id` being set by the app login flow.
    # Do not probe multiple attributes or fall back to a magic id; require a valid integer user id.

    def _handle_ok() -> None:
        try:
            # Simulate a database failure for testing error handling
            #raise RuntimeError('Simulated DB failure')
            
            # Validate and canonicalize name
            name_val = input_handler.handle_customer_input(name)
            name.setText(name_val)

            # Validate and canonicalize amount
            amount_val = input_handler.handle_currency_input(amount, asset_type='Amount')
            try:
                amount.setText(f"{float(amount_val):.2f}")
            except Exception:
                pass

            # Note is optional; validate/canonicalize if present
            try:
                note_val = input_handler.handle_note_input(note)
            except Exception:
                # If validation fails for note, re-raise to be handled below
                raise

            dbop.ensure_cash_outflows_table()
            cid = getattr(parent, 'current_user_id', None)
            if cid is None:
                ui_feedback.set_status_label(status, 'No logged-in user. Please login.', ok=False)
                return
            dbop.add_outflow(
                outflows_type='VENDOR_OUT',
                amount=amount_val,
                cashier_id=int(cid),
                note=note_val,
            )

            set_dialog_info(dlg, f"Vendor payment recorded: ${amount_val:.2f}", duration=4000)
            dlg.accept()
        except ValueError as exc:
            ui_feedback.set_status_label(status, str(exc), ok=False)
        except Exception as exc:
            log_exception_traceback_and_postclose_statusBar(
                dlg,
                'Vendor save',
                exc,
                user_message='Error: Unable to save vendor payment (see error.log)',
                level='error',
                duration=6000,
            )
            dlg.reject()

    def _handle_cancel() -> None:
        set_dialog_info(dlg, 'Vendor payment cancelled.', duration=3000)
        dlg.reject()

    ok_btn.clicked.connect(_handle_ok)
    cancel_btn.clicked.connect(_handle_cancel)
    if close_btn is not None:
        close_btn.clicked.connect(_handle_cancel)

    def barcode_override(barcode: str) -> bool:
        # Swallow barcode input while modal vendor dialog is open.
        return True

    dlg.barcode_override_handler = barcode_override

    name.setFocus(Qt.OtherFocusReason)
    try:
        name.selectAll()
    except Exception:
        pass
    return dlg
