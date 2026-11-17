from unittest.mock import patch

from modules.main_window.customer_display_controller import MainCustomerDisplayController


class _Display:
    STATE_IDLE = 'idle'
    STATE_PAYMENT = 'payment'

    def __init__(self):
        self.payload = None

    def set_mode_split(self):
        pass

    def set_mode_full_idle(self):
        pass

    def show_idle(self):
        pass

    def update_transaction(self, payload):
        self.payload = payload


class _SalesTable:
    _current_total = 1.60
    _current_subtotal = 1.58


class _MainWindow:
    def __init__(self):
        self.customer_display = _Display()
        self.sales_table = _SalesTable()


def test_customer_display_uses_authoritative_rounded_sales_total():
    main_window = _MainWindow()
    rows = [{
        'product_name': 'Tomato',
        'quantity': 0.45,
        'unit_price': 3.52,
        'unit': 'Kg',
    }]

    with patch(
        'modules.main_window.customer_display_controller.get_sales_data',
        return_value=rows,
    ):
        MainCustomerDisplayController(main_window).update_from_sales()

    payload = main_window.customer_display.payload
    assert payload['items'][0]['amount'] == 0.45 * 3.52
    assert payload['total'] == 1.60
    assert payload['rounding_applied'] is True
