from types import SimpleNamespace

from PyQt5.QtWidgets import QApplication, QDialog, QTableWidget

from main import MainLoader
from modules.table_ui.table_operations import get_sales_data, set_table_rows, setup_sales_table


_APP = None


def ensure_app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication([])
    return _APP


def test_add_items_to_sales_table_preserves_formatted_existing_unit_price():
    ensure_app()
    table = QTableWidget()
    setup_sales_table(table)
    set_table_rows(
        table,
        [
            {
                "product_name": "Existing Item",
                "quantity": 2,
                "unit_price": 1.04,
                "unit": "Each",
                "editable": True,
            }
        ],
    )

    dlg = QDialog()
    dlg.manual_entry_result = {
        "product_name": "New Item",
        "quantity": 1,
        "unit_price": 2.0,
        "unit": "Each",
    }
    dlg.accept()

    window = MainLoader.__new__(MainLoader)
    window.sales_table = table
    window.dialog_wrapper = SimpleNamespace(_last_dialog=dlg)
    window.customer_display = None
    window._mark_sales_table_unavailable = lambda *args, **kwargs: None
    window._update_customer_display_from_sales = lambda *args, **kwargs: None

    MainLoader._add_items_to_sales_table(window)

    assert table.item(0, 5).text() == "$ 2.08"
    assert table.item(1, 5).text() == "$ 2.00"
    rows = get_sales_data(table)
    assert rows[0]["unit_price"] == 1.04
    assert rows[0]["quantity"] == 2.0
