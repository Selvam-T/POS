import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTableWidget,
)
from PyQt5.QtGui import QValidator
from PyQt5.QtTest import QTest

from modules.sales import vegetable_entry
from modules.table_ui.table_operations import get_sales_data
from modules.ui_utils import dialog_utils


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance()
    return instance or QApplication([])


def test_vegetable_entry_uses_standard_dialog_builder_contract(app):
    parent = QMainWindow()
    sales_table = QTableWidget()

    dlg = vegetable_entry.launch_vegetable_entry_dialog(parent, sales_table)

    assert dlg is not None
    assert dlg.parent() is parent
    assert dlg.isModal() is True
    assert dlg.windowModality() == Qt.ApplicationModal
    assert bool(dlg.windowFlags() & Qt.FramelessWindowHint)
    assert dlg.styleSheet()
    assert dlg._main_sales_table is sales_table
    assert dlg._coord is not None
    assert len(dlg._veg_widgets) == 21
    assert dlg._veg_widgets["table"].objectName() == "vegEntryTable"
    assert dlg._veg_widgets["veg_btn_16"].objectName() == "vegEButton16"

    dlg.close()
    parent.close()


def test_vegetable_entry_missing_required_widget_hard_fails(
    app, monkeypatch
):
    parent = QMainWindow()
    sales_table = QTableWidget()
    incomplete_dialog = QDialog(parent)

    monkeypatch.setattr(
        vegetable_entry,
        "build_dialog_from_ui",
        lambda *args, **kwargs: incomplete_dialog,
    )

    with pytest.raises(ValueError, match="vegEntryTable"):
        vegetable_entry.launch_vegetable_entry_dialog(parent, sales_table)

    incomplete_dialog.close()
    parent.close()


def test_vegetable_entry_missing_ui_uses_shared_error_fallback(
    app, monkeypatch, tmp_path
):
    parent = QMainWindow()
    sales_table = QTableWidget()
    missing_ui = tmp_path / "missing_vegetable_entry.ui"
    logged = []

    monkeypatch.setattr(vegetable_entry, "UI_PATH", str(missing_ui))
    monkeypatch.setattr(dialog_utils, "log_error_message", logged.append)

    dlg = vegetable_entry.launch_vegetable_entry_dialog(parent, sales_table)

    assert dlg is not None
    assert dlg.objectName() == "FallbackErrorDialog"
    assert dlg.parent() is parent
    assert dlg.isModal() is True
    assert bool(dlg.windowFlags() & Qt.FramelessWindowHint)
    assert len(logged) == 1
    assert "Vegetable Entry: UI not found" in logged[0]
    assert dlg.main_status_is_error is True
    assert dlg.main_status_msg == (
        "Error: Standard UI for Vegetable Entry is missing or corrupted."
    )

    close_btn = dlg.findChild(QPushButton, "errorOk")
    assert close_btn is not None
    close_btn.click()
    assert dlg.result() == QDialog.Rejected

    dlg.close()
    parent.close()


@pytest.mark.parametrize("button_key", ["cancel_btn", "close_btn"])
def test_vegetable_entry_cancel_and_close_set_info_status(
    app, button_key
):
    parent = QMainWindow()
    sales_table = QTableWidget()
    dlg = vegetable_entry.launch_vegetable_entry_dialog(parent, sales_table)

    dlg._veg_widgets[button_key].click()

    assert dlg.result() == QDialog.Rejected
    assert dlg.main_status_msg == "Vegetable entry cancelled."
    assert dlg.main_status_is_error is False
    assert dlg.main_status_duration == 4000

    dlg.close()
    parent.close()


def test_vegetable_entry_empty_ok_stays_open_with_local_feedback(app):
    parent = QMainWindow()
    sales_table = QTableWidget()
    dlg = vegetable_entry.launch_vegetable_entry_dialog(parent, sales_table)
    dlg.show()
    app.processEvents()

    dlg._veg_widgets["ok_btn"].click()
    app.processEvents()

    assert dlg.isVisible() is True
    assert dlg._veg_widgets["status"].text() == (
        "Add at least one vegetable before continuing."
    )
    assert not hasattr(dlg, "vegetable_rows")

    dlg.close()
    parent.close()


