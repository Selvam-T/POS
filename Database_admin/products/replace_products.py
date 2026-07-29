"""Safely replace Product_list in an existing complete database."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Iterable, List

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import print_header, table_exists
from migration.stage_legacy_products import stage_legacy_products
from migration.validate_legacy_products import validate_legacy_products


CONFIRMATION = "REPLACE-PRODUCT-LIST"


def _connect_explicit(db_file: Path) -> sqlite3.Connection:
    path = db_file.resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Database not found: {path}")
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _table_counts(conn: sqlite3.Connection, *, exclude: Iterable[str] = ()) -> Dict[str, int]:
    excluded = set(exclude)
    table_names = [
        str(row["name"])
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
        if row["name"] not in excluded
    ]
    counts: Dict[str, int] = {}
    for table_name in table_names:
        escaped = table_name.replace('"', '""')
        counts[table_name] = int(
            conn.execute(f'SELECT COUNT(*) AS c FROM "{escaped}"').fetchone()["c"]
        )
    return counts


def _resolve_product_category_ids(
    conn: sqlite3.Connection,
    rows: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    category_ids = {
        str(row["name"]).strip().casefold(): int(row["category_id"])
        for row in conn.execute("SELECT category_id, name FROM Category")
    }
    resolved: List[Dict[str, object]] = []
    missing: set[str] = set()
    for row in rows:
        category_name = str(row.get("category") or "Other").strip()
        category_id = category_ids.get(category_name.casefold())
        if category_id is None:
            missing.add(category_name)
            continue
        product = dict(row)
        product["category_id"] = category_id
        resolved.append(product)
    if missing:
        names = ", ".join(sorted(missing, key=str.casefold))
        raise ValueError(f"Product categories are absent from Category: {names}")
    return resolved


def _insert_products(conn: sqlite3.Connection, rows: List[Dict[str, object]]) -> int:
    inserted = 0
    for row in rows:
        cost_text = str(row.get("cost_price") or "").strip()
        cost_price = float(cost_text) if cost_text else None
        conn.execute(
            """
            INSERT INTO Product_list
              (product_code, name, category_id, supplier, selling_price, cost_price, unit, last_updated)
            VALUES
              (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["product_code"],
                row["name"],
                row["category_id"],
                row.get("supplier") or "",
                float(row["selling_price"]),
                cost_price,
                row.get("unit") or "Each",
                row.get("last_updated") or "",
            ),
        )
        inserted += 1
    return inserted


def _verify_product_integrity(conn: sqlite3.Connection, expected_count: int) -> None:
    actual_count = int(
        conn.execute("SELECT COUNT(*) AS c FROM Product_list").fetchone()["c"]
    )
    if actual_count != expected_count:
        raise RuntimeError(
            f"Product row-count mismatch: expected {expected_count}, found {actual_count}"
        )

    blank_count = int(
        conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM Product_list
            WHERE product_code IS NULL
               OR trim(product_code) = ''
               OR name IS NULL
               OR trim(name) = ''
            """
        ).fetchone()["c"]
    )
    if blank_count:
        raise RuntimeError(f"Blank required product values found: {blank_count}")

    duplicate_codes = int(
        conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM (
              SELECT upper(trim(product_code))
              FROM Product_list
              GROUP BY upper(trim(product_code))
              HAVING COUNT(*) > 1
            )
            """
        ).fetchone()["c"]
    )
    duplicate_names = int(
        conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM (
              SELECT lower(trim(name))
              FROM Product_list
              GROUP BY lower(trim(name))
              HAVING COUNT(*) > 1
            )
            """
        ).fetchone()["c"]
    )
    if duplicate_codes:
        raise RuntimeError(f"Duplicate product-code groups found: {duplicate_codes}")
    if duplicate_names:
        raise RuntimeError(f"Duplicate product-name groups found: {duplicate_names}")


def replace_products(
    *,
    db_file: Path,
    csv_file: Path,
    report_dir: Path | None = None,
    confirmation: str,
    check_only: bool = False,
) -> int:
    """Validate a complete CSV and transactionally replace only Product_list."""
    database_path = db_file.resolve()
    csv_path = csv_file.resolve()
    reports = (report_dir or csv_path.parent).resolve()

    print_header("Validate Product_list Replacement")
    print(f"Database: {database_path}")
    print(f"CSV: {csv_path}")
    staged = stage_legacy_products(csv_path)
    cleaned, _ = validate_legacy_products(staged, report_dir=reports)
    print(f"Validated product rows: {len(cleaned)}")

    if check_only:
        print("Check-only completed. Database was not modified.")
        return len(cleaned)

    if confirmation != CONFIRMATION:
        raise ValueError(
            f"Replacement confirmation missing. Supply exactly: {CONFIRMATION}"
        )

    with _connect_explicit(database_path) as conn:
        if not table_exists(conn, "Category"):
            raise RuntimeError("Category table does not exist")
        if not table_exists(conn, "Product_list"):
            raise RuntimeError("Product_list table does not exist")
        product_columns = {
            str(row["name"])
            for row in conn.execute("PRAGMA table_info('Product_list')")
        }
        if "category_id" not in product_columns or "category" in product_columns:
            raise RuntimeError(
                "Product_list must use the category_id foreign-key schema"
            )
        resolved_products = _resolve_product_category_ids(conn, cleaned)

        before_products = int(
            conn.execute("SELECT COUNT(*) AS c FROM Product_list").fetchone()["c"]
        )
        unrelated_before = _table_counts(conn, exclude={"Product_list"})

        try:
            conn.execute("BEGIN IMMEDIATE;")
            conn.execute("DELETE FROM Product_list;")
            inserted = _insert_products(conn, resolved_products)
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_product_name_nocase "
                "ON Product_list(name COLLATE NOCASE);"
            )
            _verify_product_integrity(conn, len(cleaned))

            unrelated_after = _table_counts(conn, exclude={"Product_list"})
            if unrelated_after != unrelated_before:
                raise RuntimeError(
                    "An unrelated table row count changed during Product_list replacement"
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    print(f"Product_list rows before: {before_products}")
    print(f"Product_list rows after: {inserted}")
    print("Unrelated table row counts preserved.")
    print("Product_list replacement committed.")
    return inserted


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate and transactionally replace only Product_list."
    )
    parser.add_argument("--db", required=True, type=Path, help="Explicit working-copy database")
    parser.add_argument("--csv", required=True, type=Path, help="Complete product CSV")
    parser.add_argument(
        "--report-dir",
        type=Path,
        help="Validation report directory (defaults to the CSV directory)",
    )
    parser.add_argument(
        "--confirm",
        default="",
        help=f"Required replacement phrase: {CONFIRMATION}",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate and write reports without modifying the database",
    )
    args = parser.parse_args()
    replace_products(
        db_file=args.db,
        csv_file=args.csv,
        report_dir=args.report_dir,
        confirmation=args.confirm,
        check_only=args.check_only,
    )
