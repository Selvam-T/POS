import config

from modules.customer_display import CustomerDisplayWindow
from modules.table_ui.table_operations import get_sales_data, get_subtotal, get_total


class MainCustomerDisplayController:
    def __init__(self, main_window):
        self.main_window = main_window

    def init_display(self) -> None:
        self.main_window.customer_display = None
        if not bool(getattr(config, 'CUSTOMER_DISPLAY_ENABLED', True)):
            return
        try:
            self.main_window.customer_display = CustomerDisplayWindow(self.main_window)
        except Exception as exc:
            try:
                from modules.ui_utils.error_logger import log_error_message
                log_error_message(f"Customer display init failed: {exc}")
            except Exception:
                pass

    def update_from_sales(self, state: str | None = None) -> None:
        display = getattr(self.main_window, 'customer_display', None)
        if display is None:
            return
        sales_table = getattr(self.main_window, 'sales_table', None)
        if sales_table is None:
            display.set_mode_full_idle()
            display.show_idle()
            return

        try:
            rows = get_sales_data(sales_table)
        except Exception:
            rows = []

        if rows:
            display.set_mode_split()
        else:
            display.set_mode_full_idle()

        items = []
        for row in rows:
            qty = float(row.get('quantity') or 0.0)
            name = str(row.get('product_name') or row.get('product') or '')
            price = float(row.get('unit_price') or 0.0)
            line_total = qty * price
            items.append({
                'quantity': qty,
                'description': name,
                'amount': line_total,
                'unit': row.get('unit') if isinstance(row, dict) else None,
            })

        # Use the payable total already calculated by the sales table. This is
        # the same rounded value emitted to the payment panel.
        total = get_total(sales_table)
        subtotal = get_subtotal(sales_table)

        # Display returns to idle if no rows and state is not payment.
        if not rows and state not in (display.STATE_PAYMENT,):
            display.show_idle()
            return

        payload = {
            # Active sales default to the payment QR page in the right frame.
            'state': state or (display.STATE_PAYMENT if rows else display.STATE_IDLE),
            'items': items,
            'total': total,
            'rounding_applied': abs(total - subtotal) >= 0.01,
        }
        display.update_transaction(payload)