def test_vegetable_entry_invalid_row_stays_open_with_local_feedback(
    app, monkeypatch
):
    parent = QMainWindow()
    sales_table = QTableWidget()
    dlg = vegetable_entry.launch_vegetable_entry_dialog(parent, sales_table)
    dlg._veg_widgets["table"].setRowCount(1)
    monkeypatch.setattr(
        vegetable_entry,
        "get_sales_data",
        lambda table: [{
            "product_name": "Carrot",
            "quantity": 0,
            "unit_price": 2.0,
            "unit": "Each",
            "editable": True,
        }],
    )
    dlg.show()
    app.processEvents()

    dlg._veg_widgets["ok_btn"].click()
    app.processEvents()

    assert dlg.isVisible() is True
    assert "Quantity for 'Carrot' must be > 0" in dlg._veg_widgets["status"].text()
    assert not hasattr(dlg, "vegetable_rows")

    dlg.close()
    parent.close()


def test_vegetable_entry_valid_ok_sets_payload_and_info_status(
    app, monkeypatch
):
    parent = QMainWindow()
    sales_table = QTableWidget()
    dlg = vegetable_entry.launch_vegetable_entry_dialog(parent, sales_table)
    dlg._veg_widgets["table"].setRowCount(1)
    monkeypatch.setattr(
        vegetable_entry,
        "get_sales_data",
        lambda table: [{
            "product_name": "Carrot",
            "quantity": 2,
            "unit_price": 2.0,
            "unit": "Each",
            "editable": True,
        }],
    )
    monkeypatch.setattr(vegetable_entry, "PRODUCT_CACHE", {})

    dlg._veg_widgets["ok_btn"].click()

    assert dlg.result() == QDialog.Accepted
    assert dlg.vegetable_rows == [{
        "product_code": "Carrot",
        "product_name": "Carrot",
        "quantity": 2,
        "unit_price": 2.0,
        "unit": "Each",
        "editable": True,
    }]
    assert dlg.main_status_msg == "1 vegetable/s added to sale."
    assert dlg.main_status_is_error is False
    assert dlg.main_status_duration == 4000

    dlg.close()
    parent.close()


def test_vegetable_entry_invalid_weight_is_local_only(app, monkeypatch):
    parent = QMainWindow()
    sales_table = QTableWidget()
    dlg = vegetable_entry.launch_vegetable_entry_dialog(parent, sales_table)
    logged = []
    monkeypatch.setattr(vegetable_entry, "VEG_KG_MANUAL_GRAMS_FALLBACK", False)
    monkeypatch.setattr(vegetable_entry, "weight_simulation", lambda: 0)
    monkeypatch.setattr(dialog_utils, "log_error_message", logged.append)

    vegetable_entry._handle_vegetable_button_click(
        dlg,
        dlg._veg_widgets["status"],
        dlg._veg_widgets["table"],
        "VEG01",
        "Carrot",
        2.0,
        "Kg",
    )

    assert dlg._veg_widgets["status"].text() == "Error: Invalid weight"
    assert logged == []
    assert not hasattr(dlg, "main_status_msg")

    dlg.close()
    parent.close()


def test_vegetable_entry_kg_row_remains_readonly_when_manual_fallback_disabled(
    app, monkeypatch
):
    parent = QMainWindow()
    sales_table = QTableWidget()
    dlg = vegetable_entry.launch_vegetable_entry_dialog(parent, sales_table)
    monkeypatch.setattr(vegetable_entry, "VEG_KG_MANUAL_GRAMS_FALLBACK", False)
    monkeypatch.setattr(vegetable_entry, "weight_simulation", lambda: 600)

    vegetable_entry._handle_vegetable_button_click(
        dlg,
        dlg._veg_widgets["status"],
        dlg._veg_widgets["table"],
        "VEG01",
        "Carrot",
        2.0,
        "Kg",
    )

    editor = dlg._veg_widgets["table"].cellWidget(0, 2).findChild(QLineEdit, "qtyInput")
    rows = get_sales_data(dlg._veg_widgets["table"])

    assert editor.isReadOnly()
    assert editor.text() == "600"
    assert rows[0]["quantity"] == 0.6
    assert rows[0]["unit"] == "Kg"
    assert rows[0]["editable"] is False
    assert "manual_kg_grams" not in rows[0]

    dlg.close()
    parent.close()


