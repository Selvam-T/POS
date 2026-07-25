"""Create and seed the Category master table from the validated CSV."""

from __future__ import annotations

import sys
from pathlib import Path

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import connect, print_header
from migration.migrate_categories_to_table import (
    DEFAULT_CSV_PATH,
    PROTECTED_CATEGORIES,
    validate_category_csv,
)


def create_category_table(
    *,
    drop_existing: bool = False,
    csv_path: Path = DEFAULT_CSV_PATH,
    db_file: Path | str | None = None,
) -> None:
    names = validate_category_csv(csv_path)
    print_header("Create Category Table")
    with connect(db_file) as conn:
        if drop_existing:
            conn.execute("DROP TABLE IF EXISTS Category")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS Category (
                category_id  INTEGER PRIMARY KEY,
                name         TEXT NOT NULL COLLATE NOCASE
                             UNIQUE
                             CHECK(name = trim(name))
                             CHECK(length(name) BETWEEN 3 AND 25),
                is_protected INTEGER NOT NULL DEFAULT 0
                             CHECK(is_protected IN (0, 1)),
                sort_order   INTEGER NOT NULL CHECK(sort_order >= 0)
            )
            """
        )
        existing = int(conn.execute("SELECT COUNT(*) FROM Category").fetchone()[0])
        if existing == 0:
            conn.executemany(
                """
                INSERT INTO Category (name, is_protected, sort_order)
                VALUES (?, ?, ?)
                """,
                [
                    (
                        name,
                        int(name.strip().casefold() in PROTECTED_CATEGORIES),
                        order,
                    )
                    for order, name in enumerate(names, start=1)
                ],
            )
        conn.commit()
    print(f"Category ensured with {len(names)} validated master names.")


if __name__ == "__main__":
    create_category_table()
