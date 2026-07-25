from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest


ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from migration.migrate_categories_to_table import (
    CategoryMigrationError,
    apply_steps_6_and_7,
    run_preflight,
    validate_category_csv,
)
from tables.create_category_table import create_category_table
from tables.create_product_list_table import create_product_list_table


def _write_csv(path: Path, rows: list[str]) -> Path:
    path.write_text("category\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def _connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        """
        CREATE TABLE Product_list (
            product_code TEXT PRIMARY KEY,
            category TEXT
        )
        """
    )
    return conn


def test_csv_validation_uses_migration_rules(tmp_path):
    csv_path = _write_csv(
        tmp_path / "categories.csv",
        ["Bakery Goods", "Other", "Vegetable"],
    )

    assert validate_category_csv(csv_path) == [
        "Bakery Goods",
        "Other",
        "Vegetable",
    ]


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        (["Other", "", "Vegetable"], "blank category is not allowed"),
        (["Other", "other", "Vegetable"], "duplicate category"),
        (
            ["--Select Category--", "Other", "Vegetable"],
            "must not be in the category CSV",
        ),
        (["Bakery Goods", "Vegetable"], "missing: 'Other'"),
        (["Bakery Goods", "Other"], "missing: 'Vegetable'"),
    ],
)
def test_csv_validation_rejects_invalid_migration_data(tmp_path, rows, message):
    csv_path = _write_csv(tmp_path / "categories.csv", rows)

    with pytest.raises(CategoryMigrationError, match=message):
        validate_category_csv(csv_path)


def test_unknown_product_category_stops_before_writes(tmp_path):
    csv_path = _write_csv(
        tmp_path / "categories.csv",
        ["Bakery Goods", "Other", "Vegetable"],
    )
    conn = _connection()
    conn.execute(
        "INSERT INTO Product_list (product_code, category) VALUES (?, ?)",
        ("P1", "Unknown"),
    )
    conn.commit()

    with pytest.raises(CategoryMigrationError, match="absent from"):
        run_preflight(conn, csv_path)

    assert conn.execute(
        "SELECT 1 FROM sqlite_master WHERE name = 'Category'"
    ).fetchone() is None
    assert conn.execute(
        "SELECT category FROM Product_list WHERE product_code = 'P1'"
    ).fetchone()[0] == "Unknown"


def test_steps_6_and_7_are_applied_together(tmp_path):
    csv_path = _write_csv(
        tmp_path / "categories.csv",
        ["Bakery Goods", "Other", "Vegetable"],
    )
    conn = _connection()
    conn.executemany(
        "INSERT INTO Product_list (product_code, category) VALUES (?, ?)",
        [("P1", ""), ("P2", None), ("P3", "Bakery Goods")],
    )
    conn.commit()

    names, audit = run_preflight(conn, csv_path)
    assert audit.product_count == 3
    assert audit.blank_or_null_count == 2

    assert apply_steps_6_and_7(conn, names) == 2
    assert conn.execute(
        "SELECT COUNT(*) FROM Product_list WHERE category = 'Other'"
    ).fetchone()[0] == 2
    rows = conn.execute(
        "SELECT name, is_protected, sort_order FROM Category ORDER BY sort_order"
    ).fetchall()
    assert [tuple(row) for row in rows] == [
        ("Bakery Goods", 0, 1),
        ("Other", 1, 2),
        ("Vegetable", 1, 3),
    ]


def test_existing_category_table_prevents_product_changes():
    conn = _connection()
    conn.execute(
        "INSERT INTO Product_list (product_code, category) VALUES (?, ?)",
        ("P1", ""),
    )
    conn.execute("CREATE TABLE Category (category_id INTEGER PRIMARY KEY)")
    conn.commit()

    with pytest.raises(CategoryMigrationError, match="already exists"):
        apply_steps_6_and_7(conn, ["Other", "Vegetable"])

    assert conn.execute(
        "SELECT category FROM Product_list WHERE product_code = 'P1'"
    ).fetchone()[0] == ""


def test_fresh_schema_creators_build_category_foreign_key(tmp_path):
    db_path = tmp_path / "fresh.db"
    sqlite3.connect(db_path).close()
    csv_path = _write_csv(
        tmp_path / "categories.csv",
        ["Bakery Goods", "Other", "Vegetable"],
    )

    create_category_table(csv_path=csv_path, db_file=db_path)
    create_product_list_table(db_file=db_path)

    conn = sqlite3.connect(db_path)
    columns = {
        row[1]: row for row in conn.execute("PRAGMA table_info('Product_list')")
    }
    assert "category" not in columns
    assert columns["category_id"][3] == 1
    foreign_keys = conn.execute(
        "PRAGMA foreign_key_list('Product_list')"
    ).fetchall()
    assert [(row[2], row[3], row[4]) for row in foreign_keys] == [
        ("Category", "category_id", "category_id")
    ]
    assert conn.execute("SELECT COUNT(*) FROM Category").fetchone()[0] == 3
    conn.close()
