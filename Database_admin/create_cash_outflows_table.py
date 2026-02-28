"""
Create Cash movements Table Script for Anumani POS

Creates the SQLite table that tracks cash leaving the drawer/account:
- REFUND_OUT (refunds / voids)
- VENDOR_OUT (vendor/supplier payments)

This table is independent of receipts.

Run this AFTER create_database.py.

Usage:
    python create_cash_outflows_table.py
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


def create_cash_outflows_table(drop_existing: bool = False) -> None:
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

    # (Not strictly needed here, but consistent with other scripts)
    cursor.execute("PRAGMA foreign_keys = ON;")

    if drop_existing:cursor.execute("DROP TABLE IF EXISTS cash_outflows;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cash_outflows (
            outflows_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            outflows_type  TEXT    NOT NULL CHECK(outflows_type IN ('REFUND_OUT','VENDOR_OUT','CASH_IN_OTHER')),
            amount         REAL    NOT NULL CHECK(amount != 0),
            created_at     TEXT    NOT NULL,
            actor_user_id  INTEGER NOT NULL,
            note           TEXT,
            FOREIGN KEY(actor_user_id) REFERENCES users(user_id) ON DELETE RESTRICT
        );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cash_outflows_created_at ON cash_outflows(created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cash_outflows_type ON cash_outflows(outflows_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cash_outflows_actor ON cash_outflows(actor_user_id);")

    # ... commit and print messages (update print to "cash_outflows")
    conn.commit()
    if drop_existing:
        print("Table dropped and recreated: cash_outflows")
    else:
        print("Table ensured: cash_outflows")
    conn.close()


if __name__ == "__main__":
    create_cash_outflows_table(drop_existing=False)
