"""Create a fresh Anumani POS database and import products.csv."""

from __future__ import annotations

import argparse

from audit.verify_db_and_product_list import verify_database
from database.create_database import create_database
from database.reset_database import reset_database
from migration.migrate_legacy_products import migrate_legacy_products
from migration.stage_legacy_products import stage_legacy_products
from migration.validate_legacy_products import validate_legacy_products
from tables.create_cash_outflows_table import create_cash_outflows_table
from tables.create_product_list_table import create_product_list_table
from tables.create_receipt_tables import create_receipt_tables
from tables.create_user_table import create_users_table
from users.initialize_default_users import initialize_default_users


def setup_fresh_database(*, reset: bool = False) -> None:
    if reset:
        reset_database()
    else:
        create_database()

    create_users_table()
    initialize_default_users()
    create_product_list_table()
    create_receipt_tables()
    create_cash_outflows_table()

    staged = stage_legacy_products()
    cleaned, _ = validate_legacy_products(staged)
    migrate_legacy_products(cleaned)
    verify_database()

    print("\nFresh database setup complete.")
    print("Next: run the POS app and check PRODUCT_CACHE, product lookup, receipts, holds, and cash outflows.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Move an existing Anumani.db to a timestamped backup before setup.",
    )
    args = parser.parse_args()
    setup_fresh_database(reset=args.reset)
