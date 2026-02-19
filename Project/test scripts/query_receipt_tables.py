"""Print first 10 rows from receipts, receipt_items, and receipt_payments.

Usage: python tools/query_receipt_tables.py
"""
import sqlite3
import sys
from pathlib import Path

# Ensure the project root is on sys.path so sibling package `modules` can be imported
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_operation.db import get_db_path


def print_table(cursor, table_name: str, limit: int = 10) -> None:
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = [r[1] for r in cursor.fetchall()]
    except Exception:
        print(f"Table not found: {table_name}\n")
        return

    print(f"--- {table_name} (first {limit} rows) ---")
    print("| ".join(cols))
    print('-' * 80)
    try:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,))
        rows = cursor.fetchall()
        if not rows:
            print("(no rows)")
        else:
            for r in rows:
                # r may be sqlite3.Row or tuple
                if isinstance(r, sqlite3.Row):
                    values = [str(r[c]) if r[c] is not None else '' for c in cols]
                else:
                    values = [str(x) if x is not None else '' for x in r]
                print(" | ".join(values))
    except Exception as e:
        print(f"Failed to query {table_name}: {e}")
    print('\n')


def main():
    db_path = get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
    except Exception as e:
        print(f"Failed to open DB at {db_path}: {e}")
        sys.exit(1)

    for t in ("receipts", "receipt_items", "receipt_payments"):
        print_table(cur, t, limit=100)

    conn.close()


if __name__ == '__main__':
    main()
