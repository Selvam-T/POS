from PyQt5.QtCore import Qt
import xml.etree.ElementTree as ET

from PyQt5.QtWidgets import QApplication, QTableWidget

from modules.table_ui.receipt_table_helpers import (
    SORT_ROLE,
    configure_receipt_table,
    fill_receipt_table,
)


def test_receipt_amount_uses_shared_currency_format_and_numeric_sort_role():
    app = QApplication.instance() or QApplication([])
    table = QTableWidget()

    configure_receipt_table(table, status="UNPAID")
    fill_receipt_table(
        table,
        [
            {
                "receipt_no": "R001",
                "status": "UNPAID",
                "created_at": "",
                "amount": 1234.5,
            },
        ],
        status="UNPAID",
    )

    amount_item = table.item(0, 4)

    assert amount_item.text() == "$ 1,234.50"
    assert amount_item.toolTip() == "$ 1,234.50"
    assert amount_item.data(SORT_ROLE) == 1234.5
    assert amount_item.data(Qt.UserRole)["receipt_no"] == "R001"

    table.close()


def test_receipt_menu_uses_close_action_button():
    root = ET.parse("ui/receipt_menu.ui").getroot()
    buttons = {
        widget.attrib.get("name"): widget
        for widget in root.iter("widget")
        if widget.attrib.get("class") == "QPushButton"
    }

    assert "btnReceiptClose" in buttons
    assert "btnReceiptCancel" not in buttons
    close_text = buttons["btnReceiptClose"].find("./property[@name='text']/string")
    assert close_text is not None
    assert close_text.text == "CLOSE"
