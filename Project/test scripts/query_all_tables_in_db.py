import sys
import os

import sqlite3
# Get the directory of the current script, then go up one level
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Add that parent directory to the system path
sys.path.append(parent_dir)
from modules.db_operation.db import get_db_path

def list_tables(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [row[0] for row in cursor.fetchall()]

def list_records(cursor, table):
    cursor.execute(f"SELECT * FROM {table} LIMIT 5")
    return cursor.fetchall()

def count_records(cursor, table):
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    return cursor.fetchone()[0]

def main():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = list_tables(cursor)
    print("Tables in the database:")
    for table in tables:
        print(f"- {table}")

    print("\nRecords in each table:")
    for table in tables:
        print(f"\nTable: {table}")
        # Get and print column names
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Columns: {columns}")
        records = list_records(cursor, table)
        for record in records:
            print(record)

    print("\nRow count in each table:")
    for table in tables:
        count = count_records(cursor, table)
        print(f"{table}: {count} rows")

    conn.close()

if __name__ == "__main__":
    main()