def test_vegetable_entry_kg_manual_fallback_edits_integer_grams_and_transfers_kg(
    app, monkeypatch
):
    parent = QMainWindow()
    sales_table = QTableWidget()
    dlg = vegetable_entry.launch_vegetable_entry_dialog(parent, sales_table)
    dlg.show()
    app.processEvents()
    monkeypatch.setattr(vegetable_entry, "VEG_KG_MANUAL_GRAMS_FALLBACK", True)

    vegetable_entry._handle_vegetable_button_click(
        dlg,
        dlg._veg_widgets["status"],
        dlg._veg_widgets["table"],
        "VEG01",
        "Carrot",
        2.0,
        "Kg",
    )

    editor = dlg._veg_widgets["table"].cellWidget(0, 2).findChild(QLineEdit, "qtyInput")
    validator = editor.validator()
    app.processEvents()

    assert editor.text() == ""
    assert editor.hasFocus()
    assert not dlg._veg_widgets["ok_btn"].isEnabled()
    assert not dlg._veg_widgets["veg_btn_1"].isEnabled()
    assert dlg._veg_widgets["cancel_btn"].isEnabled()
    assert dlg._veg_widgets["close_btn"].isEnabled()
    assert get_sales_data(dlg._veg_widgets["table"])[0]["quantity"] == 0.0

    editor.setText("1500")
    app.processEvents()

    assert dlg._veg_widgets["ok_btn"].isEnabled()
    assert dlg._veg_widgets["veg_btn_1"].isEnabled()

    QTest.keyClick(editor, Qt.Key_Return)
    app.processEvents()
    rows = get_sales_data(dlg._veg_widgets["table"])

    assert not editor.isReadOnly()
    assert editor.property("manual_kg_grams") is True
    assert validator.validate("1500", 0)[0] == QValidator.Acceptable
    assert validator.validate("1.5", 0)[0] != QValidator.Acceptable
    assert dlg._veg_widgets["ok_btn"].hasFocus()
    assert rows[0]["quantity"] == 1.5
    assert rows[0]["unit"] == "Kg"
    assert rows[0]["editable"] is True
    assert rows[0]["manual_kg_grams"] is True

    dlg._veg_widgets["ok_btn"].click()

    assert dlg.result() == QDialog.Accepted
    assert dlg.vegetable_rows == [
        {
            "product_code": "Carrot",
            "product_name": "Carrot",
            "quantity": 1.5,
            "unit_price": 2.0,
            "unit": "Kg",
            "editable": True,
            "manual_kg_grams": True,
        }
    ]

    parent.close()


def test_vegetable_entry_kg_manual_fallback_delete_clears_pending_button_block(
    app, monkeypatch
):
    parent = QMainWindow()
    sales_table = QTableWidget()
    dlg = vegetable_entry.launch_vegetable_entry_dialog(parent, sales_table)
    dlg.show()
    app.processEvents()
    monkeypatch.setattr(vegetable_entry, "VEG_KG_MANUAL_GRAMS_FALLBACK", True)

    vegetable_entry._handle_vegetable_button_click(
        dlg,
        dlg._veg_widgets["status"],
        dlg._veg_widgets["table"],
        "VEG01",
        "Carrot",
        2.0,
        "Kg",
    )

    delete_btn = dlg._veg_widgets["table"].cellWidget(0, 6).findChild(QPushButton, "removeBtn")

    assert delete_btn.isEnabled()
    assert not dlg._veg_widgets["ok_btn"].isEnabled()
    assert not dlg._veg_widgets["veg_btn_1"].isEnabled()

    delete_btn.click()
    app.processEvents()

    assert dlg._veg_widgets["table"].rowCount() == 0
    assert dlg._veg_widgets["ok_btn"].isEnabled()
    assert dlg._veg_widgets["veg_btn_1"].isEnabled()

    dlg.close()
    parent.close()


