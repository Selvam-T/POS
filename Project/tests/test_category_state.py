# run with: pytest tests/test_category_state.py

import json
import os
import sys
from pathlib import Path

import pytest

# Ensure project package is on path when running directly.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.ui_utils import category_state


@pytest.fixture()
def temp_categories_path(tmp_path, monkeypatch):
    # Point category_state to a temp JSON path to avoid touching real AppData.
    path = tmp_path / "categories.json"
    monkeypatch.setattr(category_state, "CATEGORIES_JSON_PATH", str(path))
    monkeypatch.setattr(category_state, "CATEGORIES_JSON_BACKUP_PREFIX", "categories.json.bak.")
    monkeypatch.setattr(category_state, "PROTECTED_CATEGORIES", ["Other", "--Select Category--"])
    monkeypatch.setattr(
        category_state,
        "PRODUCT_CATEGORIES",
        [
            "--Select Category--",
            "Snacks",
            "Beverages",
            "Other",
        ],
    )
    return path


def _read_json(path: Path):
    # Helper to load the JSON file for assertions.
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_seed_orders_placeholder_and_other(temp_categories_path):
    # Seeding should keep placeholder first, sort middle, and keep Other last.
    cats = category_state.seed_categories_if_missing()
    assert cats[0] == "--Select Category--"
    assert cats[-1] == "Other"
    assert cats[1:-1] == ["Beverages", "Snacks"]


def test_save_orders_list(temp_categories_path):
    # Save should normalize ordering regardless of input order.
    category_state.save_categories([
        "--Select Category--",
        "Vegetables",
        "Alcohol",
        "Other",
        "Snacks",
    ])
    data = _read_json(temp_categories_path)
    assert data["categories"][0] == "--Select Category--"
    assert data["categories"][-1] == "Other"
    assert data["categories"][1:-1] == ["Alcohol", "Snacks", "Vegetables"]


def test_save_rejects_duplicates(temp_categories_path):
    # Duplicates should be rejected (case-insensitive).
    with pytest.raises(ValueError):
        category_state.save_categories([
            "--Select Category--",
            "Snacks",
            "snacks",
        ])


def test_load_reorders_existing_file(temp_categories_path):
    # Load should reorder an existing JSON file to canonical order.
    temp_categories_path.parent.mkdir(parents=True, exist_ok=True)
    temp_categories_path.write_text(
        json.dumps({"categories": ["--Select Category--", "Other", "Bread", "Alcohol"]}),
        encoding="utf-8",
    )
    cats = category_state.load_categories()
    assert cats[0] == "--Select Category--"
    assert cats[-1] == "Other"
    assert cats[1:-1] == ["Alcohol", "Bread"]


def test_add_update_delete_flow(temp_categories_path):
    # Basic CRUD flow should work and persist.
    category_state.seed_categories_if_missing()

    category_state.add_category("Bakery")
    cats = category_state.load_categories()
    assert "Bakery" in cats

    category_state.update_category("Bakery", "Bread")
    cats = category_state.load_categories()
    assert "Bakery" not in cats
    assert "Bread" in cats

    category_state.delete_category("Bread")
    cats = category_state.load_categories()
    assert "Bread" not in cats


def test_protected_names_blocked(temp_categories_path):
    # Protected names should be blocked from add/update/delete.
    category_state.seed_categories_if_missing()

    with pytest.raises(ValueError):
        category_state.add_category("Other")

    with pytest.raises(ValueError):
        category_state.update_category("Other", "Misc")

    with pytest.raises(ValueError):
        category_state.delete_category("Other")
