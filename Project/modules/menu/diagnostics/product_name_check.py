"""Duplicate product-name diagnostic."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from time import perf_counter
from typing import Mapping, Sequence

from modules.db_operation.sqlite_runtime import get_db_path
from modules.menu.diagnostics.common import read_only_connection, timestamp
from modules.ui_utils.canonicalization import canonicalize_product_code


def normalize_product_name_for_duplicate_check(value: object) -> str:
    """Normalize case and repeated whitespace while preserving punctuation."""
    return " ".join(str(value or "").split()).casefold()


def find_duplicate_product_names(database_rows: Sequence[Mapping]) -> dict:
    """Group product records whose names match after limited normalization."""
    groups: dict[str, list[dict]] = defaultdict(list)
    empty_name_codes: list[str] = []

    for row in database_rows:
        code = canonicalize_product_code(row.get("product_code"))
        original_name = str(row.get("name") or "")
        normalized_name = normalize_product_name_for_duplicate_check(
            original_name
        )
        if not normalized_name:
            empty_name_codes.append(code)
            continue
        groups[normalized_name].append(
            {
                "product_code": code,
                "product_name": original_name.strip(),
            }
        )

    duplicate_groups = []
    for normalized_name, products in groups.items():
        if len(products) < 2:
            continue
        ordered_products = sorted(
            products,
            key=lambda item: (
                item["product_name"].casefold(),
                item["product_code"],
            ),
        )
        duplicate_groups.append(
            {
                "normalized_name": normalized_name,
                "product_count": len(ordered_products),
                "products": ordered_products,
            }
        )
    duplicate_groups.sort(
        key=lambda group: (
            -group["product_count"],
            group["normalized_name"],
        )
    )
    return {
        "database_total": len(database_rows),
        "names_checked_total": sum(len(products) for products in groups.values()),
        "empty_name_total": len(empty_name_codes),
        "empty_name_codes": sorted(empty_name_codes),
        "duplicate_group_total": len(duplicate_groups),
        "duplicate_product_total": sum(
            group["product_count"] for group in duplicate_groups
        ),
        "duplicate_groups": duplicate_groups,
    }


def _read_product_rows(database_path: str) -> list[dict]:
    conn = read_only_connection(database_path)
    try:
        rows = conn.execute(
            """
            SELECT product_code, name
              FROM Product_list
             ORDER BY name, product_code
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def run_product_name_diagnostics(
    *,
    db_path: str | None = None,
    database_rows: Sequence[Mapping] | None = None,
) -> dict:
    """Run duplicate-name detection against Product_list."""
    started_clock = perf_counter()
    result = {
        "check": "Duplicate product names",
        "status": "FAIL",
        "started_at": timestamp(),
        "completed_at": None,
        "duration_seconds": 0.0,
        "database_path": "",
        "database_total": 0,
        "names_checked_total": 0,
        "empty_name_total": 0,
        "empty_name_codes": [],
        "duplicate_group_total": 0,
        "duplicate_product_total": 0,
        "duplicate_groups": [],
        "issues": [],
    }
    try:
        if database_rows is None:
            database_path = str(Path(db_path or get_db_path()).resolve())
            result["database_path"] = database_path
            rows = _read_product_rows(database_path)
        else:
            rows = list(database_rows)
            if db_path:
                result["database_path"] = str(Path(db_path).resolve())

        comparison = find_duplicate_product_names(rows)
        result.update(comparison)
        if result["duplicate_group_total"]:
            result["issues"].append(
                "Duplicate product-name groups requiring review: "
                f"{result['duplicate_group_total']}"
            )
        result["status"] = "WARNING" if result["issues"] else "PASS"
    except Exception as exc:
        result["issues"].append(
            f"{type(exc).__name__}: "
            f"{str(exc) or 'Duplicate product-name diagnostic failed'}"
        )
    finally:
        result["completed_at"] = timestamp()
        result["duration_seconds"] = round(perf_counter() - started_clock, 3)
    return result
