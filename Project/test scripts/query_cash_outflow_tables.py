import sys
import os

import sqlite3
# Get the directory of the current script, then go up one level
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Add that parent directory to the system path
sys.path.append(parent_dir)
from modules.db_operation.db import get_db_path

def main():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM cash_outflows ORDER BY created_at DESC LIMIT 20")
    rows = cursor.fetchall()

    if not rows:
        print("cash_outflows table is empty")
        conn.close()
        return

    # Print header
    cursor.execute("PRAGMA table_info(cash_outflows)")
    columns = [row[1] for row in cursor.fetchall()]
    print(" | ".join(columns))
    print("-" * 80)

    for row in rows:
        print(" | ".join(str(x) for x in row))

    cursor.execute("SELECT COUNT(*) FROM cash_outflows")
    count = cursor.fetchone()[0]
    print(f"\nTotal rows: {count}")

    conn.close()

if __name__ == "__main__":
    main()