def test_vegetable_entry_each_empty_qty_blocks_ok_and_veg_buttons(
    app, monkeypatch
):
    parent = QMainWindow()
    sales_table = QTableWidget()
    dlg = vegetable_entry.launch_vegetable_entry_dialog(parent, sales_table)
    dlg.show()
    app.processEvents()
    monkeypatch.setattr(vegetable_entry, "VEG_KG_MANUAL_GRAMS_FALLBACK", False)

    vegetable_entry._handle_vegetable_button_click(
        dlg,
        dlg._veg_widgets["status"],
        dlg._veg_widgets["table"],
        "VEG02",
        "Onion",
        1.5,
        "Each",
    )

    editor = dlg._veg_widgets["table"].cellWidget(0, 2).findChild(QLineEdit, "qtyInput")
    delete_btn = dlg._veg_widgets["table"].cellWidget(0, 6).findChild(QPushButton, "removeBtn")

    assert editor.text() == "1"
    assert dlg._veg_widgets["ok_btn"].isEnabled()
    assert dlg._veg_widgets["veg_btn_1"].isEnabled()

    editor.clear()
    app.processEvents()

    assert not dlg._veg_widgets["ok_btn"].isEnabled()
    assert not dlg._veg_widgets["veg_btn_1"].isEnabled()
    assert delete_btn.isEnabled()
    assert dlg._veg_widgets["cancel_btn"].isEnabled()
    assert dlg._veg_widgets["close_btn"].isEnabled()

    editor.setText("3")
    app.processEvents()

    assert dlg._veg_widgets["ok_btn"].isEnabled()
    assert dlg._veg_widgets["veg_btn_1"].isEnabled()

    dlg.close()
    parent.close()


def test_vegetable_entry_scale_exception_logs_and_sets_postclose_error(
    app, monkeypatch
):
    parent = QMainWindow()
    sales_table = QTableWidget()
    dlg = vegetable_entry.launch_vegetable_entry_dialog(parent, sales_table)
    logged = []
    monkeypatch.setattr(vegetable_entry, "VEG_KG_MANUAL_GRAMS_FALLBACK", False)

    def fail_scale():
        raise RuntimeError("scale offline")

    monkeypatch.setattr(vegetable_entry, "weight_simulation", fail_scale)
    monkeypatch.setattr(dialog_utils, "log_error_message", logged.append)

    vegetable_entry._handle_vegetable_button_click(
        dlg,
        dlg._veg_widgets["status"],
        dlg._veg_widgets["table"],
        "VEG01",
        "Carrot",
        2.0,
        "Kg",
    )

    assert dlg._veg_widgets["status"].text() == "Scale error. Unable to add Carrot."
    assert len(logged) == 1
    assert "Vegetable Entry scale (VEG01, Carrot)" in logged[0]
    assert "scale offline" in logged[0]
    assert dlg.main_status_msg == "Error: Unable to weigh Carrot"
    assert dlg.main_status_is_error is True
    assert dlg.main_status_duration == vegetable_entry.MAIN_STATUS_LONG_DURATION_MS

    dlg._veg_widgets["cancel_btn"].click()
    assert dlg.main_status_msg == "Error: Unable to weigh Carrot"
    assert dlg.main_status_is_error is True

    dlg.close()
    parent.close()


def test_vegetable_entry_table_rebuild_exception_uses_runtime_error_pipeline(
    app, monkeypatch
):
    parent = QMainWindow()
    sales_table = QTableWidget()
    dlg = vegetable_entry.launch_vegetable_entry_dialog(parent, sales_table)
    logged = []

    def fail_rebuild(table, rows, status_bar=None):
        raise RuntimeError("table rebuild failed")

    monkeypatch.setattr(vegetable_entry, "set_table_rows", fail_rebuild)
    monkeypatch.setattr(dialog_utils, "log_error_message", logged.append)

    vegetable_entry._handle_vegetable_button_click(
        dlg,
        dlg._veg_widgets["status"],
        dlg._veg_widgets["table"],
        "VEG02",
        "Onion",
        1.5,
        "Each",
    )

    assert dlg._veg_widgets["status"].text() == (
        "Unable to add Onion to the vegetable table."
    )
    assert len(logged) == 1
    assert "Vegetable Entry staging table (VEG02, Onion)" in logged[0]
    assert "table rebuild failed" in logged[0]
    assert dlg.main_status_msg == "Error: Vegetable table update failed"
    assert dlg.main_status_is_error is True

    dlg.close()
    parent.close()


