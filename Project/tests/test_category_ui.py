import os
import sqlite3
import sys

import pytest
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTabWidget,
)

# Ensure project package is on path when running directly.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.menu import product_menu
from modules.menu.product_menu import launch_product_dialog
from modules.ui_utils import category_service


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture()
def temp_category_json(tmp_path, monkeypatch):
    path = tmp_path / "categories.db"
    monkeypatch.setenv("POS_DB_PATH", str(path))
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE Category (
            category_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            is_protected INTEGER NOT NULL,
            sort_order INTEGER NOT NULL
        );
        CREATE TABLE Product_list (
            product_code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category_id INTEGER NOT NULL REFERENCES Category(category_id),
            supplier TEXT,
            selling_price REAL NOT NULL,
            cost_price REAL,
            unit TEXT,
            last_updated TEXT
        );
        INSERT INTO Category(name, is_protected, sort_order)
        VALUES
          ('Zulu', 0, 1),
          ('Beta', 0, 2),
          ('Vegetable', 1, 3),
          ('Other', 1, 4),
          ('Alpha', 0, 5);
        """
    )
    conn.commit()
    conn.close()
    return path


def _make_main(is_admin: bool):
    mw = QMainWindow()
    mw.current_is_admin = bool(is_admin)
    return mw


def _flush_success_events(app):
    app.processEvents()
    app.processEvents()


def test_category_tab_disabled_for_non_admin(app, temp_category_json):
    mw = _make_main(is_admin=False)
    dlg = launch_product_dialog(mw)
    tabs = dlg.findChild(QTabWidget, 'tabWidget')
    assert tabs is not None
    assert tabs.isTabEnabled(3) is False
    dlg.close()


def test_category_combo_includes_protected_categories_for_warning(app, temp_category_json):
    mw = _make_main(is_admin=True)
    dlg = launch_product_dialog(mw)
    combo = dlg.findChild(QComboBox, 'categorySelectComboBox')
    assert combo is not None

    items = [combo.itemText(i) for i in range(combo.count())]
    assert items == [
        "--Select Category--",
        "Alpha",
        "Beta",
        "Vegetable",
        "Zulu",
        "Other",
    ]
    dlg.close()


def test_category_add_refreshes_all_product_category_combos(
    app,
    temp_category_json,
):
    mw = _make_main(is_admin=True)
    dlg = launch_product_dialog(mw)
    dlg.show()
    app.processEvents()

    add_combo = dlg.findChild(QComboBox, "addCategoryComboBox")
    update_combo = dlg.findChild(QComboBox, "updateCategoryComboBox")
    category_combo = dlg.findChild(QComboBox, "categorySelectComboBox")
    assert all(combo.findText("Test") == -1 for combo in (
        add_combo,
        update_combo,
        category_combo,
    ))

    dlg.findChild(QTabWidget, "tabWidget").setCurrentIndex(3)
    dlg.findChild(QRadioButton, "categoryAddRadioBtn").setChecked(True)
    dlg.findChild(QLineEdit, "categoryAddLineEdit").setText("test")
    app.processEvents()
    dlg.findChild(QPushButton, "btnCategoryOk").click()
    _flush_success_events(app)

    expected = [
        "--Select Category--",
        "Alpha",
        "Beta",
        "Test",
        "Vegetable",
        "Zulu",
        "Other",
    ]
    for combo in (add_combo, update_combo):
        assert [combo.itemText(i) for i in range(combo.count())] == expected

    dlg.findChild(QRadioButton, "categoryRemoveRadioBtn").setChecked(True)
    app.processEvents()
    assert [
        category_combo.itemText(i) for i in range(category_combo.count())
    ] == expected
    dlg.close()


def test_remove_protected_category_shows_warning(app, temp_category_json):
    mw = _make_main(is_admin=True)
    dlg = launch_product_dialog(mw)
    dlg.show()
    app.processEvents()
    dlg.findChild(QTabWidget, "tabWidget").setCurrentIndex(3)
    dlg.findChild(QRadioButton, "categoryRemoveRadioBtn").setChecked(True)
    app.processEvents()

    combo = dlg.findChild(QComboBox, "categorySelectComboBox")
    combo.setCurrentIndex(combo.findText("Other"))
    dlg.product_category_tab_controller._on_combo_activated(combo.currentIndex())
    app.processEvents()
    dlg.findChild(QPushButton, "btnCategoryOk").click()
    app.processEvents()

    assert "protected" in dlg.findChild(
        QLabel, "categoryStatusLabel"
    ).text().lower()
    dlg.close()


def test_duplicate_category_add_returns_focus_and_selects_input(
    app,
    temp_category_json,
):
    mw = _make_main(is_admin=True)
    dlg = launch_product_dialog(mw)
    dlg.show()
    app.processEvents()
    dlg.findChild(QTabWidget, "tabWidget").setCurrentIndex(3)

    category_input = dlg.findChild(QLineEdit, "categoryAddLineEdit")
    category_input.setText("aLPHA")
    dlg.findChild(QPushButton, "btnCategoryOk").click()
    _flush_success_events(app)

    assert "already exists" in dlg.findChild(
        QLabel, "categoryStatusLabel"
    ).text()
    assert category_input.hasFocus()
    assert category_input.selectedText() == "Alpha"
    dlg.close()


def test_existing_category_replace_is_rejected_and_returns_focus(
    app,
    temp_category_json,
):
    mw = _make_main(is_admin=True)
    dlg = launch_product_dialog(mw)
    dlg.show()
    app.processEvents()
    dlg.findChild(QTabWidget, "tabWidget").setCurrentIndex(3)
    dlg.findChild(QRadioButton, "categoryReplaceRadioBtn").setChecked(True)
    app.processEvents()

    combo = dlg.findChild(QComboBox, "categorySelectComboBox")
    combo.setCurrentIndex(combo.findText("Alpha"))
    dlg.product_category_tab_controller._on_combo_activated(combo.currentIndex())
    replacement_input = dlg.findChild(QLineEdit, "categoryUpdateLineEdit")
    replacement_input.setText("bETA")
    dlg.findChild(QPushButton, "btnCategoryOk").click()
    _flush_success_events(app)

    status = dlg.findChild(QLabel, "categoryStatusLabel").text()
    assert "already exists" in status
    assert "merging is not available" in status.casefold()
    assert replacement_input.hasFocus()
    assert replacement_input.selectedText() == "Beta"
    assert "Alpha" in category_service.list_categories()
    dlg.close()


def test_active_sale_locks_product_tabs_for_button_launch(app, temp_category_json):
    mw = _make_main(is_admin=True)
    mw.sales_table = QTableWidget(1, 1)

    dlg = launch_product_dialog(mw)
    tabs = dlg.findChild(QTabWidget, "tabWidget")

    assert tabs.currentIndex() == 0
    assert [tabs.isTabEnabled(i) for i in range(4)] == [True, False, False, False]
    dlg.close()


def test_missing_scan_locks_product_tabs_when_sale_is_empty(app, temp_category_json):
    mw = _make_main(is_admin=True)
    mw.sales_table = QTableWidget(0, 1)

    dlg = launch_product_dialog(
        mw,
        initial_mode="add",
        initial_code="TESTSCAN",
        opened_from_missing_scan=True,
    )
    tabs = dlg.findChild(QTabWidget, "tabWidget")

    assert tabs.currentIndex() == 0
    assert [tabs.isTabEnabled(i) for i in range(4)] == [True, False, False, False]
    assert dlg.findChild(QLineEdit, "addProductCodeLineEdit").text() == "TESTSCAN"
    dlg.close()


def test_missing_scan_add_closes_dialog_and_inserts_product(
    app,
    temp_category_json,
    monkeypatch,
):
    mw = _make_main(is_admin=True)
    mw.sales_table = QTableWidget(0, 1)
    inserted = []
    monkeypatch.setattr(product_menu, "add_product", lambda *args, **kwargs: (True, "OK"))
    monkeypatch.setattr(product_menu.dbop, "refresh_product_cache", lambda: None)
    monkeypatch.setattr(
        product_menu,
        "handle_barcode_scanned",
        lambda table, code, status_bar: inserted.append((table, code)),
    )

    dlg = launch_product_dialog(
        mw,
        initial_code="TESTSCAN",
        opened_from_missing_scan=True,
    )
    dlg.show()
    app.processEvents()
    dlg.findChild(QLineEdit, "addProductNameLineEdit").setText("Test Scan")
    dlg.findChild(QLineEdit, "addSellingPriceLineEdit").setText("1.25")
    dlg.findChild(QLineEdit, "addCostPriceLineEdit").setText("0.50")
    dlg.findChild(QLineEdit, "addSupplierLineEdit").setText("Supplier")
    dlg.findChild(QComboBox, "addCategoryComboBox").setCurrentIndex(1)

    dlg.findChild(QPushButton, "btnAddOk").click()
    QTest.qWait(20)

    assert inserted == [(mw.sales_table, "TESTSCAN")]
    assert dlg.result() == QDialog.Accepted
    assert not dlg.isVisible()


def test_product_add_success_stays_open_and_focuses_close(app, temp_category_json, monkeypatch):
    mw = _make_main(is_admin=True)
    monkeypatch.setattr(product_menu, "add_product", lambda *args, **kwargs: (True, "OK"))
    monkeypatch.setattr(product_menu.dbop, "refresh_product_cache", lambda: None)

    dlg = launch_product_dialog(mw)
    dlg.show()
    app.processEvents()
    dlg.findChild(QLineEdit, "addProductCodeLineEdit").setText("TESTADD")
    dlg.findChild(QLineEdit, "addProductNameLineEdit").setText("Test Add")
    dlg.findChild(QLineEdit, "addSellingPriceLineEdit").setText("1.25")
    dlg.findChild(QLineEdit, "addCostPriceLineEdit").setText("0.50")
    dlg.findChild(QLineEdit, "addSupplierLineEdit").setText("Supplier")
    dlg.findChild(QComboBox, "addCategoryComboBox").setCurrentIndex(1)

    dlg.findChild(QPushButton, "btnAddOk").click()
    _flush_success_events(app)

    assert dlg.isVisible()
    assert dlg.result() == 0
    assert "Product 'Test Add' Added" in dlg.findChild(QLabel, "addStatusLabel").text()
    assert dlg.findChild(QLineEdit, "addProductCodeLineEdit").text() == ""
    assert dlg.findChild(QLineEdit, "addProductNameLineEdit").text() == ""
    assert dlg.findChild(QPushButton, "btnAddClose").hasFocus()
    dlg.close()


def test_product_add_requires_category_selection(
    app,
    temp_category_json,
    monkeypatch,
):
    mw = _make_main(is_admin=True)
    saved = []
    monkeypatch.setattr(
        product_menu,
        "add_product",
        lambda *args, **kwargs: saved.append(args) or (True, "OK"),
    )

    dlg = launch_product_dialog(mw)
    dlg.show()
    app.processEvents()
    dlg.findChild(QLineEdit, "addProductCodeLineEdit").setText("NOCAT")
    dlg.findChild(QLineEdit, "addProductNameLineEdit").setText("No Category")
    dlg.findChild(QLineEdit, "addSellingPriceLineEdit").setText("1.25")
    dlg.findChild(QLineEdit, "addCostPriceLineEdit").setText("0.50")
    dlg.findChild(QLineEdit, "addSupplierLineEdit").setText("Supplier")

    category_combo = dlg.findChild(QComboBox, "addCategoryComboBox")
    assert category_combo.currentIndex() == 0
    dlg.findChild(QPushButton, "btnAddOk").click()
    app.processEvents()

    assert saved == []
    assert dlg.findChild(QLabel, "addStatusLabel").text() == "Select a category"
    assert category_combo.hasFocus()
    dlg.close()


def test_product_remove_success_stays_open_and_focuses_close(app, temp_category_json, monkeypatch):
    mw = _make_main(is_admin=True)
    monkeypatch.setattr(
        product_menu,
        "get_product_full",
        lambda code: (
            True,
            {
                "product_code": code,
                "name": "Test Remove",
                "category": "",
                "cost": 0.50,
                "price": 1.25,
                "unit": "Each",
                "supplier": "Supplier",
                "last_updated": "",
            },
        ),
    )
    monkeypatch.setattr(product_menu, "delete_product", lambda code: (True, "OK"))
    monkeypatch.setattr(product_menu.dbop, "refresh_product_cache", lambda: None)

    dlg = launch_product_dialog(mw)
    dlg.show()
    app.processEvents()
    tabs = dlg.findChild(QTabWidget, "tabWidget")
    tabs.setCurrentIndex(1)
    code = dlg.findChild(QLineEdit, "removeProductCodeLineEdit")
    code.setText("TESTREM")
    code.editingFinished.emit()
    app.processEvents()
    dlg.findChild(QPushButton, "btnRemoveOk").setEnabled(True)

    dlg.findChild(QPushButton, "btnRemoveOk").click()
    _flush_success_events(app)

    assert dlg.isVisible()
    assert dlg.result() == 0
    assert "Product 'Test Remove' Deleted" in dlg.findChild(QLabel, "removeStatusLabel").text()
    assert dlg.findChild(QLineEdit, "removeProductCodeLineEdit").text() == ""
    assert dlg.findChild(QLineEdit, "removeNameSearchLineEdit").text() == ""
    assert dlg.findChild(QPushButton, "btnRemoveClose").hasFocus()
    dlg.close()


def test_product_update_noop_stays_open_and_focuses_close(app, temp_category_json):
    mw = _make_main(is_admin=True)
    product = {
        "product_code": "TESTUPD",
        "name": "Test Update",
        "category": "",
        "category_id": 1,
        "cost": 0.50,
        "price": 1.25,
        "unit": "Each",
        "supplier": "Supplier",
        "last_updated": "",
    }
    from modules.menu import product_menu as product_menu_module
    original_get_product_full = product_menu_module.get_product_full
    product_menu_module.get_product_full = lambda code: (True, dict(product))
    dlg = launch_product_dialog(mw)
    try:
        dlg.show()
        app.processEvents()
        tabs = dlg.findChild(QTabWidget, "tabWidget")
        tabs.setCurrentIndex(2)

        code = dlg.findChild(QLineEdit, "updateProductCodeLineEdit")
        code.setText("TESTUPD")
        code.editingFinished.emit()
        app.processEvents()
        dlg.findChild(QPushButton, "btnUpdateOk").setEnabled(True)

        dlg.findChild(QPushButton, "btnUpdateOk").click()
        _flush_success_events(app)

        assert dlg.isVisible()
        assert dlg.result() == 0
        assert "No changes to update." in dlg.findChild(QLabel, "updateStatusLabel").text()
        assert dlg.findChild(QLineEdit, "updateProductCodeLineEdit").text() == ""
        assert dlg.findChild(QLineEdit, "updateProductNameLineEdit").text() == ""
        assert dlg.findChild(QPushButton, "btnUpdateClose").hasFocus()
    finally:
        product_menu_module.get_product_full = original_get_product_full
        dlg.close()


def test_product_update_requires_category_selection(
    app,
    temp_category_json,
    monkeypatch,
):
    mw = _make_main(is_admin=True)
    product = {
        "product_code": "TESTUPD",
        "name": "Test Update",
        "category": "Alpha",
        "category_id": 1,
        "cost": 0.50,
        "price": 1.25,
        "unit": "Each",
        "supplier": "Supplier",
        "last_updated": "",
    }
    saved = []
    monkeypatch.setattr(
        product_menu,
        "get_product_full",
        lambda code: (True, dict(product)),
    )
    monkeypatch.setattr(
        product_menu,
        "update_product",
        lambda *args, **kwargs: saved.append(args) or (True, "OK"),
    )

    dlg = launch_product_dialog(mw)
    dlg.show()
    app.processEvents()
    dlg.findChild(QTabWidget, "tabWidget").setCurrentIndex(2)
    code = dlg.findChild(QLineEdit, "updateProductCodeLineEdit")
    code.setText("TESTUPD")
    code.editingFinished.emit()
    app.processEvents()

    category_combo = dlg.findChild(QComboBox, "updateCategoryComboBox")
    category_combo.setCurrentIndex(0)
    dlg.findChild(QPushButton, "btnUpdateOk").setEnabled(True)
    dlg.findChild(QPushButton, "btnUpdateOk").click()
    app.processEvents()

    assert saved == []
    assert dlg.findChild(QLabel, "updateStatusLabel").text() == "Select a category"
    assert category_combo.hasFocus()
    dlg.close()
def test_category_add_success_stays_open_and_focuses_close(app, temp_category_json):
    mw = _make_main(is_admin=True)
    dlg = launch_product_dialog(mw)
    dlg.show()
    app.processEvents()
    tabs = dlg.findChild(QTabWidget, "tabWidget")
    tabs.setCurrentIndex(3)
    dlg.findChild(QLineEdit, "categoryAddLineEdit").setText("gAMMA_category")

    dlg.findChild(QPushButton, "btnCategoryOk").click()
    _flush_success_events(app)

    assert dlg.isVisible()
    assert dlg.result() == 0
    assert "Category 'Gamma Category' added" in dlg.findChild(
        QLabel, "categoryStatusLabel"
    ).text()
    conn = sqlite3.connect(temp_category_json)
    try:
        assert conn.execute(
            "SELECT name FROM Category WHERE name = ? COLLATE NOCASE",
            ("Gamma Category",),
        ).fetchone() == ("Gamma Category",)
    finally:
        conn.close()
    assert dlg.findChild(QLineEdit, "categoryAddLineEdit").text() == ""
    assert dlg.findChild(QPushButton, "btnCategoryClose").hasFocus()
    dlg.close()


def test_category_replace_normalizes_name(app, temp_category_json):
    mw = _make_main(is_admin=True)
    dlg = launch_product_dialog(mw)
    dlg.show()
    app.processEvents()
    dlg.findChild(QTabWidget, "tabWidget").setCurrentIndex(3)
    dlg.findChild(QRadioButton, "categoryReplaceRadioBtn").setChecked(True)
    app.processEvents()

    combo = dlg.findChild(QComboBox, "categorySelectComboBox")
    combo.setCurrentIndex(combo.findText("Alpha"))
    dlg.product_category_tab_controller._on_combo_activated(combo.currentIndex())
    dlg.findChild(QLineEdit, "categoryUpdateLineEdit").setText("fRESH_food")
    dlg.findChild(QPushButton, "btnCategoryOk").click()
    _flush_success_events(app)

    conn = sqlite3.connect(temp_category_json)
    try:
        assert conn.execute(
            "SELECT name FROM Category WHERE name = ? COLLATE NOCASE",
            ("Fresh Food",),
        ).fetchone() == ("Fresh Food",)
    finally:
        conn.close()
    dlg.close()
