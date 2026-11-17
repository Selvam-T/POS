"""Live PRODUCT_CACHE consistency diagnostic."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Mapping, Sequence

from modules.db_operation.sqlite_runtime import get_db_path
from modules.menu.diagnostics.common import read_only_connection, timestamp
from modules.ui_utils.canonicalization import (
    canonicalize_product_code,
    canonicalize_title_text,
)


def _expected_cache_item(row: Mapping) -> tuple[str, float, str, str]:
    return (
        canonicalize_title_text(row.get("name")),
        float(row.get("selling_price") or 0.0),
        canonicalize_title_text(row.get("unit")) or "Each",
        str(row.get("category") or "").strip(),
    )


def compare_product_cache(
    database_rows: Sequence[Mapping],
    cache: Mapping[str, tuple],
) -> dict:
    """Compare database products with a supplied live cache mapping."""
    expected = {}
    duplicate_database_codes = []
    for row in database_rows:
        code = canonicalize_product_code(row.get("product_code"))
        if not code:
            continue
        if code in expected:
            duplicate_database_codes.append(code)
        expected[code] = _expected_cache_item(row)

    actual = {}
    invalid_cache_keys = []
    duplicate_normalized_cache_keys = []
    for raw_key, value in (cache or {}).items():
        raw_text = str(raw_key or "")
        code = canonicalize_product_code(raw_text)
        if not code or raw_text != code:
            invalid_cache_keys.append(raw_text)
        if not code:
            continue
        if code in actual:
            duplicate_normalized_cache_keys.append(code)
        actual[code] = tuple(value)

    expected_codes = set(expected)
    actual_codes = set(actual)
    missing = sorted(expected_codes - actual_codes)
    extra = sorted(actual_codes - expected_codes)
    mismatched = sorted(
        code
        for code in expected_codes & actual_codes
        if actual[code] != expected[code]
    )
    consistent = sorted(
        code
        for code in expected_codes & actual_codes
        if actual[code] == expected[code]
    )

    field_names = ("name", "selling_price", "unit", "category")
    mismatch_details = {}
    for code in mismatched:
        expected_item = expected[code]
        actual_item = actual[code]
        differing_fields = [
            field
            for index, field in enumerate(field_names)
            if index >= len(actual_item) or actual_item[index] != expected_item[index]
        ]
        if len(actual_item) != len(expected_item):
            differing_fields.append("record_shape")
        mismatch_details[code] = {
            "fields": differing_fields,
            "expected": expected_item,
            "actual": actual_item,
        }

    inconsistent_total = (
        len(missing)
        + len(extra)
        + len(mismatched)
        + len(invalid_cache_keys)
        + len(duplicate_normalized_cache_keys)
        + len(duplicate_database_codes)
    )
    return {
        "database_total": len(expected),
        "cache_total": len(cache or {}),
        "consistent_total": len(consistent),
        "inconsistent_total": inconsistent_total,
        "missing_from_cache": missing,
        "extra_in_cache": extra,
        "value_mismatches": mismatched,
        "mismatch_details": mismatch_details,
        "invalid_cache_keys": sorted(invalid_cache_keys),
        "duplicate_normalized_cache_keys": sorted(
            set(duplicate_normalized_cache_keys)
        ),
        "duplicate_database_codes": sorted(set(duplicate_database_codes)),
        "expected": expected,
        "actual": actual,
    }


def _read_product_rows(database_path: str) -> list[dict]:
    conn = read_only_connection(database_path)
    try:
        rows = conn.execute(
            """
            SELECT p.product_code, p.name, p.selling_price, p.unit,
                   c.name AS category
              FROM Product_list AS p
              JOIN Category AS c ON c.category_id = p.category_id
             ORDER BY p.product_code
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def run_product_cache_diagnostics(
    cache: Mapping[str, tuple],
    *,
    db_path: str | None = None,
    database_rows: Sequence[Mapping] | None = None,
) -> dict:
    """Compare the supplied live cache with Product_list without reloading it."""
    started_at = timestamp()
    started_clock = perf_counter()
    result = {
        "check": "Product cache consistency",
        "status": "FAIL",
        "started_at": started_at,
        "completed_at": None,
        "duration_seconds": 0.0,
        "database_path": "",
        "database_total": 0,
        "cache_total": len(cache or {}),
        "consistent_total": 0,
        "inconsistent_total": 0,
        "missing_from_cache": [],
        "extra_in_cache": [],
        "value_mismatches": [],
        "mismatch_details": {},
        "invalid_cache_keys": [],
        "duplicate_normalized_cache_keys": [],
        "duplicate_database_codes": [],
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

        comparison = compare_product_cache(rows, cache)
        for key in (
            "database_total",
            "cache_total",
            "consistent_total",
            "inconsistent_total",
            "missing_from_cache",
            "extra_in_cache",
            "value_mismatches",
            "mismatch_details",
            "invalid_cache_keys",
            "duplicate_normalized_cache_keys",
            "duplicate_database_codes",
        ):
            result[key] = comparison[key]

        issue_specs = (
            ("missing_from_cache", "Products missing from cache"),
            ("extra_in_cache", "Cache entries missing from database"),
            ("value_mismatches", "Cache value mismatches"),
            ("invalid_cache_keys", "Invalid cache keys"),
            (
                "duplicate_normalized_cache_keys",
                "Duplicate normalized cache keys",
            ),
            ("duplicate_database_codes", "Duplicate normalized database codes"),
        )
        for key, label in issue_specs:
            if result[key]:
                result["issues"].append(f"{label}: {len(result[key])}")

        result["status"] = "PASS" if not result["issues"] else "FAIL"
    except Exception as exc:
        result["issues"].append(
            f"{type(exc).__name__}: "
            f"{str(exc) or 'Product cache diagnostic failed'}"
        )
    finally:
        result["completed_at"] = timestamp()
        result["duration_seconds"] = round(perf_counter() - started_clock, 3)

    return result
