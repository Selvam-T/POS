import json
import os
import sys

import pytest
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QComboBox

# Ensure project package is on path when running directly.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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
