"""Category master-data and product relationship diagnostic."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from time import perf_counter
from typing import Mapping, Sequence

from modules.db_operation.sqlite_runtime import get_db_path
from modules.menu.diagnostics.common import read_only_connection, timestamp
from modules.ui_utils.canonicalization import canonicalize_product_code


REQUIRED_CATEGORY_NAMES = ("Other", "Vegetable")
_FIXED_VEGETABLE_PATTERN = re.compile(r"^VEG(?:0[1-9]|1[0-6])$")


def normalize_category_name(value: object) -> str:
    """Normalize case and whitespace while preserving punctuation."""
    return " ".join(str(value or "").split()).casefold()


def analyze_category_integrity(
    category_rows: Sequence[Mapping],
    product_rows: Sequence[Mapping],
) -> dict:
    """Analyze category names and Product_list category relationships."""
    categories_by_id = {}
    categories_by_name: dict[str, list[dict]] = defaultdict(list)
    blank_categories = []

    for row in category_rows:
        category_id = row.get("category_id")
        name = str(row.get("name") or "")
        normalized_name = normalize_category_name(name)
        category = {
            "category_id": category_id,
            "name": name.strip(),
            "is_protected": bool(row.get("is_protected")),
        }
        categories_by_id[category_id] = category
        if not normalized_name:
            blank_categories.append(category)
        else:
            categories_by_name[normalized_name].append(category)

    duplicate_name_groups = []
    for normalized_name, categories in categories_by_name.items():
        if len(categories) < 2:
            continue
        duplicate_name_groups.append(
            {
                "normalized_name": normalized_name,
                "category_count": len(categories),
                "categories": sorted(
                    categories,
                    key=lambda item: (
                        item["name"].casefold(),
                        str(item["category_id"]),
                    ),
                ),
            }
        )
    duplicate_name_groups.sort(key=lambda item: item["normalized_name"])

    required_categories = {}
    missing_required_categories = []
    duplicate_required_categories = []
    for required_name in REQUIRED_CATEGORY_NAMES:
        matches = categories_by_name.get(
            normalize_category_name(required_name),
            [],
        )
        required_categories[required_name] = matches
        if not matches:
            missing_required_categories.append(required_name)
        elif len(matches) > 1:
            duplicate_required_categories.append(required_name)

    products_without_category_id = []
    products_with_missing_category_id = []
    fixed_vegetables_wrong_category = []
    for row in product_rows:
        code = canonicalize_product_code(row.get("product_code"))
        name = str(row.get("name") or "").strip()
        category_id = row.get("category_id")
        detail = {
            "product_code": code,
            "product_name": name,
            "category_id": category_id,
        }
        if category_id is None:
            products_without_category_id.append(detail)
        elif category_id not in categories_by_id:
            products_with_missing_category_id.append(detail)

        if _FIXED_VEGETABLE_PATTERN.fullmatch(code):
            category = categories_by_id.get(category_id)
            category_name = category.get("name") if category else ""
            if normalize_category_name(category_name) != "vegetable":
                fixed_vegetables_wrong_category.append(
                    {**detail, "category_name": category_name}
                )

    sort_key = lambda item: (item["product_code"], item["product_name"])
    return {
        "category_total": len(category_rows),
        "product_total": len(product_rows),
        "blank_category_total": len(blank_categories),
        "blank_categories": blank_categories,
        "duplicate_name_group_total": len(duplicate_name_groups),
        "duplicate_name_groups": duplicate_name_groups,
        "required_categories": required_categories,
        "missing_required_categories": missing_required_categories,
        "duplicate_required_categories": duplicate_required_categories,
        "products_without_category_id_total": len(products_without_category_id),
        "products_without_category_id": sorted(
            products_without_category_id, key=sort_key
        ),
        "products_with_missing_category_id_total": len(
            products_with_missing_category_id
        ),
        "products_with_missing_category_id": sorted(
            products_with_missing_category_id, key=sort_key
        ),
        "fixed_vegetables_wrong_category_total": len(
            fixed_vegetables_wrong_category
        ),
        "fixed_vegetables_wrong_category": sorted(
            fixed_vegetables_wrong_category, key=sort_key
        ),
    }


def _read_category_and_product_rows(
    database_path: str,
) -> tuple[list[dict], list[dict]]:
    conn = read_only_connection(database_path)
    try:
        categories = [
            dict(row)
            for row in conn.execute(
                "SELECT category_id, name, is_protected "
                "FROM Category ORDER BY category_id"
            ).fetchall()
        ]
        products = [
            dict(row)
            for row in conn.execute(
                "SELECT product_code, name, category_id "
                "FROM Product_list ORDER BY product_code"
            ).fetchall()
        ]
        return categories, products
    finally:
        conn.close()


def run_category_integrity_diagnostics(
    *,
    db_path: str | None = None,
    category_rows: Sequence[Mapping] | None = None,
    product_rows: Sequence[Mapping] | None = None,
) -> dict:
    """Run category integrity checks without modifying the database."""
    started_clock = perf_counter()
    result = {
        "check": "Category integrity",
        "status": "FAIL",
        "started_at": timestamp(),
        "completed_at": None,
        "duration_seconds": 0.0,
        "database_path": "",
        "category_total": 0,
        "product_total": 0,
        "blank_category_total": 0,
        "blank_categories": [],
        "duplicate_name_group_total": 0,
        "duplicate_name_groups": [],
        "required_categories": {},
        "missing_required_categories": [],
        "duplicate_required_categories": [],
        "products_without_category_id_total": 0,
        "products_without_category_id": [],
        "products_with_missing_category_id_total": 0,
        "products_with_missing_category_id": [],
        "fixed_vegetables_wrong_category_total": 0,
        "fixed_vegetables_wrong_category": [],
        "issues": [],
    }
    try:
        if category_rows is None or product_rows is None:
            database_path = str(Path(db_path or get_db_path()).resolve())
            result["database_path"] = database_path
            categories, products = _read_category_and_product_rows(
                database_path
            )
        else:
            categories = list(category_rows)
            products = list(product_rows)
            if db_path:
                result["database_path"] = str(Path(db_path).resolve())

        result.update(analyze_category_integrity(categories, products))
        issue_specs = (
            ("blank_categories", "Blank category names"),
            ("duplicate_name_groups", "Duplicate normalized category-name groups"),
            ("missing_required_categories", "Missing required categories"),
            (
                "duplicate_required_categories",
                "Required categories with multiple matches",
            ),
            ("products_without_category_id", "Products with no category_id"),
            (
                "products_with_missing_category_id",
                "Products referencing an ID that does not exist in the "
                "Category table",
            ),
            (
                "fixed_vegetables_wrong_category",
                "Fixed vegetable products not assigned to Vegetable",
            ),
        )
        for key, label in issue_specs:
            if result[key]:
                result["issues"].append(f"{label}: {len(result[key])}")
        result["status"] = "WARNING" if result["issues"] else "PASS"
    except Exception as exc:
        result["issues"].append(
            f"{type(exc).__name__}: "
            f"{str(exc) or 'Category integrity diagnostic failed'}"
        )
    finally:
        result["completed_at"] = timestamp()
        result["duration_seconds"] = round(perf_counter() - started_clock, 3)
    return result
