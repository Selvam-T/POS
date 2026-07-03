"""Dump PRODUCT_CACHE to CSV for diagnostics.

Run from the Project folder:
    python dev_tools/diagnostics/dump_product_cache.py

Optional explicit DB:
    python dev_tools/diagnostics/dump_product_cache.py --db "../db/Anumani - Copy.db"
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_operation.product_cache import PRODUCT_CACHE, load_product_cache


OUTPUT_PATH = Path(__file__).resolve().parent / "product_cache_snapshot.csv"
HEADERS = ["product_code", "display_name", "selling_price", "unit", "category"]


def dump_product_cache(db_path: str | None = None) -> Path:
    if db_path:
        os.environ["POS_DB_PATH"] = db_path

    cache = load_product_cache()

    rows = []
    for product_code in sorted(cache.keys(), key=lambda value: value.casefold()):
        name, selling_price, unit, category = cache[product_code]
        rows.append(
            {
                "product_code": product_code,
                "display_name": name,
                "selling_price": selling_price,
                "unit": unit,
                "category": category,
            }
        )

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"PRODUCT_CACHE rows: {len(PRODUCT_CACHE)}")
    print(f"CSV written: {OUTPUT_PATH}")
    print("Preview:")
    for row in rows[:10]:
        print(
            f"{row['product_code']} | {row['display_name']} | "
            f"{row['selling_price']} | {row['unit']} | {row['category']}"
        )
    return OUTPUT_PATH


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        help="Optional database path. Use this only when inspecting a non-default DB file.",
    )
    args = parser.parse_args()
    dump_product_cache(args.db)
