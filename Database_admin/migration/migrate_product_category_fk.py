"""Replace Product_list.category text with a required Category foreign key.

Implements controlled category migration steps 8 through 11. Steps 8–10 run
inside one transaction and roll back together if mapping or preservation
verification fails.
"""

from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path


ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import connect, db_path, print_header, table_exists


class ProductCategoryForeignKeyMigrationError(RuntimeError):
    """Raised when Product_list category-id migration cannot continue safely."""


@dataclass(frozen=True)
class MigrationResult:
    products_mapped: int
    products_rebuilt: int


def _column_names(conn: sqlite3.Connection, table_name: str) -> list[str]:
    return [str(row["name"]) for row in conn.execute(f'PRAGMA table_info("{table_name}")')]


def validate_preconditions(conn: sqlite3.Connection) -> int:
    """Validate the expected intermediate schema and return product count."""
    if not table_exists(conn, "Category"):
        raise ProductCategoryForeignKeyMigrationError(
            "Category table is missing; complete migration steps 2-7 first"
        )
    if not table_exists(conn, "Product_list"):
        raise ProductCategoryForeignKeyMigrationError("Product_list is missing")

    columns = _column_names(conn, "Product_list")
    if "category" not in columns:
        raise ProductCategoryForeignKeyMigrationError(
            "Product_list.category is missing; steps 8-10 may already be complete"
        )
    if "category_id" in columns:
        raise ProductCategoryForeignKeyMigrationError(
            "Product_list.category_id already exists; refusing a partial rerun"
        )

    protected = {
        str(row["name"]).casefold()
        for row in conn.execute(
            "SELECT name FROM Category WHERE is_protected = 1"
        )
    }
    if protected != {"other", "vegetable"}:
        raise ProductCategoryForeignKeyMigrationError(
            "Category protection mismatch; expected only Other and Vegetable"
        )

    unresolved = conn.execute(
        """
        SELECT DISTINCT p.category
          FROM Product_list AS p
          LEFT JOIN Category AS c
            ON trim(p.category) = c.name COLLATE NOCASE
         WHERE p.category IS NULL
            OR trim(p.category) = ''
            OR c.category_id IS NULL
         ORDER BY p.category COLLATE NOCASE
        """
    ).fetchall()
    if unresolved:
        values = ", ".join(repr(row["category"]) for row in unresolved)
        raise ProductCategoryForeignKeyMigrationError(
            f"Unresolved Product_list categories: {values}"
        )

    return int(conn.execute("SELECT COUNT(*) FROM Product_list").fetchone()[0])


def _verify_staged_mapping(conn: sqlite3.Connection, expected_count: int) -> None:
    unresolved_count = int(
        conn.execute(
            "SELECT COUNT(*) FROM Product_list WHERE category_id IS NULL"
        ).fetchone()[0]
    )
    mapped_count = int(
        conn.execute(
            "SELECT COUNT(*) FROM Product_list WHERE category_id IS NOT NULL"
        ).fetchone()[0]
    )
    if unresolved_count:
        raise ProductCategoryForeignKeyMigrationError(
            f"Step 9 failed: {unresolved_count} products have no category_id"
        )
    if mapped_count != expected_count:
        raise ProductCategoryForeignKeyMigrationError(
            f"Step 9 failed: expected {expected_count} mappings, found {mapped_count}"
        )


def _verify_rebuild_before_drop(conn: sqlite3.Connection, expected_count: int) -> None:
    rebuilt_count = int(
        conn.execute("SELECT COUNT(*) FROM Product_list_new").fetchone()[0]
    )
    if rebuilt_count != expected_count:
        raise ProductCategoryForeignKeyMigrationError(
            f"Rebuild row mismatch: expected {expected_count}, found {rebuilt_count}"
        )

    comparison_columns = """
        product_code, name, category_id, supplier,
        selling_price, cost_price, unit, last_updated
    """
    lost = int(
        conn.execute(
            f"""
            SELECT COUNT(*) FROM (
                SELECT {comparison_columns} FROM Product_list
                EXCEPT
                SELECT {comparison_columns} FROM Product_list_new
            )
            """
        ).fetchone()[0]
    )
    added = int(
        conn.execute(
            f"""
            SELECT COUNT(*) FROM (
                SELECT {comparison_columns} FROM Product_list_new
                EXCEPT
                SELECT {comparison_columns} FROM Product_list
            )
            """
        ).fetchone()[0]
    )
    if lost or added:
        raise ProductCategoryForeignKeyMigrationError(
            f"Rebuild value mismatch: lost={lost}, added={added}"
        )


def migrate_product_category_fk(conn: sqlite3.Connection) -> MigrationResult:
    """Perform steps 8–10 atomically and verify the rebuilt table."""
    product_count = validate_preconditions(conn)

    try:
        conn.execute("BEGIN IMMEDIATE")

        # Step 8: add a temporary nullable column and map every legacy name.
        conn.execute("ALTER TABLE Product_list ADD COLUMN category_id INTEGER")
        mapped = conn.execute(
            """
            UPDATE Product_list
               SET category_id = (
                   SELECT c.category_id
                     FROM Category AS c
                    WHERE c.name = trim(Product_list.category) COLLATE NOCASE
               )
            """
        )

        # Step 9: do not proceed to the rebuild unless every row resolved.
        _verify_staged_mapping(conn, product_count)

        # Step 10: rebuild with only category_id and an enforced relationship.
        conn.execute(
            """
            CREATE TABLE Product_list_new (
                product_code  TEXT PRIMARY KEY NOT NULL
                              CHECK(trim(product_code) <> ''),
                name          TEXT NOT NULL CHECK(trim(name) <> ''),
                category_id   INTEGER NOT NULL,
                supplier      TEXT,
                selling_price REAL NOT NULL,
                cost_price    REAL,
                unit          TEXT,
                last_updated  TEXT,
                FOREIGN KEY (category_id)
                    REFERENCES Category(category_id)
                    ON UPDATE RESTRICT
                    ON DELETE RESTRICT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO Product_list_new (
                product_code, name, category_id, supplier,
                selling_price, cost_price, unit, last_updated
            )
            SELECT
                product_code, name, category_id, supplier,
                selling_price, cost_price, unit, last_updated
              FROM Product_list
            """
        )
        _verify_rebuild_before_drop(conn, product_count)

        conn.execute("DROP TABLE Product_list")
        conn.execute("ALTER TABLE Product_list_new RENAME TO Product_list")
        conn.execute(
            """
            CREATE INDEX idx_product_code_nocase
                ON Product_list(product_code COLLATE NOCASE)
            """
        )

        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise ProductCategoryForeignKeyMigrationError(
                f"Foreign-key verification failed: {len(violations)} violation(s)"
            )

        conn.commit()
        return MigrationResult(
            products_mapped=int(mapped.rowcount or 0),
            products_rebuilt=product_count,
        )
    except Exception:
        conn.rollback()
        raise


def main() -> None:
    print_header("Product Category Foreign-Key Migration")
    conn = connect()
    try:
        result = migrate_product_category_fk(conn)
        print(f"Database: {db_path()}")
        print(f"Step 8 - products mapped to category_id: {result.products_mapped}")
        print("Step 9 - unresolved category mappings: 0")
        print(f"Step 10 - Product_list rows rebuilt: {result.products_rebuilt}")
        print("Step 11 - transactional foreign-key verification: passed")
        print("MIGRATION STEPS 8-11 COMPLETED.")
        print(
            "NOTICE: POS runtime conversion is still required before application use."
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
