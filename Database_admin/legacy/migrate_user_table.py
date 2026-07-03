"""Legacy maintenance script: add users.must_change_password to an old DB."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import db_path


def migrate_must_change_password() -> None:
    path = db_path()
    if not path.exists():
        print(f"Database file not found: {path}")
        return

    conn = sqlite3.connect(str(path))
    try:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "must_change_password" in cols:
            print("Skip: must_change_password already exists.")
            return
        conn.execute(
            "ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0"
        )
        conn.commit()
        print("Added users.must_change_password.")
    except sqlite3.Error as exc:
        conn.rollback()
        print(f"Database error during migration: {exc}")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_must_change_password()
