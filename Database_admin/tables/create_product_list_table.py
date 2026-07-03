"""Create the Product_list table."""

from __future__ import annotations

import sys
from pathlib import Path

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import connect, print_header


def create_product_list_table(*, drop_existing: bool = False) -> None:
    print_header("Create Product_list Table")
    with connect() as conn:
        if drop_existing:
            conn.execute("DROP TABLE IF EXISTS Product_list;")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS Product_list (
                product_code  TEXT PRIMARY KEY NOT NULL CHECK(trim(product_code) <> ''),
                name          TEXT NOT NULL CHECK(trim(name) <> ''),
                category      TEXT,
                supplier      TEXT,
                selling_price REAL NOT NULL,
                cost_price    REAL,
                unit          TEXT,
                last_updated  TEXT
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_product_code_nocase "
            "ON Product_list(product_code COLLATE NOCASE);"
        )
        conn.execute("DROP INDEX IF EXISTS uq_product_name_nocase;")
        conn.commit()

    print("Product_list ensured. Product names are not unique at DB level.")


if __name__ == "__main__":
    create_product_list_table(drop_existing=False)
