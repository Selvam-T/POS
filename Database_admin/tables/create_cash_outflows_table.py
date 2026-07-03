"""Create the cash_outflows table."""

from __future__ import annotations

import sys
from pathlib import Path

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import connect, print_header


def create_cash_outflows_table(*, drop_existing: bool = False) -> None:
    print_header("Create Cash Outflows Table")
    with connect() as conn:
        if drop_existing:
            conn.execute("DROP TABLE IF EXISTS cash_outflows;")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cash_outflows (
                outflows_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                outflows_type TEXT    NOT NULL CHECK(outflows_type IN ('REFUND_OUT','VENDOR_OUT','CASH_IN_OTHER')),
                amount        REAL    NOT NULL CHECK(amount != 0),
                created_at    TEXT    NOT NULL,
                cashier_id    INTEGER NOT NULL,
                note          TEXT,
                FOREIGN KEY(cashier_id) REFERENCES users(user_id) ON DELETE RESTRICT
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cash_outflows_created_at ON cash_outflows(created_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cash_outflows_type ON cash_outflows(outflows_type);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cash_outflows_cashier ON cash_outflows(cashier_id);")
        conn.commit()

    print("cash_outflows ensured.")


if __name__ == "__main__":
    create_cash_outflows_table(drop_existing=False)
