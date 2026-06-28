import json
import os
import sys

import pytest
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QComboBox, QLabel, QLineEdit, QPushButton

# Ensure project package is on path when running directly.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.menu import product_menu
from modules.menu.product_menu import launch_product_dialog
from modules.ui_utils import category_state


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture()
def temp_category_json(tmp_path, monkeypatch):
    path = tmp_path / "categories.json"
    monkeypatch.setattr(category_state, "CATEGORIES_JSON_PATH", str(path))
    monkeypatch.setattr(category_state, "CATEGORIES_JSON_BACKUP_PREFIX", "categories.json.bak.")
    monkeypatch.setattr(category_state, "PROTECTED_CATEGORIES", ["Other", "--Select Category--"])
    monkeypatch.setattr(
        category_state,
        "PRODUCT_CATEGORIES",
        ["--Select Category--", "Alpha", "Other"],
    )

    data = {
        "categories": [
            "--Select Category--",
            "Beta",
            "Other",
            "Alpha",
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
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


def test_category_combo_excludes_other_for_admin(app, temp_category_json):
    mw = _make_main(is_admin=True)
    dlg = launch_product_dialog(mw)
    combo = dlg.findChild(QComboBox, 'categorySelectComboBox')
    assert combo is not None

    items = [combo.itemText(i) for i in range(combo.count())]
    assert items[0] == "--Select Category--"
    assert "Other" not in items
    dlg.close()


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

    dlg.findChild(QPushButton, "btnAddOk").click()
    _flush_success_events(app)

    assert dlg.isVisible()
    assert dlg.result() == 0
    assert "Product 'Test Add' Added" in dlg.findChild(QLabel, "addStatusLabel").text()
    assert dlg.findChild(QLineEdit, "addProductCodeLineEdit").text() == ""
    assert dlg.findChild(QLineEdit, "addProductNameLineEdit").text() == ""
    assert dlg.findChild(QPushButton, "btnAddClose").hasFocus()
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


def test_category_add_success_stays_open_and_focuses_close(app, temp_category_json):
    mw = _make_main(is_admin=True)
    dlg = launch_product_dialog(mw)
    dlg.show()
    app.processEvents()
    tabs = dlg.findChild(QTabWidget, "tabWidget")
    tabs.setCurrentIndex(3)
    dlg.findChild(QLineEdit, "categoryAddLineEdit").setText("Gamma")

    dlg.findChild(QPushButton, "btnCategoryOk").click()
    _flush_success_events(app)

    assert dlg.isVisible()
    assert dlg.result() == 0
    assert "Category 'Gamma' added" in dlg.findChild(QLabel, "categoryStatusLabel").text()
    assert dlg.findChild(QLineEdit, "categoryAddLineEdit").text() == ""
    assert dlg.findChild(QPushButton, "btnCategoryClose").hasFocus()
    dlg.close()
