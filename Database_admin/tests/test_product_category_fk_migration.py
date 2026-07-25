from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest


ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from migration.migrate_product_category_fk import (
    ProductCategoryForeignKeyMigrationError,
    migrate_product_category_fk,
)


def _connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        """
        CREATE TABLE Category (
            category_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            is_protected INTEGER NOT NULL,
            sort_order INTEGER NOT NULL
        )
        """
    )
    conn.executemany(
        """
        INSERT INTO Category (category_id, name, is_protected, sort_order)
        VALUES (?, ?, ?, ?)
        """,
        [
            (1, "Bakery Goods", 0, 1),
            (2, "Other", 1, 2),
            (3, "Vegetable", 1, 3),
        ],
    )
    conn.execute(
        """
        CREATE TABLE Product_list (
            product_code TEXT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL,
            category TEXT,
            supplier TEXT,
            selling_price REAL NOT NULL,
            cost_price REAL,
            unit TEXT,
            last_updated TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX idx_product_code_nocase "
        "ON Product_list(product_code COLLATE NOCASE)"
    )
    return conn


def test_rebuild_maps_ids_preserves_values_and_enforces_foreign_key():
    conn = _connection()
    conn.executemany(
        """
        INSERT INTO Product_list (
            product_code, name, category, supplier,
            selling_price, cost_price, unit, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("P1", "Bread", "Bakery Goods", "Supplier", 2.5, 1.5, "Each", "t1"),
            ("P2", "Misc", "other", "", 3.0, None, "Each", "t2"),
        ],
    )
    conn.commit()

    result = migrate_product_category_fk(conn)

    assert result.products_mapped == 2
    assert result.products_rebuilt == 2
    assert [row["name"] for row in conn.execute("PRAGMA table_info('Product_list')")] == [
        "product_code",
        "name",
        "category_id",
        "supplier",
        "selling_price",
        "cost_price",
        "unit",
        "last_updated",
    ]
    assert tuple(
        conn.execute(
            """
            SELECT p.product_code, p.name, c.name, p.supplier,
                   p.selling_price, p.cost_price, p.unit, p.last_updated
              FROM Product_list AS p
              JOIN Category AS c ON c.category_id = p.category_id
             WHERE p.product_code = 'P1'
            """
        ).fetchone()
    ) == ("P1", "Bread", "Bakery Goods", "Supplier", 2.5, 1.5, "Each", "t1")
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO Product_list (
                product_code, name, category_id, selling_price
            ) VALUES ('BAD', 'Bad category', 999, 1.0)
            """
        )


def test_unknown_category_rolls_back_without_partial_column():
    conn = _connection()
    conn.execute(
        """
        INSERT INTO Product_list (product_code, name, category, selling_price)
        VALUES ('P1', 'Unknown product', 'Unknown', 1.0)
        """
    )
    conn.commit()

    with pytest.raises(
        ProductCategoryForeignKeyMigrationError,
        match="Unresolved Product_list categories",
    ):
        migrate_product_category_fk(conn)

    columns = [
        row["name"] for row in conn.execute("PRAGMA table_info('Product_list')")
    ]
    assert "category" in columns
    assert "category_id" not in columns
    assert conn.execute(
        "SELECT category FROM Product_list WHERE product_code = 'P1'"
    ).fetchone()[0] == "Unknown"


def test_protected_category_mismatch_stops_before_schema_change():
    conn = _connection()
    conn.execute(
        "UPDATE Category SET is_protected = 0 WHERE name = 'Vegetable'"
    )
    conn.commit()

    with pytest.raises(
        ProductCategoryForeignKeyMigrationError,
        match="protection mismatch",
    ):
        migrate_product_category_fk(conn)

    columns = [
        row["name"] for row in conn.execute("PRAGMA table_info('Product_list')")
    ]
    assert "category_id" not in columns
