"""Export Product_list to CSV."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import DATA_DIR, connect, db_path


def export_products(out_path: Path | None = None) -> Path:
    output = out_path or (DATA_DIR / "product_export.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT product_code, name, category, supplier, selling_price, cost_price, unit, last_updated
            FROM Product_list
            ORDER BY name COLLATE NOCASE, product_code COLLATE NOCASE
            """
        ).fetchall()

    headers = [
        "product_code",
        "name",
        "category",
        "supplier",
        "selling_price",
        "cost_price",
        "unit",
        "last_updated",
    ]
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(["" if row[h] is None else row[h] for h in headers])

    print(f"Exported {len(rows)} products from {db_path()} to {output}")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", help="Output CSV path")
    args = parser.parse_args()
    export_products(Path(args.out) if args.out else None)
