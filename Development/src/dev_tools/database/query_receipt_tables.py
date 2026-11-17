"""Print first 10 rows from receipts, receipt_items, and receipt_payments.

Usage: python dev_tools/database/query_receipt_tables.py
"""
import sqlite3
import sys
from contextlib import redirect_stdout
from pathlib import Path

# Ensure the project root is on sys.path so sibling package `modules` can be imported
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_operation.sqlite_runtime import get_db_path
LIMIT = 10

def print_table(cursor, table_name: str, limit: int = 10) -> None:
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = [r[1] for r in cursor.fetchall()]
    except Exception:
        print(f"Table not found: {table_name}\n")
        return

    print(f"\n[ {table_name} Table - {limit} rows ]")
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


def run_query():
    db_path = get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
    except Exception as e:
        print(f"Failed to open DB at {db_path}: {e}")
        sys.exit(1)

    for t in ("receipts", "receipt_items", "receipt_payments"):
        print_table(cur, t, limit=LIMIT)

    conn.close()


def main():
    output_path = Path(__file__).with_suffix(".txt")
    with output_path.open("w", encoding="utf-8") as output_file:
        with redirect_stdout(output_file):
            run_query()
    print(f"Query output written to: {output_path}")


if __name__ == '__main__':
    main()
