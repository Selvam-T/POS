from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QLabel, QLineEdit, QTableWidget

from modules.table_ui.table_operations import (
    bind_total_label,
    get_sales_data,
    get_subtotal,
    get_total,
    recalc_row_total,
    set_table_rows,
    setup_sales_table,
)

_APP = None


def ensure_app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication([])
    return _APP


def make_table():
    ensure_app()
    table = QTableWidget()
    setup_sales_table(table)
    return table


def test_sales_table_money_columns_use_shared_currency_format_and_numeric_values():
    table = make_table()
    total_label = QLabel()
    bind_total_label(table, total_label)

    set_table_rows(
        table,
        [
            {
                "product_name": "Test Item",
                "quantity": 2,
                "unit_price": 1234.5,
                "unit": "Each",
                "editable": True,
            }
        ],
    )

    price_item = table.item(0, 4)
    total_item = table.item(0, 5)

    assert price_item.text() == "$ 1,234.50"
    assert price_item.data(Qt.UserRole) == 1234.5
    assert total_item.text() == "$ 2,469.00"
    assert total_item.data(Qt.UserRole) == 2469.0
    assert total_label.text() == "$ 2,469.00"
    assert total_label.property("numeric_value") == 2469.0
    assert get_total(table) == 2469.0

    rows = get_sales_data(table)
    assert rows[0]["unit_price"] == 1234.5


def test_sales_table_recalc_keeps_currency_display_and_numeric_total():
    table = make_table()
    total_label = QLabel()
    bind_total_label(table, total_label)

    set_table_rows(
        table,
        [
            {
                "product_name": "Each Item",
                "quantity": 2,
                "unit_price": 2.0,
                "unit": "Each",
                "editable": True,
            }
        ],
    )

    editor = table.cellWidget(0, 2).findChild(QLineEdit, "qtyInput")
    editor.setText("3")
    recalc_row_total(table, 0)

    total_item = table.item(0, 5)
    assert total_item.text() == "$ 6.00"
    assert total_item.data(Qt.UserRole) == 6.0
    assert total_label.text() == "$ 6.00"
    assert total_label.property("numeric_value") == 6.0


def test_sales_table_total_label_uses_rounded_payable_total_only():
    table = make_table()
    total_label = QLabel()
    bind_total_label(table, total_label)

    set_table_rows(
        table,
        [
            {
                "product_name": "Rounding Item",
                "quantity": 1,
                "unit_price": 1.04,
                "unit": "Each",
                "editable": True,
            }
        ],
    )

    total_item = table.item(0, 5)
    assert total_item.text() == "$ 1.04"
    assert total_item.data(Qt.UserRole) == 1.04
    assert get_subtotal(table) == 1.04
    assert get_total(table) == 1.0
    assert total_label.text() == "$ 1.00"
    assert total_label.property("numeric_value") == 1.0
    assert total_label.property("subtotal_value") == 1.04
