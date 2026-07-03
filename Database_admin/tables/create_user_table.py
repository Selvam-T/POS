"""Create the users table."""

from __future__ import annotations

import sys
from pathlib import Path

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import connect, print_header


def create_users_table(*, drop_existing: bool = False) -> None:
    print_header("Create Users Table")
    with connect() as conn:
        if drop_existing:
            conn.execute("DROP TABLE IF EXISTS users;")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id               INTEGER PRIMARY KEY AUTOINCREMENT,
                username              TEXT    NOT NULL UNIQUE,
                password_hash         TEXT    NOT NULL,
                password_updated_at   TEXT    NOT NULL,
                recovery_email        TEXT,
                is_active             INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
                must_change_password  INTEGER NOT NULL DEFAULT 0 CHECK(must_change_password IN (0,1))
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
        conn.commit()

    print("users ensured.")


if __name__ == "__main__":
    create_users_table(drop_existing=False)
