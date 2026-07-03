"""Validate staged product rows and produce cleaned/rejected reports."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from admin_lib import DATA_DIR, clean_text, normalize_unit, now_stamp, read_csv_rows, write_csv_rows, print_header
from migration.stage_legacy_products import PRODUCT_HEADERS, STAGED_PATH


CLEANED_PATH = DATA_DIR / "cleaned_products.csv"
REJECTED_PATH = DATA_DIR / "rejected_products.csv"
VALIDATION_SUMMARY_PATH = DATA_DIR / "product_validation_summary.txt"

APP_LIMITS = {
    "product_code": (2, 14),
    "name": (4, 40),
    "supplier": (0, 15),
    "category": (0, 25),
}


def _to_float(value: str) -> Tuple[bool, float | None]:
    text = clean_text(value)
    if not text:
        return False, None
    try:
        return True, float(text)
    except ValueError:
        return False, None


def validate_legacy_products(staged_path: Path = STAGED_PATH) -> tuple[Path, Path]:
    print_header("Validate Legacy Products")
    if not staged_path.exists():
        raise FileNotFoundError(f"Staged file not found: {staged_path}")

    rows = read_csv_rows(staged_path)
    seen_codes: set[str] = set()
    cleaned: List[Dict[str, object]] = []
    rejected: List[Dict[str, object]] = []
    warnings: Counter[str] = Counter()
    reject_reasons: Counter[str] = Counter()

    for row in rows:
        reasons: List[str] = []
        row_warnings: List[str] = []

        source_row = clean_text(row.get("source_row"))
        product_code = clean_text(row.get("product_code"))
        name = clean_text(row.get("name"))
        category = clean_text(row.get("category")) or "Other"
        supplier = clean_text(row.get("supplier"))
        unit = normalize_unit(row.get("unit"))
        last_updated = clean_text(row.get("last_updated")) or now_stamp()

        if not product_code:
            reasons.append("blank product_code")
        elif len(product_code) < APP_LIMITS["product_code"][0]:
            reasons.append("product_code shorter than 2")
        elif len(product_code) > APP_LIMITS["product_code"][1]:
            reasons.append("product_code longer than 14")

        code_key = product_code.upper()
        if product_code and code_key in seen_codes:
            reasons.append("duplicate product_code")
        elif product_code:
            seen_codes.add(code_key)

        if not name:
            reasons.append("blank name")
        elif len(name) > APP_LIMITS["name"][1]:
            row_warnings.append("name longer than POS input max 40")

        ok_price, selling_price = _to_float(str(row.get("selling_price", "")))
        if not ok_price or selling_price is None:
            reasons.append("invalid selling_price")
        elif selling_price < 0:
            reasons.append("negative selling_price")

        cost_text = clean_text(row.get("cost_price"))
        cost_price: float | None = None
        if cost_text:
            ok_cost, parsed_cost = _to_float(cost_text)
            if ok_cost:
                cost_price = parsed_cost
            else:
                row_warnings.append("invalid cost_price set to blank")

        if len(category) > APP_LIMITS["category"][1]:
            row_warnings.append("category longer than POS input max 25")
        if supplier and len(supplier) > APP_LIMITS["supplier"][1]:
            row_warnings.append("supplier longer than POS input max 15")

        if reasons:
            for reason in reasons:
                reject_reasons[reason] += 1
            rejected.append(
                {
                    "source_row": source_row,
                    **{h: row.get(h, "") for h in PRODUCT_HEADERS},
                    "reasons": "; ".join(reasons),
                }
            )
            continue

        for warning in row_warnings:
            warnings[warning] += 1

        cleaned.append(
            {
                "source_row": source_row,
                "product_code": product_code,
                "name": name,
                "category": category,
                "supplier": supplier,
                "selling_price": selling_price,
                "cost_price": "" if cost_price is None else cost_price,
                "unit": unit,
                "last_updated": last_updated,
                "warnings": "; ".join(row_warnings),
            }
        )

    cleaned_fields = ["source_row", *PRODUCT_HEADERS, "warnings"]
    rejected_fields = ["source_row", *PRODUCT_HEADERS, "reasons"]
    write_csv_rows(CLEANED_PATH, cleaned_fields, cleaned)
    write_csv_rows(REJECTED_PATH, rejected_fields, rejected)

    summary_lines = [
        "Product validation summary",
        f"Rows staged: {len(rows)}",
        f"Rows valid: {len(cleaned)}",
        f"Rows rejected: {len(rejected)}",
        "",
        "Rejected reasons:",
    ]
    summary_lines.extend(f"- {reason}: {count}" for reason, count in sorted(reject_reasons.items()))
    summary_lines.extend(["", "Warnings:"])
    summary_lines.extend(f"- {warning}: {count}" for warning, count in sorted(warnings.items()))
    VALIDATION_SUMMARY_PATH.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(f"Rows valid: {len(cleaned)}")
    print(f"Rows rejected: {len(rejected)}")
    print(f"Validation summary: {VALIDATION_SUMMARY_PATH}")
    if rejected:
        print(f"Rejected rows: {REJECTED_PATH}")
        raise ValueError("Product validation failed. Fix data/products.csv and rerun setup.")

    return CLEANED_PATH, REJECTED_PATH


if __name__ == "__main__":
    validate_legacy_products()
