from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

import pytest

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from audit.verify_db_and_product_list import verify_database
from migration.stage_legacy_products import PRODUCT_HEADERS, stage_legacy_products
from migration.validate_legacy_products import validate_legacy_products
from products.replace_products import CONFIRMATION, replace_products
from tables.create_product_list_table import create_product_list_table


def _create_complete_database(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        for table in (
            "users",
            "cash_outflows",
            "receipts",
            "receipt_items",
            "receipt_payments",
        ):
            conn.execute(f'CREATE TABLE "{table}" (id INTEGER PRIMARY KEY)')
        conn.execute("INSERT INTO users(id) VALUES (1)")
    create_product_list_table(db_file=path)


def _write_products(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=PRODUCT_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in PRODUCT_HEADERS})


def _product(code: str, name: object, price: object = "1.00") -> dict[str, object]:
    return {
        "product_code": code,
        "name": name,
        "category": "Other",
        "supplier": "",
        "selling_price": price,
        "cost_price": "",
        "unit": "Each",
        "last_updated": "2026-07-23 00:00:00",
    }


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("MG Yoghurt", "MG Yoghurt"),
        ("MG Yoghurt", "mg yoghurt"),
        ("MG Yoghurt", "  MG   Yoghurt  "),
    ],
)
def test_validation_rejects_normalized_duplicate_names(
    tmp_path: Path, first: str, second: str
) -> None:
    csv_path = tmp_path / "products.csv"
    _write_products(csv_path, [_product("P1", first), _product("P2", second)])

    staged = stage_legacy_products(csv_path)
    with pytest.raises(ValueError, match="Product validation failed"):
        validate_legacy_products(staged, report_dir=tmp_path)

    rejected = (tmp_path / "rejected_products.csv").read_text(encoding="utf-8")
    assert "duplicate product name" in rejected


@pytest.mark.parametrize("name", ["", "   ", None])
def test_validation_rejects_blank_or_null_names(tmp_path: Path, name: object) -> None:
    csv_path = tmp_path / "products.csv"
    _write_products(csv_path, [_product("P1", name)])

    with pytest.raises(ValueError, match="Product validation failed"):
        validate_legacy_products(
            stage_legacy_products(csv_path),
            report_dir=tmp_path,
        )


def test_validation_rejects_case_insensitive_duplicate_codes(tmp_path: Path) -> None:
    csv_path = tmp_path / "products.csv"
    _write_products(
        csv_path,
        [_product("abc", "First Product"), _product("ABC", "Second Product")],
    )

    with pytest.raises(ValueError, match="Product validation failed"):
        validate_legacy_products(
            stage_legacy_products(csv_path),
            report_dir=tmp_path,
        )

    rejected = (tmp_path / "rejected_products.csv").read_text(encoding="utf-8")
    assert "duplicate product_code" in rejected


def test_schema_and_audit_require_case_insensitive_unique_names(tmp_path: Path) -> None:
    db_path = tmp_path / "complete.db"
    _create_complete_database(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO Product_list
              (product_code, name, selling_price)
            VALUES ('P1', 'MG Yoghurt', 1.0)
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO Product_list
                  (product_code, name, selling_price)
                VALUES ('P2', 'mg yoghurt', 2.0)
                """
            )

    verify_database(db_file=db_path)


def test_product_only_replacement_preserves_unrelated_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "working.db"
    csv_path = tmp_path / "products.csv"
    _create_complete_database(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO Product_list
              (product_code, name, selling_price)
            VALUES ('OLD', 'Old Product', 1.0)
            """
        )
    _write_products(
        csv_path,
        [_product("P1", "First Product"), _product("P2", "Second Product", "2.00")],
    )

    inserted = replace_products(
        db_file=db_path,
        csv_file=csv_path,
        report_dir=tmp_path / "reports",
        confirmation=CONFIRMATION,
    )

    assert inserted == 2
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM Product_list").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM Product_list WHERE product_code = 'OLD'"
        ).fetchone()[0] == 0


def test_product_replacement_rolls_back_on_insert_failure(tmp_path: Path) -> None:
    db_path = tmp_path / "working.db"
    csv_path = tmp_path / "products.csv"
    _create_complete_database(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO Product_list
              (product_code, name, selling_price)
            VALUES ('OLD', 'Old Product', 1.0)
            """
        )
        conn.execute(
            """
            CREATE TRIGGER reject_blocked_product
            BEFORE INSERT ON Product_list
            WHEN NEW.product_code = 'BLOCKED'
            BEGIN
                SELECT RAISE(ABORT, 'blocked by test trigger');
            END
            """
        )
    _write_products(csv_path, [_product("BLOCKED", "Blocked Product")])

    with pytest.raises(sqlite3.IntegrityError, match="blocked by test trigger"):
        replace_products(
            db_file=db_path,
            csv_file=csv_path,
            report_dir=tmp_path / "reports",
            confirmation=CONFIRMATION,
        )

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT product_code, name FROM Product_list"
        ).fetchall()
    assert rows == [("OLD", "Old Product")]


def test_check_only_does_not_modify_database(tmp_path: Path) -> None:
    db_path = tmp_path / "working.db"
    csv_path = tmp_path / "products.csv"
    _create_complete_database(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO Product_list
              (product_code, name, selling_price)
            VALUES ('OLD', 'Old Product', 1.0)
            """
        )
    _write_products(csv_path, [_product("P1", "First Product")])

    validated = replace_products(
        db_file=db_path,
        csv_file=csv_path,
        report_dir=tmp_path / "reports",
        confirmation="",
        check_only=True,
    )

    assert validated == 1
    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT product_code FROM Product_list"
        ).fetchall() == [("OLD",)]
