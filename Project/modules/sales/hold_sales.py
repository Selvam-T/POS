import os
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLineEdit, QPushButton, QLabel

from modules.db_operation.held_sale_committer import HeldSaleCommitter
from modules.payment import receipt_generator
from modules.ui_utils.error_logger import log_error
from config import ENABLE_PRINTER_PRINT
from modules.ui_utils import input_handler, ui_feedback
from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui,
    require_widgets,
    set_dialog_main_status_max,
    report_exception_post_close,
)
from modules.ui_utils.focus_utils import FieldCoordinator, FocusGate


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')
HOLD_SALES_UI = os.path.join(UI_DIR, 'hold_sales.ui')


def _show_validation_error(status_label: QLabel, widget: QLineEdit, message: str) -> None:
    ui_feedback.set_status_label(status_label, message, ok=False)
    widget.setFocus(Qt.OtherFocusReason)
    widget.selectAll()


def _build_sales_snapshot(parent) -> list[dict]:
    if parent is None:
        return []
    try:
        if hasattr(parent, "_build_sale_items_snapshot"):
            return list(parent._build_sale_items_snapshot() or [])
    except Exception:
        pass
    return []


def launch_hold_sales_dialog(parent=None):
    qss_path = os.path.join(BASE_DIR, 'assets', 'dialog.qss')
    dlg = build_dialog_from_ui(
        HOLD_SALES_UI,
        host_window=parent,
        dialog_name='Hold Sales',
        qss_path=qss_path,
        frameless=True,
        application_modal=True,
    )

    # If load failed, return the standardized fallback immediately
    if not dlg:
        from modules.ui_utils.dialog_utils import build_error_fallback_dialog
        return build_error_fallback_dialog(parent, "Hold Sales", qss_path)

    widgets = require_widgets(dlg, {
        'name_in': (QLineEdit, 'holdSalesCustomerLineEdit'),
        'note_in': (QLineEdit, 'holdSalesNoteLineEdit'),
        'status_lbl': (QLabel, 'holdSalesStatusLabel'),
        'ok_btn': (QPushButton, 'btnHoldSalesOk'),
        'cancel_btn': (QPushButton, 'btnHoldSalesCancel'),
    })
    close_btn = dlg.findChild(QPushButton, 'customCloseBtn')

    name_in = widgets['name_in']
    note_in = widgets['note_in']
    status_lbl = widgets['status_lbl']
    ok_btn = widgets['ok_btn']
    cancel_btn = widgets['cancel_btn']

    name_in.setReadOnly(False)
    note_in.setReadOnly(False)
    name_in.setFocusPolicy(Qt.StrongFocus)
    note_in.setFocusPolicy(Qt.StrongFocus)

    gate = FocusGate([note_in, ok_btn],lock_enabled=True)
    gate.set_locked(True)

    def _set_placeholders() -> None:
        for le in (name_in, note_in):
            ui_default = (le.placeholderText() or "").strip()
            if not ui_default:
                ui_default = (le.text() or "").strip()
            le.clear()
            le.setPlaceholderText(ui_default)

    _set_placeholders()

    coord = FieldCoordinator(dlg)

    def _validate_and_normalize_name() -> str:
        val = input_handler.handle_customer_input(name_in)
        name_in.setText(val)
        return val

    def _validate_and_normalize_note() -> str:
        val = input_handler.handle_note_input(note_in)
        note_in.setText(val)
        return val

    def _unlock_and_focus_note() -> None:
        gate.set_locked(False)
        note_in.setFocus(Qt.OtherFocusReason)
        note_in.selectAll()

    def _lock_note_gate() -> None:
        gate.set_locked(True)
        note_in.clear()

    def _on_name_edited(*_args):
        _lock_note_gate()
        coord.clear_status(status_lbl)

    def _on_note_edited(*_args):
        coord.clear_status(status_lbl)

    name_in.textEdited.connect(_on_name_edited)
    note_in.textEdited.connect(_on_note_edited)

    coord.add_link(
        source=name_in,
        next_focus=_unlock_and_focus_note,
        status_label=status_lbl,
        validate_fn=_validate_and_normalize_name,
    )

    coord.add_link(
        source=note_in,
        next_focus=ok_btn,
        status_label=status_lbl,
        validate_fn=_validate_and_normalize_note,
        swallow_empty=False,
    )

    coord.register_validator(name_in, _validate_and_normalize_name, status_label=status_lbl)
    coord.register_validator(note_in, _validate_and_normalize_note, status_label=status_lbl)

    hold_committer = HeldSaleCommitter()

    def _handle_ok() -> None:
        try:
            customer_name = _validate_and_normalize_name()
        except ValueError as exc:
            _show_validation_error(status_lbl, name_in, str(exc))
            return

        try:
            note_text = _validate_and_normalize_note()
        except ValueError as exc:
            _show_validation_error(status_lbl, note_in, str(exc))
            return

        sales_items = _build_sales_snapshot(parent)
        if not sales_items:
            _show_validation_error(status_lbl, name_in, "No active sale to hold")
            return
        try:
            # uncomment to test db operation failure handling:
            # raise RuntimeError("TEST: hold sale failure")
            receipt_no = hold_committer.commit_hold_sale(
                customer_name=customer_name,
                note=note_text,
                sales_items=sales_items,
            )
            dlg.held_receipt_no = receipt_no

            if parent is not None and hasattr(parent, "_clear_sales_table_core"):
                parent._clear_sales_table_core()
            panel = getattr(parent, 'payment_panel_controller', None) if parent is not None else None
            if panel is not None:
                panel.clear_payment_frame()

            set_dialog_main_status_max(dlg, "Sale held successfully.", level='info', duration=4000)
            dlg.accept()
        except Exception as exc:
            try:
                receipt_text = receipt_generator.generate_receipt_text_from_snapshot(
                    items=sales_items,
                    receipt_no="HOLD-FAILED",
                    status="UNPAID",
                    cashier_name="",
                )
                cleared = False
                if not ENABLE_PRINTER_PRINT:
                    print(receipt_text)
                    set_dialog_main_status_max(
                        dlg,
                        "Hold failed. Receipt printed to console.",
                        level='error',
                        duration=6000,
                    )
                    cleared = True
                else:
                    from modules.devices import printer as device_printer
                    printed_ok = device_printer.print_receipt(receipt_text, blocking=True)
                    if printed_ok:
                        set_dialog_main_status_max(
                            dlg,
                            "Hold failed. Receipt printed.",
                            level='error',
                            duration=6000,
                        )
                        cleared = True
                    else:
                        log_error("Hold failed: printer send failed for snapshot receipt.")
                        set_dialog_main_status_max(
                            dlg,
                            "Hold failed. Receipt print failed.",
                            level='error',
                            duration=6000,
                        )
                if cleared and parent is not None:
                    if hasattr(parent, "_clear_sales_table_core"):
                        parent._clear_sales_table_core()
                    panel = getattr(parent, 'payment_panel_controller', None)
                    if panel is not None:
                        panel.clear_payment_frame()
            except Exception as print_exc:
                log_error(f"Hold failed: receipt print error: {print_exc}")
                set_dialog_main_status_max(
                    dlg,
                    "Hold failed. Receipt print error.",
                    level='error',
                    duration=6000,
                )
            report_exception_post_close(
                dlg,
                "Hold sale",
                exc,
                user_message="Error: Unable to hold sale (see error.log)",
                level='error',
                duration=6000,
            )
            dlg.reject()

    def _handle_close() -> None:
        set_dialog_main_status_max(dlg, "Hold Sales cancelled.", level='info', duration=4000)
        dlg.reject()

    ok_btn.clicked.connect(_handle_ok)
    cancel_btn.clicked.connect(_handle_close)
    if close_btn is not None:
        close_btn.clicked.connect(_handle_close)

    name_in.setFocus(Qt.OtherFocusReason)
    name_in.selectAll()

    return dlg
