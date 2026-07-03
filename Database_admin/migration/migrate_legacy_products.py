"""Migrate validated product rows into Product_list."""

from __future__ import annotations

import sys
from pathlib import Path

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import connect, read_csv_rows, print_header
from migration.validate_legacy_products import CLEANED_PATH


def migrate_legacy_products(cleaned_path: Path = CLEANED_PATH) -> int:
    print_header("Migrate Legacy Products")
    if not cleaned_path.exists():
        raise FileNotFoundError(f"Cleaned product file not found: {cleaned_path}")

    rows = read_csv_rows(cleaned_path)
    inserted = 0
    with connect() as conn:
        for row in rows:
            cost_text = str(row.get("cost_price") or "").strip()
            cost_price = float(cost_text) if cost_text else None
            conn.execute(
                """
                INSERT INTO Product_list
                  (product_code, name, category, supplier, selling_price, cost_price, unit, last_updated)
                VALUES
                  (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["product_code"],
                    row["name"],
                    row.get("category") or "Other",
                    row.get("supplier") or "",
                    float(row["selling_price"]),
                    cost_price,
                    row.get("unit") or "Each",
                    row.get("last_updated") or "",
                ),
            )
            inserted += 1
        conn.commit()

    print(f"Rows inserted into Product_list: {inserted}")
    return inserted


if __name__ == "__main__":
    migrate_legacy_products()
