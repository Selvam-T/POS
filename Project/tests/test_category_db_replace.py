import sqlite3

import pytest

from modules.ui_utils import category_service


@pytest.fixture()
def category_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("POS_DB_PATH", str(db_path))
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE Category (
            category_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            is_protected INTEGER NOT NULL,
            sort_order INTEGER NOT NULL
        );
        CREATE TABLE Product_list (
            product_code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category_id INTEGER NOT NULL REFERENCES Category(category_id)
                ON DELETE RESTRICT ON UPDATE RESTRICT,
            supplier TEXT,
            selling_price REAL NOT NULL,
            cost_price REAL,
            unit TEXT,
            last_updated TEXT
        );
        CREATE TABLE receipt_items (
            id INTEGER PRIMARY KEY,
            category TEXT
        );
        INSERT INTO Category(name, is_protected, sort_order)
        VALUES ('Other', 1, 1), ('Vegetable', 1, 2), ('Snacks', 0, 3);
        """
    )
    conn.commit()
    conn.close()
    return db_path


def test_delete_reassigns_products_but_preserves_receipt_snapshot(category_db):
    conn = sqlite3.connect(category_db)
    snack_id = conn.execute(
        "SELECT category_id FROM Category WHERE name='Snacks'"
    ).fetchone()[0]
    conn.execute(
        """
        INSERT INTO Product_list
          (product_code, name, category_id, selling_price, unit)
        VALUES ('P001', 'Test', ?, 1.0, 'Each')
        """,
        (snack_id,),
    )
    conn.execute("INSERT INTO receipt_items(category) VALUES ('Snacks')")
    conn.commit()
    conn.close()

    assert category_service.delete_category("Snacks") == 1

    conn = sqlite3.connect(category_db)
    assert conn.execute(
        """
        SELECT c.name FROM Product_list p
        JOIN Category c ON c.category_id=p.category_id
        WHERE p.product_code='P001'
        """
    ).fetchone()[0] == "Other"
    assert conn.execute(
        "SELECT category FROM receipt_items"
    ).fetchone()[0] == "Snacks"
    assert conn.execute(
        "SELECT COUNT(*) FROM Category WHERE name='Snacks'"
    ).fetchone()[0] == 0
    conn.close()


def test_rename_keeps_product_id_and_refreshes_cache(category_db):
    conn = sqlite3.connect(category_db)
    snack_id = conn.execute(
        "SELECT category_id FROM Category WHERE name='Snacks'"
    ).fetchone()[0]
    conn.execute(
        """
        INSERT INTO Product_list
          (product_code, name, category_id, selling_price, unit)
        VALUES ('P002', 'CacheTest', ?, 2.0, 'Each')
        """,
        (snack_id,),
    )
    conn.commit()
    conn.close()

    assert category_service.update_category("Snacks", "Treats") == 0

    from modules.db_operation import PRODUCT_CACHE
    assert PRODUCT_CACHE["P002"][3] == "Treats"


@pytest.mark.parametrize("name", ["Other", "Vegetable"])
def test_protected_categories_warn_and_remain(category_db, name):
    with pytest.raises(ValueError, match="protected"):
        category_service.delete_category(name)
    with pytest.raises(ValueError, match="protected"):
        category_service.update_category(name, "Replacement")

    assert name in category_service.list_categories()


def test_replace_with_existing_category_merges(category_db):
    category_service.add_category("Treats")
    conn = sqlite3.connect(category_db)
    snack_id = conn.execute(
        "SELECT category_id FROM Category WHERE name='Snacks'"
    ).fetchone()[0]
    conn.execute(
        """
        INSERT INTO Product_list
          (product_code, name, category_id, selling_price)
        VALUES ('P003', 'MergeTest', ?, 1.0)
        """,
        (snack_id,),
    )
    conn.commit()
    conn.close()

    assert category_service.update_category("Snacks", "Treats") == 1
    assert "Snacks" not in category_service.list_categories()
