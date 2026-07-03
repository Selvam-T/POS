"""Create the SQLite database file for Anumani POS."""

from __future__ import annotations

import sys
from pathlib import Path

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

import sqlite3

from admin_lib import db_path, print_header


def create_database(*, overwrite: bool = False) -> Path:
    path = db_path()
    print_header("Anumani POS - Database Creation")
    print(f"Database: {path}")

    if path.exists():
        if not overwrite:
            raise FileExistsError(
                f"Database already exists: {path}. Remove it first or run reset_database.py."
            )
        path.unlink()
        print("Deleted existing database.")

    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.close()
    print("Database created.")
    return path


if __name__ == "__main__":
    create_database()
