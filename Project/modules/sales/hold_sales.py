import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLineEdit, QPushButton, QLabel

from modules.db_operation.held_sale_committer import HeldSaleCommitter
from modules.payment import receipt_generator
from modules.db_operation.users_repo import get_username_by_id
from modules.ui_utils.error_logger import log_error
from modules.devices import print_helper
from modules.ui_utils import input_handler, ui_feedback
from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui,
    require_widgets,
    set_dialog_main_status_max,
    report_exception_post_close,
)
from modules.ui_utils.focus_utils import FieldCoordinator

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')
HOLD_SALES_UI = os.path.join(UI_DIR, 'hold_sales.ui')

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
    # Build the dialog, with error fallback if loading fails
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
        'status_lbl': (QLabel, 'holdSalesStatusLabel'),
        'ok_btn': (QPushButton, 'btnHoldSalesOk'),
        'cancel_btn': (QPushButton, 'btnHoldSalesCancel'),
    })
    close_btn = dlg.findChild(QPushButton, 'customCloseBtn')

    name_in = widgets['name_in']
    status_lbl = widgets['status_lbl']
    ok_btn = widgets['ok_btn']
    cancel_btn = widgets['cancel_btn']

    name_in.setReadOnly(False)
    name_in.setFocusPolicy(Qt.StrongFocus)

    coord = FieldCoordinator(dlg)

    def _on_name_edited(*_args):
        ui_feedback.clear_status_label(status_lbl)

    name_in.textEdited.connect(_on_name_edited)

    coord.add_link(
        source=name_in,
        next_focus=ok_btn,
        status_label=status_lbl,
        validate_fn=lambda: input_handler.handle_customer_input(name_in),
    )

    coord.register_validator(name_in, lambda: input_handler.handle_customer_input(name_in), status_label=status_lbl)

    hold_committer = HeldSaleCommitter()

    def _handle_ok() -> None:
        try:
            customer_name = input_handler.handle_customer_input(name_in)
            name_in.setText(customer_name)
        except ValueError as exc:
            ui_feedback.set_status_label(status_lbl, str(exc), ok=False)
            name_in.setFocus(Qt.OtherFocusReason)
            name_in.selectAll()
            return

        sales_items = _build_sales_snapshot(parent)
        if not sales_items:
            ui_feedback.set_status_label(status_lbl, "No active sale to hold", ok=False)
            name_in.setFocus(Qt.OtherFocusReason)
            name_in.selectAll()
            return
        try:
            # uncomment to test db operation failure handling:
            raise RuntimeError("TEST: hold sale failure")
            cid = getattr(parent, 'current_user_id', None)
            if cid is None:
                ui_feedback.set_status_label(status_lbl, "No logged-in user. Please login.", ok=False)
                name_in.setFocus(Qt.OtherFocusReason)
                name_in.selectAll()
                return
            # Commit held receipt to DB (insert receipts header + receipt_items)
            receipt_no = hold_committer.commit_hold_sale(
                customer_name=customer_name,
                sales_items=sales_items,
                cashier_id=int(cid),
            )
            dlg.held_receipt_no = receipt_no
            # Commit successful: will clear UI and accept dialog below

            if parent is not None and hasattr(parent, "_clear_sales_table_core"):
                parent._clear_sales_table_core()
            panel = getattr(parent, 'payment_panel_controller', None) if parent is not None else None
            if panel is not None:
                panel.clear_payment_frame()

            set_dialog_main_status_max(dlg, "Sale held successfully.", level='info', duration=4000)
            dlg.accept()
        except Exception as exc:
            # Commit failed: prepare snapshot receipt for fallback printing
            try:
                cid = getattr(parent, 'current_user_id', None)
                cashier_name = get_username_by_id(int(cid)) if cid is not None else ''
                receipt_text = receipt_generator.generate_receipt_text_from_snapshot(
                    items=sales_items,
                    receipt_no="Not generated - HOLD-FAILED",
                    status="UNPAID",
                    cashier_name=cashier_name or '',
                )
            except Exception as print_exc:
                # Snapshot generation failed
                log_error(f"Hold failed: receipt print error: {print_exc}")
                set_dialog_main_status_max(
                    dlg,
                    "Hold failed. Receipt print error.",
                    level='error',
                    duration=6000,
                )
            else:
                cleared = False
                print_result = print_helper.print_receipt_with_fallback(
                    receipt_text,
                    blocking=True,
                    context="Hold failed",
                )
                if print_result.get("ok"):
                    if print_result.get("mode") == "console":
                        set_dialog_main_status_max(
                            dlg,
                            "Hold failed. Receipt printed to console.",
                            level='error',
                            duration=6000,
                        )
                    else:
                        set_dialog_main_status_max(
                            dlg,
                            "Hold failed. Receipt printed.",
                            level='error',
                            duration=6000,
                        )
                    cleared = True
                else:
                    set_dialog_main_status_max(
                        dlg,
                        "Hold failed. Receipt print failed.",
                        level='error',
                        duration=6000,
                    )

                # After successful snapshot print/console fallback, clear UI to avoid duplicate state
                if cleared and parent is not None:
                    if hasattr(parent, "_clear_sales_table_core"):
                        parent._clear_sales_table_core()
                    panel = getattr(parent, 'payment_panel_controller', None)
                    if panel is not None:
                        panel.clear_payment_frame()

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

    ok_btn.setFocus(Qt.OtherFocusReason)

    return dlg
