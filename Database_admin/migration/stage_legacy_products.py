"""Stage raw legacy product CSV rows for validation."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import DATA_DIR, products_csv_path, read_csv_rows, write_csv_rows, print_header


PRODUCT_HEADERS = [
    "product_code",
    "name",
    "category",
    "supplier",
    "selling_price",
    "cost_price",
    "unit",
    "last_updated",
]

STAGED_PATH = DATA_DIR / "staged_products.csv"


def stage_legacy_products(csv_path: Path | None = None) -> Path:
    print_header("Stage Legacy Products")
    source = csv_path or products_csv_path()
    if not source.exists():
        raise FileNotFoundError(f"Product CSV not found: {source}")

    rows = read_csv_rows(source)
    if not rows:
        raise ValueError(f"Product CSV is empty: {source}")

    missing = [h for h in PRODUCT_HEADERS if h not in rows[0]]
    if missing:
        raise ValueError(f"Product CSV is missing required headers: {', '.join(missing)}")

    staged: List[Dict[str, object]] = []
    for index, row in enumerate(rows, start=2):
        staged_row: Dict[str, object] = {"source_row": index}
        for header in PRODUCT_HEADERS:
            staged_row[header] = row.get(header, "")
        staged.append(staged_row)

    write_csv_rows(STAGED_PATH, ["source_row", *PRODUCT_HEADERS], staged)
    print(f"Rows staged: {len(staged)}")
    print(f"Staged file: {STAGED_PATH}")
    return STAGED_PATH


if __name__ == "__main__":
    stage_legacy_products()
