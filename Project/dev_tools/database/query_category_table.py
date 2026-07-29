import sqlite3
import sys
from contextlib import redirect_stdout
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_operation.sqlite_runtime import get_db_path


def run_query():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(Category)")
    columns = [row[1] for row in cursor.fetchall()]
    if not columns:
        print("Category table not found")
        conn.close()
        return

    cursor.execute(
        """
        SELECT *
          FROM Category
         ORDER BY
           CASE WHEN name = 'Other' COLLATE NOCASE THEN 1 ELSE 0 END,
           name COLLATE NOCASE
        """
    )
    rows = cursor.fetchall()

    print(" | ".join(columns))
    print("-" * 100)
    if not rows:
        print("Category table is empty")
    else:
        for row in rows:
            print(" | ".join("" if value is None else str(value) for value in row))

    print(f"\nTotal categories: {len(rows)}")
    conn.close()


def main():
    output_path = Path(__file__).with_suffix(".txt")
    with output_path.open("w", encoding="utf-8") as output_file:
        with redirect_stdout(output_file):
            run_query()
    print(f"Query output written to: {output_path}")


if __name__ == "__main__":
    main()
