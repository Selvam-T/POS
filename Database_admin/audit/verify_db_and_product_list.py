"""Verify database tables and Product_list health."""

from __future__ import annotations

import sys
from pathlib import Path

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import connect, db_path, print_header, table_exists


EXPECTED_BASE_TABLES = {
    "Product_list",
    "users",
    "cash_outflows",
    "receipts",
    "receipt_items",
    "receipt_payments",
}


def verify_database() -> None:
    print_header("Audit Database")
    print(f"Database: {db_path()}")
    with connect() as conn:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        missing = sorted(EXPECTED_BASE_TABLES - tables)
        if missing:
            raise RuntimeError(f"Missing expected tables: {', '.join(missing)}")

        product_count = conn.execute("SELECT COUNT(*) AS c FROM Product_list").fetchone()["c"]
        print(f"Product_list rows: {product_count}")

        indexes = conn.execute("PRAGMA index_list('Product_list')").fetchall()
        index_names = {row["name"] for row in indexes}
        if "uq_product_name_nocase" in index_names:
            raise RuntimeError("Unexpected product-name unique index exists: uq_product_name_nocase")
        print("Product name unique index: absent")

        blank_codes = conn.execute(
            "SELECT COUNT(*) AS c FROM Product_list WHERE trim(product_code) = ''"
        ).fetchone()["c"]
        blank_names = conn.execute(
            "SELECT COUNT(*) AS c FROM Product_list WHERE trim(name) = ''"
        ).fetchone()["c"]
        duplicate_names = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM (
              SELECT lower(trim(name)) AS k
              FROM Product_list
              GROUP BY lower(trim(name))
              HAVING COUNT(*) > 1
            )
            """
        ).fetchone()["c"]

        if blank_codes:
            raise RuntimeError(f"Blank product_code rows found: {blank_codes}")
        if blank_names:
            raise RuntimeError(f"Blank product name rows found: {blank_names}")

        print(f"Duplicate product-name groups allowed in DB: {duplicate_names}")
        print(f"receipt_counters table exists now: {table_exists(conn, 'receipt_counters')}")
        print("Note: receipt_counters is created by POS runtime when receipt numbers are generated.")
        print("Audit passed.")


if __name__ == "__main__":
    verify_database()
