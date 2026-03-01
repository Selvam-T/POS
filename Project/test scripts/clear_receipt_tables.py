import sqlite3
import sys
from pathlib import Path

# Same path setup as your other files
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_operation.db import get_db_path


def _table_exists(cur, table_name: str) -> bool:
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    return cur.fetchone() is not None


def _safe_delete_all(cur, table_name: str) -> None:
    if not _table_exists(cur, table_name):
        print(f"Skipping {table_name}: table does not exist")
        return
    cur.execute(f"DELETE FROM {table_name}")
    print(f"Cleared {table_name}")

def clear_all_receipt_data():
    db_path = get_db_path()
    print(f"Using database: {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("BEGIN")

        # Child tables first, then parent table.
        _safe_delete_all(cur, "receipt_payments")
        _safe_delete_all(cur, "receipt_items")
        _safe_delete_all(cur, "receipts")

        # Reset auto-increment counters only when sqlite_sequence exists.
        if _table_exists(cur, "sqlite_sequence"):
            cur.execute(
                "DELETE FROM sqlite_sequence WHERE name IN ('receipts', 'receipt_items', 'receipt_payments')"
            )
            print("Reset sqlite_sequence for receipt tables")
        else:
            print("Skipping sqlite_sequence reset: table does not exist")

        conn.commit()
        print("\nAll receipt-related data has been cleared successfully.")

    except Exception as e:
        conn.rollback()
        print("Error:", e)
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    answer = input("This will DELETE ALL receipts, items and payments. Type YES to continue: ").strip().upper()
    if answer == "YES":
        clear_all_receipt_data()
    else:
        print("Cancelled.")