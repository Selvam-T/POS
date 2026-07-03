"""Create receipt, receipt_items, and receipt_payments tables."""

from __future__ import annotations

import sys
from pathlib import Path

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import connect, print_header


def create_receipt_tables(*, drop_existing: bool = False) -> None:
    print_header("Create Receipt Tables")
    with connect() as conn:
        if drop_existing:
            conn.execute("DROP TABLE IF EXISTS receipt_payments;")
            conn.execute("DROP TABLE IF EXISTS receipt_items;")
            conn.execute("DROP TABLE IF EXISTS receipts;")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS receipts (
                receipt_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_no      TEXT    NOT NULL UNIQUE,
                customer_name   TEXT,
                cashier_id      INTEGER NOT NULL,
                status          TEXT    NOT NULL CHECK(status IN ('PAID','UNPAID','CANCELLED')),
                grand_total     REAL    NOT NULL,
                created_at      TEXT    NOT NULL,
                paid_at         TEXT,
                cancelled_at    TEXT,
                note            TEXT,
                FOREIGN KEY(cashier_id) REFERENCES users(user_id) ON DELETE RESTRICT
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS receipt_items (
                item_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id   INTEGER NOT NULL,
                line_no      INTEGER NOT NULL,
                product_code TEXT    NOT NULL,
                product_name TEXT    NOT NULL,
                category     TEXT,
                qty          REAL    NOT NULL,
                unit         TEXT    NOT NULL,
                unit_price   REAL    NOT NULL,
                line_total   REAL    NOT NULL,
                UNIQUE(receipt_id, line_no),
                FOREIGN KEY(receipt_id) REFERENCES receipts(receipt_id) ON DELETE CASCADE
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_receipt_items_receipt_id ON receipt_items(receipt_id);")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS receipt_payments (
                payment_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id   INTEGER NOT NULL,
                payment_type TEXT    NOT NULL CHECK(payment_type IN ('NETS','CASH','PAYNOW','OTHER')),
                tendered     REAL    NOT NULL,
                amount       REAL    NOT NULL CHECK(amount > 0),
                created_at   TEXT    NOT NULL,
                FOREIGN KEY(receipt_id) REFERENCES receipts(receipt_id) ON DELETE CASCADE
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_receipt_payments_receipt_id ON receipt_payments(receipt_id);")
        conn.commit()

    print("receipts, receipt_items, and receipt_payments ensured.")
    print("receipt_counters is intentionally created by the POS runtime receipt number service.")


if __name__ == "__main__":
    create_receipt_tables(drop_existing=False)
