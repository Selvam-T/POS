import sys
import os
from contextlib import redirect_stdout
from pathlib import Path

import sqlite3
# Get the project root from dev_tools/database.
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add that parent directory to the system path
sys.path.append(parent_dir)
from modules.db_operation.sqlite_runtime import get_db_path

def run_query():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users ORDER BY user_id DESC LIMIT 10")
    rows = cursor.fetchall()

    if not rows:
        print("users table is empty")
        conn.close()
        return

    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    print(" | ".join(columns))
    print("-" * 100)

    for row in rows:
        print(" | ".join(str(x) for x in row))

    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    print(f"\nTotal users: {count}")

    conn.close()


def main():
    output_path = Path(__file__).with_suffix(".txt")
    with output_path.open("w", encoding="utf-8") as output_file:
        with redirect_stdout(output_file):
            run_query()
    print(f"Query output written to: {output_path}")


if __name__ == "__main__":
    main()
