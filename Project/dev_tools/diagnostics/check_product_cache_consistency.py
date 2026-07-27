"""Compare Product_list rows with PRODUCT_CACHE.

Run from the Project folder:
    python dev_tools/diagnostics/check_product_cache_consistency.py

Optional explicit DB:
    python dev_tools/diagnostics/check_product_cache_consistency.py --db "../db/example.db"

A standalone process cannot inspect PRODUCT_CACHE in another running POS
process. If this process starts with an empty cache, the script loads it from
the selected database before comparing. ``compare_product_cache()`` can also
be imported and called inside the application process to inspect its live
cache without reloading it.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_operation import products_repo
from modules.db_operation.product_cache import PRODUCT_CACHE, load_product_cache
from modules.menu.diagnostics.product_cache_check import compare_product_cache


def run_check(db_path: str | None = None) -> dict:
    if db_path:
        os.environ["POS_DB_PATH"] = db_path

    if not PRODUCT_CACHE:
        print("PRODUCT_CACHE was empty in this diagnostic process; loading it now.")
        load_product_cache()

    result = compare_product_cache(products_repo.list_products(), PRODUCT_CACHE)
    print(f"Product_list total: {result['database_total']}")
    print(f"PRODUCT_CACHE total: {result['cache_total']}")
    print(f"Consistent: {result['consistent_total']}")
    print(f"Not consistent: {result['inconsistent_total']}")

    for code in result["missing_from_cache"]:
        print(f"MISSING FROM CACHE: {code}")
    for code in result["extra_in_cache"]:
        print(f"EXTRA IN CACHE: {code}")
    for code in result["value_mismatches"]:
        print(
            f"VALUE MISMATCH: {code} | "
            f"DB expected={result['expected'][code]!r} | "
            f"cache={result['actual'][code]!r}"
        )

    if result["inconsistent_total"] == 0:
        print("Result: Product_list and PRODUCT_CACHE are consistent.")
    else:
        print("Result: Product_list and PRODUCT_CACHE are NOT consistent.")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        help="Optional database path. Use this only for a non-default database.",
    )
    arguments = parser.parse_args()
    run_check(arguments.db)
