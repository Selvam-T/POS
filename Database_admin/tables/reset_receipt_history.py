"""Development helper: reset receipt history and receipt counters."""

from __future__ import annotations

import sys
from pathlib import Path

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import connect, print_header
from tables.create_receipt_tables import create_receipt_tables


def reset_receipt_history() -> None:
    print_header("Reset Receipt History")
    with connect() as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("DROP TABLE IF EXISTS receipt_payments;")
        conn.execute("DROP TABLE IF EXISTS receipt_items;")
        conn.execute("DROP TABLE IF EXISTS receipts;")
        conn.execute("DROP TABLE IF EXISTS receipt_counters;")
        conn.commit()

    create_receipt_tables(drop_existing=False)
    print("Receipt history and receipt counters reset.")


if __name__ == "__main__":
    reset_receipt_history()
