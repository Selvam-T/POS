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

if __name__ == "__main__":
    main()