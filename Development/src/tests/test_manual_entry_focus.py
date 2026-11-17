from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QComboBox, QLineEdit, QMainWindow, QPushButton, QTableWidget

from modules.db_operation import product_cache
from modules.sales.manual_entry import launch_manual_entry_dialog


_APP = None


def ensure_app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication([])
    return _APP


def _open_manual_entry_with_products(products):
    app = ensure_app()
    product_cache.PRODUCT_CACHE.clear()
    product_cache.PRODUCT_CACHE.update(products)

    parent = QMainWindow()
    parent.sales_table = QTableWidget()
    dlg = launch_manual_entry_dialog(parent)
    dlg.show()
    app.processEvents()
    return app, parent, dlg


def test_manual_entry_locked_quantity_starts_empty():
    app, parent, dlg = _open_manual_entry_with_products({})

    qty = dlg.findChild(QLineEdit, "manualQuantityLineEdit")

    assert not qty.isEnabled()
    assert qty.text() == ""

    dlg.close()
    parent.close()


def test_manual_entry_each_product_name_enter_defaults_quantity_and_focuses_ok():
    app, parent, dlg = _open_manual_entry_with_products(
        {"EACH1": ("Each Item", 1.25, "Each", "Test")}
    )

    name = dlg.findChild(QLineEdit, "manualNameSearchLineEdit")
    qty = dlg.findChild(QLineEdit, "manualQuantityLineEdit")
    ok_btn = dlg.findChild(QPushButton, "btnManualOk")
    name.setFocus()
    name.setText("Each Item")
    app.processEvents()

    QTest.keyClick(name, Qt.Key_Return)
    app.processEvents()

    assert dlg.isVisible()
    assert qty.isEnabled()
    assert not qty.isReadOnly()
    assert qty.text() == "1"
    assert ok_btn.hasFocus()

    dlg.close()
    parent.close()


def test_manual_entry_kg_product_name_enter_focuses_unit_without_unlocking_quantity():
    app, parent, dlg = _open_manual_entry_with_products(
        {"KG1": ("Kg Item", 2.50, "Kg", "Test")}
    )

    name = dlg.findChild(QLineEdit, "manualNameSearchLineEdit")
    qty = dlg.findChild(QLineEdit, "manualQuantityLineEdit")
    unit = dlg.findChild(QComboBox, "manualUnitComboBox")
    name.setFocus()
    name.setText("Kg Item")
    app.processEvents()

    QTest.keyClick(name, Qt.Key_Return)
    app.processEvents()

    assert dlg.isVisible()
    assert unit.hasFocus()
    assert unit.isEnabled()
    assert not qty.isEnabled()

    dlg.close()
    parent.close()


def test_manual_entry_kg_unit_selection_unlocks_and_focuses_quantity():
    app, parent, dlg = _open_manual_entry_with_products(
        {"KG1": ("Kg Item", 2.50, "Kg", "Test")}
    )

    name = dlg.findChild(QLineEdit, "manualNameSearchLineEdit")
    qty = dlg.findChild(QLineEdit, "manualQuantityLineEdit")
    unit = dlg.findChild(QComboBox, "manualUnitComboBox")
    name.setFocus()
    name.setText("Kg Item")
    QTest.keyClick(name, Qt.Key_Return)
    app.processEvents()

    unit.setCurrentText("KG")
    app.processEvents()

    assert qty.isEnabled()
    assert not qty.isReadOnly()
    assert qty.hasFocus()

    dlg.close()
    parent.close()


def test_manual_entry_quantity_enter_focuses_ok_and_click_accepts():
    app, parent, dlg = _open_manual_entry_with_products(
        {"EACH1": ("Each Item", 1.25, "Each", "Test")}
    )

    name = dlg.findChild(QLineEdit, "manualNameSearchLineEdit")
    qty = dlg.findChild(QLineEdit, "manualQuantityLineEdit")
    ok_btn = dlg.findChild(QPushButton, "btnManualOk")
    name.setFocus()
    name.setText("Each Item")
    QTest.keyClick(name, Qt.Key_Return)
    app.processEvents()

    qty.setText("2")
    QTest.keyClick(qty, Qt.Key_Return)
    app.processEvents()

    assert ok_btn.hasFocus()
    ok_btn.click()
    app.processEvents()

    assert dlg.result() == dlg.Accepted
    assert dlg.manual_entry_result["quantity"] == 2
    assert dlg.manual_entry_result["unit"] == "Each"

    parent.close()


def test_manual_entry_each_runtime_price_enter_skips_quantity_and_accepts_default_one():
    app, parent, dlg = _open_manual_entry_with_products(
        {"EACH1": ("Each Item", 0.10, "Each", "Test")}
    )

    name = dlg.findChild(QLineEdit, "manualNameSearchLineEdit")
    qty = dlg.findChild(QLineEdit, "manualQuantityLineEdit")
    price = dlg.findChild(QLineEdit, "manualPriceLineEdit")
    ok_btn = dlg.findChild(QPushButton, "btnManualOk")
    name.setFocus()
    name.setText("Each Item")
    QTest.keyClick(name, Qt.Key_Return)
    app.processEvents()

    assert price.hasFocus()
    assert qty.text() == "1"

    price.setText("2.75")
    QTest.keyClick(price, Qt.Key_Return)
    app.processEvents()

    assert ok_btn.hasFocus()
    ok_btn.click()
    app.processEvents()

    assert dlg.result() == dlg.Accepted
    assert dlg.manual_entry_result["quantity"] == 1
    assert dlg.manual_entry_result["unit_price"] == 2.75

    parent.close()
