"""Legacy schema-inspection template kept for reference."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import db_path


def migrate_schema() -> None:
    path = db_path()
    if not path.exists():
        print(f"Database not found: {path}")
        return
    conn = sqlite3.connect(str(path))
    try:
        print(f"Database: {path}")
        for row in conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"):
            print(f"\n[{row[0]}]\n{row[1]}")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_schema()
