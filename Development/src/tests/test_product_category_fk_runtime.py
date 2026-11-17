import sqlite3

import pytest

from modules.db_operation import (
    PRODUCT_CACHE,
    add_product,
    get_product_full,
    update_product,
)
from modules.db_operation import products_repo


@pytest.fixture()
def product_db(tmp_path, monkeypatch):
    path = tmp_path / "products.db"
    monkeypatch.setenv("POS_DB_PATH", str(path))
    conn = sqlite3.connect(path)
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
                ON UPDATE RESTRICT ON DELETE RESTRICT,
            supplier TEXT,
            selling_price REAL NOT NULL,
            cost_price REAL,
            unit TEXT,
            last_updated TEXT
        );
        INSERT INTO Category(category_id, name, is_protected, sort_order)
        VALUES (1, 'Alpha', 0, 1), (2, 'Other', 1, 2);
        """
    )
    conn.commit()
    conn.close()
    PRODUCT_CACHE.clear()
    yield path
    PRODUCT_CACHE.clear()


def test_facade_add_and_update_use_category_ids_and_expose_names(product_db):
    ok, message = add_product(
        "P1",
        "Test Product",
        2.5,
        1,
        "Supplier",
        1.0,
        "Each",
    )
    assert (ok, message) == (True, "OK")

    found, product = get_product_full("P1")
    assert found
    assert product["category_id"] == 1
    assert product["category"] == "Alpha"
    assert PRODUCT_CACHE["P1"][3] == "Alpha"

    ok, message = update_product(
        "P1",
        "Test Product",
        2.5,
        2,
        "Supplier",
        1.0,
        "Each",
    )
    assert (ok, message) == (True, "OK")
    assert get_product_full("P1")[1]["category"] == "Other"
    assert PRODUCT_CACHE["P1"][3] == "Other"


def test_repository_rejects_unknown_category_id(product_db):
    with pytest.raises(sqlite3.IntegrityError):
        products_repo.add_product(
            product_code="BAD",
            name="Invalid Category",
            category_id=999,
            selling_price=1.0,
        )
