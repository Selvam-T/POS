"""Validate category master data and create the initial Category table.

This migration intentionally stops before converting Product_list.category
from text to category_id. It implements category migration steps 2 through 7:

* validate the complete category CSV with the application's validator;
* require protected categories and reject the UI-only placeholder;
* audit every existing Product_list category;
* map blank/NULL product categories to Other; and
* create and populate Category in the same transaction as that mapping.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path


ADMIN_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ADMIN_ROOT.parent / "Project"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from admin_lib import connect, db_path, print_header, table_exists
from modules.ui_utils.input_validation import validate_category


DEFAULT_CSV_PATH = ADMIN_ROOT / "Master_data" / "category_target_list.csv"
CSV_HEADER = "category"
UI_PLACEHOLDER = "--Select Category--"
PROTECTED_CATEGORIES = frozenset({"other", "vegetable"})


class CategoryMigrationError(ValueError):
    """Raised when category migration preflight or execution cannot continue."""


@dataclass(frozen=True)
class ProductCategoryAudit:
    product_count: int
    blank_or_null_count: int
    unknown_categories: tuple[str, ...]


def _key(value: object) -> str:
    return str(value or "").strip().casefold()


def validate_category_csv(csv_path: Path = DEFAULT_CSV_PATH) -> list[str]:
    """Return validated category names, or raise with every detected issue."""
    errors: list[str] = []
    names: list[str] = []
    seen: dict[str, int] = {}

    if not csv_path.is_file():
        raise CategoryMigrationError(f"Category CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.reader(source))

    headers = rows[0] if rows else []
    data_rows = rows[1:] if rows else []
    if headers != [CSV_HEADER]:
        errors.append(
            f"Header must be exactly '{CSV_HEADER}'; found {headers}"
        )

    for row_number, row in enumerate(data_rows, start=2):
        if not row:
            errors.append(f"Row {row_number}: blank category is not allowed")
            continue
        if len(row) != 1:
            errors.append(
                f"Row {row_number}: expected exactly one category cell; found {len(row)}"
            )
            continue
        name = str(row[0] or "").strip()
        if not name:
            errors.append(f"Row {row_number}: blank category is not allowed")
            continue

        ok, message = validate_category(name)
        if not ok:
            errors.append(f"Row {row_number}: {message}")
            continue

        key = _key(name)
        if key in seen:
            errors.append(
                f"Row {row_number}: duplicate category '{name}'; "
                f"first seen at row {seen[key]}"
            )
            continue

        seen[key] = row_number
        names.append(name)

    placeholder_key = _key(UI_PLACEHOLDER)
    if placeholder_key in seen:
        errors.append(
            f"UI placeholder '{UI_PLACEHOLDER}' must not be in the category CSV"
        )

    for required in sorted(PROTECTED_CATEGORIES):
        if required not in seen:
            display = "Other" if required == "other" else "Vegetable"
            errors.append(f"Required protected category missing: '{display}'")

    if errors:
        raise CategoryMigrationError(
            "Category CSV validation failed:\n- " + "\n- ".join(errors)
        )
    return names


def audit_product_categories(
    conn: sqlite3.Connection,
    category_names: list[str],
) -> ProductCategoryAudit:
    """Audit legacy product category text without modifying the database."""
    allowed = {_key(name) for name in category_names}
    rows = conn.execute(
        """
        SELECT category, COUNT(*) AS product_count
          FROM Product_list
         GROUP BY category
         ORDER BY category COLLATE NOCASE
        """
    ).fetchall()

    product_count = 0
    blank_or_null_count = 0
    unknown: list[str] = []
    for row in rows:
        count = int(row["product_count"])
        product_count += count
        category = row["category"]
        key = _key(category)
        if not key:
            blank_or_null_count += count
        elif key not in allowed:
            unknown.append(str(category))

    return ProductCategoryAudit(
        product_count=product_count,
        blank_or_null_count=blank_or_null_count,
        unknown_categories=tuple(unknown),
    )


def run_preflight(
    conn: sqlite3.Connection,
    csv_path: Path = DEFAULT_CSV_PATH,
) -> tuple[list[str], ProductCategoryAudit]:
    """Run all read-only checks required before category migration writes."""
    names = validate_category_csv(csv_path)
    audit = audit_product_categories(conn, names)
    if audit.unknown_categories:
        values = ", ".join(repr(value) for value in audit.unknown_categories)
        raise CategoryMigrationError(
            "Product_list contains categories absent from the validated CSV: "
            f"{values}"
        )
    return names, audit


def apply_steps_6_and_7(
    conn: sqlite3.Connection,
    category_names: list[str],
) -> int:
    """Map blank products and create/populate Category in one transaction."""
    if table_exists(conn, "Category"):
        raise CategoryMigrationError(
            "Category table already exists; migration was not applied"
        )

    try:
        conn.execute("BEGIN IMMEDIATE")
        blank_update = conn.execute(
            """
            UPDATE Product_list
               SET category = 'Other'
             WHERE category IS NULL OR trim(category) = ''
            """
        )
        conn.execute(
            """
            CREATE TABLE Category (
                category_id  INTEGER PRIMARY KEY,
                name         TEXT NOT NULL COLLATE NOCASE
                             UNIQUE
                             CHECK(name = trim(name))
                             CHECK(length(name) BETWEEN 3 AND 25),
                is_protected INTEGER NOT NULL DEFAULT 0
                             CHECK(is_protected IN (0, 1)),
                sort_order   INTEGER NOT NULL
                             CHECK(sort_order >= 0)
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO Category (name, is_protected, sort_order)
            VALUES (?, ?, ?)
            """,
            [
                (name, int(_key(name) in PROTECTED_CATEGORIES), sort_order)
                for sort_order, name in enumerate(category_names, start=1)
            ],
        )
        conn.commit()
        return int(blank_update.rowcount or 0)
    except Exception:
        conn.rollback()
        raise


def migrate_categories(
    conn: sqlite3.Connection,
    csv_path: Path = DEFAULT_CSV_PATH,
) -> tuple[list[str], ProductCategoryAudit, int]:
    """Preflight, then atomically perform migration steps 6 and 7."""
    names, audit = run_preflight(conn, csv_path)
    mapped_count = apply_steps_6_and_7(conn, names)
    return names, audit, mapped_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate and create the initial POS Category table."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help=f"Category CSV path (default: {DEFAULT_CSV_PATH})",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Run validation and Product_list audit without database writes.",
    )
    args = parser.parse_args()

    print_header("Category Table Migration")
    conn = connect()
    try:
        names, audit = run_preflight(conn, args.csv.resolve())
        print(f"Database: {db_path()}")
        print(f"Category CSV: {args.csv.resolve()}")
        print(f"Validated categories: {len(names)}")
        print(f"Products audited: {audit.product_count}")
        print(f"Blank/NULL product categories: {audit.blank_or_null_count}")
        print("Unknown product categories: 0")

        if args.preflight:
            print("PRE-FLIGHT PASSED: no database changes made.")
            return

        mapped_count = apply_steps_6_and_7(conn, names)
        print(f"Blank/NULL product categories mapped to Other: {mapped_count}")
        print(f"Category rows inserted: {len(names)}")
        print("MIGRATION STEPS 2-7 COMPLETED.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
