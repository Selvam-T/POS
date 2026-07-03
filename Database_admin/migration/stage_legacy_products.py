"""Stage raw legacy product CSV rows for validation."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import products_csv_path, read_csv_rows, print_header


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

def stage_legacy_products(csv_path: Path | None = None) -> List[Dict[str, object]]:
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

    print(f"Rows staged: {len(staged)}")
    return staged


if __name__ == "__main__":
    stage_legacy_products()
