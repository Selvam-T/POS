"""Recovery receipt printing for failed payment DB commits."""

from modules.devices import print_helper
from modules.payment import receipt_generator
from modules.ui_utils.dialog_utils import report_to_statusbar
from modules.ui_utils.error_logger import log_error_message
from config import MAIN_STATUS_DURATION_MS, MAIN_STATUS_ERROR_DURATION_MS


def print_payment_failure_receipt(main_window, payment_split: dict) -> None:
    """Print a temporary receipt from current UI state after DB commit failures."""
    if main_window is None:
        return
    if not bool(getattr(main_window, '_payment_failure_lock_active', False)):
        return

    try:
        sales_items = main_window._build_sale_items_snapshot()
        if not sales_items:
            report_to_statusbar(main_window, "No Receipt to be printed.", is_error=True, duration=MAIN_STATUS_ERROR_DURATION_MS)
            return

        payments = []
        for ptype, amount, tendered in main_window._build_payment_rows(payment_split):
            payments.append({
                'payment_type': ptype,
                'amount': amount,
                'tendered': tendered,
            })

        receipt_text = receipt_generator.generate_receipt_text_from_snapshot(
            items=sales_items,
            payments=payments,
            receipt_no="TEMP-DB-FAIL",
            status="PAID",
            cashier_name=str(getattr(main_window, 'current_username', '') or ''),
            payable_total=float(payment_split.get('total', 0.0) or 0.0),
        )
        print_result = print_helper.print_receipt_with_fallback(
            receipt_text,
            blocking=True,
            context="Payment failure recovery",
        )
        if print_result.get("ok"):
            report_to_statusbar(
                main_window,
                "Temporary receipt printed.",
                is_error=False,
                duration=MAIN_STATUS_DURATION_MS,
            )
        else:
            report_to_statusbar(
                main_window,
                "Temporary receipt print failed.",
                is_error=True,
                duration=MAIN_STATUS_ERROR_DURATION_MS,
            )
    except Exception as exc:
        log_error_message(f"Payment failure receipt print failed: {exc}")
        report_to_statusbar(
            main_window,
            "Receipt print failed.",
            is_error=True,
            duration=MAIN_STATUS_ERROR_DURATION_MS,
        )
