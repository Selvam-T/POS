from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from modules.customer_display.customer_display import CustomerDisplayWindow


def test_customer_display_item_and_total_currency_format():
    app = QApplication.instance() or QApplication([])
    display = CustomerDisplayWindow()

    display.set_items([
        {
            "quantity": 1,
            "unit": "Each",
            "description": "Item",
            "amount": 1234.5,
        }
    ])
    display.set_total(1234.5)

    amount_item = display._table.item(0, 2)
    assert amount_item.text() == "$ 1,234.50"
    assert amount_item.data(Qt.UserRole) == 1234.5
    assert display._total_label.text() == "$ 1,234.50"
    assert display._total_label.property("numeric_value") == 1234.5
    assert display._total_title_label.text() == "Total Payable :"

    display.set_total(1234.5, rounding_applied=True)
    assert display._total_title_label.text() == "Total Payable (round) :"

    display.close()


def test_customer_display_payment_result_total_currency_format():
    app = QApplication.instance() or QApplication([])
    display = CustomerDisplayWindow()

    display.show_payment_result(total=1234.5, greeting="Thank you")

    assert display._payment_result_total.text() == "$ 1,234.50"
    assert display._payment_result_total.property("numeric_value") == 1234.5
    assert not display._payment_result_total.isHidden()

    display.close()
