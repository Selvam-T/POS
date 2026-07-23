"""Verify database tables and Product_list health."""

from __future__ import annotations

import argparse
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


def verify_database(*, db_file: Path | str | None = None) -> None:
    selected_path = Path(db_file).resolve() if db_file is not None else db_path()
    print_header("Audit Database")
    print(f"Database: {selected_path}")
    with connect(selected_path) as conn:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        missing = sorted(EXPECTED_BASE_TABLES - tables)
        if missing:
            raise RuntimeError(f"Missing expected tables: {', '.join(missing)}")

        product_count = conn.execute("SELECT COUNT(*) AS c FROM Product_list").fetchone()["c"]
        print(f"Product_list rows: {product_count}")

        columns = {
            row["name"]: row for row in conn.execute("PRAGMA table_info('Product_list')")
        }
        code_column = columns.get("product_code")
        name_column = columns.get("name")
        if code_column is None or not bool(code_column["pk"]):
            raise RuntimeError("Product_list.product_code must be the primary key")
        if not bool(code_column["notnull"]):
            raise RuntimeError("Product_list.product_code must be NOT NULL")
        if name_column is None or not bool(name_column["notnull"]):
            raise RuntimeError("Product_list.name must be NOT NULL")

        indexes = conn.execute("PRAGMA index_list('Product_list')").fetchall()
        indexes_by_name = {row["name"]: row for row in indexes}
        if "idx_product_code_nocase" not in indexes_by_name:
            raise RuntimeError("Missing product-code index: idx_product_code_nocase")
        name_index = indexes_by_name.get("uq_product_name_nocase")
        if name_index is None:
            raise RuntimeError("Missing product-name unique index: uq_product_name_nocase")
        if not bool(name_index["unique"]):
            raise RuntimeError("Product-name index is not unique: uq_product_name_nocase")
        index_columns = conn.execute(
            "PRAGMA index_xinfo('uq_product_name_nocase')"
        ).fetchall()
        name_columns = [row for row in index_columns if row["key"] and row["cid"] >= 0]
        if len(name_columns) != 1 or name_columns[0]["name"] != "name":
            raise RuntimeError("uq_product_name_nocase does not index Product_list.name")
        if str(name_columns[0]["coll"]).upper() != "NOCASE":
            raise RuntimeError("uq_product_name_nocase must use NOCASE collation")
        print("Product name unique index: present (NOCASE)")
        print("Product code primary key and NOCASE lookup index: present")

        blank_codes = conn.execute(
            "SELECT COUNT(*) AS c FROM Product_list "
            "WHERE product_code IS NULL OR trim(product_code) = ''"
        ).fetchone()["c"]
        blank_names = conn.execute(
            "SELECT COUNT(*) AS c FROM Product_list "
            "WHERE name IS NULL OR trim(name) = ''"
        ).fetchone()["c"]
        duplicate_codes = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM (
              SELECT upper(trim(product_code)) AS k
              FROM Product_list
              GROUP BY upper(trim(product_code))
              HAVING COUNT(*) > 1
            )
            """
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
        if duplicate_codes:
            raise RuntimeError(f"Duplicate product-code groups found: {duplicate_codes}")
        if duplicate_names:
            raise RuntimeError(f"Duplicate product-name groups found: {duplicate_names}")

        print("Blank product codes: 0")
        print("Blank product names: 0")
        print("Duplicate product-code groups: 0")
        print("Duplicate product-name groups: 0")
        print(f"receipt_counters table exists now: {table_exists(conn, 'receipt_counters')}")
        print("Note: receipt_counters is created by POS runtime when receipt numbers are generated.")
        print("Audit passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit a complete POS database.")
    parser.add_argument("--db", type=Path, help="Explicit database path")
    args = parser.parse_args()
    verify_database(db_file=args.db)
