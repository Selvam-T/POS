import sqlite3
from pathlib import Path
import sys

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


def clear_users_table():
    db_path = get_db_path()
    print(f"Using database: {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("BEGIN")

        if not _table_exists(cur, "users"):
            print("users table does not exist → nothing to clear")
            return

        cur.execute("DELETE FROM users")
        print("Cleared users table")

        if _table_exists(cur, "sqlite_sequence"):
            cur.execute("DELETE FROM sqlite_sequence WHERE name = 'users'")
            print("Reset sqlite_sequence for users")

        conn.commit()
        print("\nUsers table cleared successfully.")

    except Exception as e:
        conn.rollback()
        print("Error:", e)
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    answer = input("This will DELETE ALL users. Type YES to continue: ").strip().upper()
    if answer == "YES":
        clear_users_table()
    else:
        print("Cancelled.")