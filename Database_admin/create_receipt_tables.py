"""
Create Receipt Tables Script for Anumani POS

Creates the SQLite tables that back:
- Hold Sales (UNPAID receipts)
- View Hold (list/print/load/cancel UNPAID receipts)
- Receipt History (all receipts with status)
- Mixed payment types per receipt (receipt_payments)

Run this AFTER create_database.py.

Usage:
    python create_receipt_tables.py
"""
import sqlite3
from pathlib import Path


def load_config():
    config = {}
    env_path = Path(__file__).parent / "config" / ".env"
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


def create_receipt_tables(drop_existing=True):
    config = load_config()
    db_path = config.get("DB_PATH", "../db/Anumani.db")
    script_dir = Path(__file__).parent
    db_path = (script_dir / db_path).resolve()

    if not db_path.exists():
        print(f"\n✗ Database not found: {db_path}")
        print("Run create_database.py first!")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # IMPORTANT: SQLite only enforces foreign keys when this is ON.
    cursor.execute("PRAGMA foreign_keys = ON;")

    if drop_existing:
        # Drop child tables first
        cursor.execute("DROP TABLE IF EXISTS receipt_payments;")
        cursor.execute("DROP TABLE IF EXISTS receipt_items;")
        cursor.execute("DROP TABLE IF EXISTS receipts;")

    # receipts (header)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            receipt_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_no   TEXT    NOT NULL UNIQUE,
            customer_name TEXT,
            cashier_name TEXT    NOT NULL,
            status       TEXT    NOT NULL CHECK(status IN ('PAID','UNPAID','CANCELLED')),
            grand_total  REAL    NOT NULL,
            created_at   TEXT    NOT NULL,
            paid_at      TEXT,
            cancelled_at TEXT,
            note         TEXT
        );
    """)

    # receipt_items (lines) - snapshot fields; no FK to Product_list by design
    cursor.execute("""
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
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_receipt_items_receipt_id ON receipt_items(receipt_id);")

    # receipt_payments (supports mixed payment types per receipt)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipt_payments (
            payment_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_id   INTEGER NOT NULL,
            payment_type TEXT    NOT NULL CHECK(payment_type IN ('NETS','CASH','PAYNOW','OTHER')),
            tendered     REAL    NOT NULL,
            amount       REAL    NOT NULL CHECK(amount > 0),
            created_at   TEXT    NOT NULL,
            FOREIGN KEY(receipt_id) REFERENCES receipts(receipt_id) ON DELETE CASCADE
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_receipt_payments_receipt_id ON receipt_payments(receipt_id);")

    conn.commit()
    if drop_existing:
        print("✓ Tables dropped and recreated: receipts, receipt_items, receipt_payments")
    else:
        print("✓ Tables ensured: receipts, receipt_items, receipt_payments")
    conn.close()


if __name__ == "__main__":
    create_receipt_tables(drop_existing=True)
