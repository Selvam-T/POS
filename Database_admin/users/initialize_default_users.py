"""Initialize default admin and staff accounts."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import connect, print_header


def _sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def initialize_default_users() -> None:
    print_header("Initialize Default Users")
    users = [
        ("admin", "admin123", "thiagarajan.selvam@gmail.com"),
        ("staff", "staff123", None),
    ]
    with connect() as conn:
        for username, password, email in users:
            conn.execute(
                """
                INSERT OR IGNORE INTO users
                  (username, password_hash, password_updated_at, recovery_email, is_active, must_change_password)
                VALUES
                  (?, ?, datetime('now'), ?, 1, 0)
                """,
                (username, _sha256(password), email),
            )
        conn.commit()

    print("Default users initialized or already present: admin, staff.")


if __name__ == "__main__":
    initialize_default_users()
