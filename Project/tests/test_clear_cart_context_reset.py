from types import SimpleNamespace
from unittest.mock import patch

from PyQt5.QtWidgets import QDialog

from main import MainLoader


def test_clear_cart_resets_context_when_payment_panel_cleanup_fails():
    dialog = QDialog()
    dialog.accept()
    window = MainLoader.__new__(MainLoader)
    window.dialog_wrapper = SimpleNamespace(_last_dialog=dialog)
    window.customer_display = None
    window.receipt_context = {
        'active_receipt_id': 42,
        'source': 'HOLD_LOADED',
        'status': 'UNPAID',
        'last_receipt_no': None,
    }
    window._payment_failure_lock_active = False
    window.payment_panel_controller = SimpleNamespace(
        clear_payment_frame=lambda: (_ for _ in ()).throw(RuntimeError('panel failed'))
    )
    window._clear_sales_table_core = lambda update_display=False: None
    window._apply_hold_loaded_sales_lock = lambda locked: None
    window._refresh_sales_label_from_context = lambda: None
    window._update_customer_display_from_sales = lambda: None

    # Keep the deliberately simulated cleanup failure out of the shared
    # production error.log used by the installed application.
    with patch('modules.ui_utils.error_logger.log_error_message') as log_error:
        MainLoader._clear_sales_table(window)

    assert window.receipt_context['active_receipt_id'] is None
    assert window.receipt_context['source'] == 'ACTIVE_SALE'
    assert window.receipt_context['status'] == 'NONE'
    log_error.assert_called_once()
