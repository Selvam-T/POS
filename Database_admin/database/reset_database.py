"""Reset the configured database file by moving any existing file to a backup."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import db_path, print_header
from database.create_database import create_database


def reset_database(*, backup_existing: bool = True) -> Path:
    print_header("Reset Database")
    path = db_path()
    if path.exists():
        if backup_existing:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = path.with_name(f"{path.stem}_backup_{stamp}{path.suffix}")
            path.rename(backup)
            print(f"Existing database moved to: {backup}")
        else:
            path.unlink()
            print("Existing database deleted.")
    else:
        print("No existing database found.")

    return create_database(overwrite=False)


if __name__ == "__main__":
    reset_database()