def test_vegetable_entry_result_exception_uses_runtime_error_pipeline(
    app, monkeypatch
):
    parent = QMainWindow()
    sales_table = QTableWidget()
    dlg = vegetable_entry.launch_vegetable_entry_dialog(parent, sales_table)
    dlg._veg_widgets["table"].setRowCount(1)
    logged = []

    def fail_scrape(table):
        raise RuntimeError("scrape failed")

    monkeypatch.setattr(vegetable_entry, "get_sales_data", fail_scrape)
    monkeypatch.setattr(dialog_utils, "log_error_message", logged.append)

    dlg._veg_widgets["ok_btn"].click()

    assert dlg._veg_widgets["status"].text() == "Unable to prepare vegetable items."
    assert len(logged) == 1
    assert "Vegetable Entry prepare result" in logged[0]
    assert "scrape failed" in logged[0]
    assert dlg.main_status_msg == "Error: Unable to prepare vegetable items"
    assert dlg.main_status_is_error is True

    dlg.close()
    parent.close()


def test_vegetable_entry_row_limit_remains_handled_without_error_logging(
    app, monkeypatch
):
    from config import MAX_TABLE_ROWS
    from modules.ui_utils import max_rows_dialog

    parent = QMainWindow()
    sales_table = QTableWidget()
    dlg = vegetable_entry.launch_vegetable_entry_dialog(parent, sales_table)
    sales_table.setRowCount(MAX_TABLE_ROWS - 1)
    dlg._veg_widgets["table"].setRowCount(1)
    logged = []
    guard_calls = []

    class GuardDialog:
        def exec_(self):
            guard_calls.append(True)

    monkeypatch.setattr(
        vegetable_entry,
        "get_sales_data",
        lambda table: [{
            "product_name": "Carrot",
            "quantity": 1,
            "unit_price": 2.0,
            "unit": "Each",
            "editable": True,
        }],
    )
    monkeypatch.setattr(
        max_rows_dialog,
        "open_max_rows_dialog",
        lambda *args, **kwargs: GuardDialog(),
    )
    monkeypatch.setattr(dialog_utils, "log_error_message", logged.append)

    vegetable_entry._handle_vegetable_button_click(
        dlg,
        dlg._veg_widgets["status"],
        dlg._veg_widgets["table"],
        "VEG02",
        "Onion",
        1.5,
        "Each",
    )

    assert guard_calls == [True]
    assert logged == []
    assert not hasattr(dlg, "main_status_msg")

    dlg.close()
    parent.close()


def test_vegetable_entry_uses_cached_unit_without_full_product_sql_lookup(
    app, monkeypatch
):
    from modules.db_operation import products_repo

    parent = QMainWindow()
    sales_table = QTableWidget()
    lookup_codes = []
    selections = []

    def cached_lookup(code):
        lookup_codes.append(code)
        if code == "VEG01":
            return True, "Carrot", 2.0, "Kg"
        return False, code, 0.0, "Each"

    def fail_full_lookup(*args, **kwargs):
        raise RuntimeError("full SQL lookup must not be used")

    monkeypatch.setattr(vegetable_entry, "get_product_info", cached_lookup)
    monkeypatch.setattr(products_repo, "get_product_full", fail_full_lookup)
    monkeypatch.setattr(
        vegetable_entry,
        "_handle_vegetable_button_click",
        lambda *args: selections.append(args),
    )

    dlg = vegetable_entry.launch_vegetable_entry_dialog(parent, sales_table)
    dlg._veg_widgets["veg_btn_1"].click()

    assert dlg is not None
    assert lookup_codes == [f"VEG{i:02d}" for i in range(1, 17)]
    assert dlg._veg_widgets["veg_btn_1"].text() == "Carrot"
    assert len(selections) == 1
    assert selections[0][-2] == "Kg"
    assert selections[0][-1] is False

    dlg.close()
    parent.close()
