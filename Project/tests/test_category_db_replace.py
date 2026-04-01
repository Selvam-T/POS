import os
import sqlite3
import sys

import pytest

# Ensure project package is on path when running directly.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.ui_utils import category_service, category_state


@pytest.fixture()
def temp_db_and_json(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("POS_DB_PATH", str(db_path))

    monkeypatch.setattr(category_state, "CATEGORIES_JSON_PATH", str(tmp_path / "categories.json"))
    monkeypatch.setattr(category_state, "CATEGORIES_JSON_BACKUP_PREFIX", "categories.json.bak.")
    monkeypatch.setattr(category_state, "PROTECTED_CATEGORIES", ["Other", "--Select Category--"])
    monkeypatch.setattr(category_state, "PRODUCT_CATEGORIES", ["--Select Category--", "Other"])

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE Product_list (
                product_code TEXT,
                name TEXT,
                category TEXT,
                supplier TEXT,
                selling_price REAL,
                cost_price REAL,
                unit TEXT,
                last_updated TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE receipt_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    category_state.seed_categories_if_missing()
    return db_path


def _count_by_category(conn, table, category):
    row = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM {table} WHERE category = ? COLLATE NOCASE",
        (category,),
    ).fetchone()
    return int(row[0] or 0)


def test_delete_category_replaces_in_db(temp_db_and_json):
    category_state.add_category("Snacks")

    conn = sqlite3.connect(str(temp_db_and_json))
    try:
        conn.execute(
            "INSERT INTO Product_list (product_code, name, category, supplier, selling_price, cost_price, unit, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("P001", "Test", "Snacks", "", 1.0, 0.0, "EACH", "2026-01-01"),
        )
        conn.execute(
            "INSERT INTO receipt_items (category) VALUES (?)",
            ("Snacks",),
        )
        conn.commit()
    finally:
        conn.close()

    products_updated = category_service.delete_category("Snacks")
    assert products_updated == 1

    conn = sqlite3.connect(str(temp_db_and_json))
    try:
        assert _count_by_category(conn, "Product_list", "Snacks") == 0
        assert _count_by_category(conn, "receipt_items", "Snacks") == 1
        assert _count_by_category(conn, "Product_list", "Other") == 1
        assert _count_by_category(conn, "receipt_items", "Other") == 0
    finally:
        conn.close()

    cats = category_state.list_categories()
    assert "Snacks" not in cats
    assert "Other" in cats


def test_product_cache_refreshed_after_category_replace(temp_db_and_json):
    # Ensure product and category exist
    category_state.add_category("Snacks")
    conn = sqlite3.connect(str(temp_db_and_json))
    try:
        conn.execute(
            "INSERT INTO Product_list (product_code, name, category, supplier, selling_price, cost_price, unit, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("P002", "CacheTest", "Snacks", "", 2.0, 0.0, "EACH", "2026-01-01"),
        )
        conn.commit()
    finally:
        conn.close()

    # Clear in-memory cache and run the delete_category which should refresh it
    from modules.db_operation import PRODUCT_CACHE
    PRODUCT_CACHE.clear()

    products_updated = category_service.delete_category("Snacks")
    assert products_updated >= 1

    # PRODUCT_CACHE should have been refreshed and contain P002
    from modules.db_operation import PRODUCT_CACHE as PC
    assert any(k == 'P002' for k in (PC or {}).keys())
