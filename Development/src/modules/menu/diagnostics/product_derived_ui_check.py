"""Product search-list and fixed vegetable-slot diagnostic."""

from __future__ import annotations

import re
from collections import Counter
from time import perf_counter
from typing import Mapping

from modules.menu.diagnostics.common import timestamp
from modules.ui_utils.canonicalization import canonicalize_product_code
from modules.ui_utils.product_choices import (
    build_product_name_choices,
    normalize_product_choice_name,
)


PRODUCT_NAME_CONSUMERS = (
    "Manual entry",
    "Refund",
    "Receipt",
    "Product menu",
)
EXPECTED_VEGETABLE_CODES = tuple(f"VEG{index:02d}" for index in range(1, 17))
_RESERVED_VEGETABLE_PATTERN = re.compile(r"^VEG-?\d+$", re.IGNORECASE)


def analyze_product_derived_ui(product_cache: Mapping | None) -> dict:
    """Analyze cache-derived names and fixed vegetable slots without UI access."""
    cache = product_cache or {}
    choices = build_product_name_choices(cache)

    source_names = []
    invalid_name_codes = []
    malformed_cache_codes = []
    for raw_code, record in cache.items():
        code = canonicalize_product_code(raw_code)
        if not isinstance(record, (tuple, list)) or not record:
            malformed_cache_codes.append(code)
            continue
        try:
            name = normalize_product_choice_name(record[0])
        except Exception:
            malformed_cache_codes.append(code)
            continue
        if name:
            source_names.append(name)
        else:
            invalid_name_codes.append(code)

    expected_counts = Counter(source_names)
    actual_counts = Counter(choices)
    lookup_name_counts = Counter(
        normalize_product_choice_name(name).casefold()
        for name in source_names
    )
    duplicate_source_name_total = sum(
        count - 1 for count in lookup_name_counts.values() if count > 1
    )

    cache_by_code = {
        canonicalize_product_code(code): record
        for code, record in cache.items()
        if canonicalize_product_code(code)
    }
    expected_vegetable_set = set(EXPECTED_VEGETABLE_CODES)
    reserved_codes = {
        code
        for code in cache_by_code
        if _RESERVED_VEGETABLE_PATTERN.fullmatch(code)
    }
    missing_vegetable_codes = sorted(expected_vegetable_set - reserved_codes)
    unexpected_vegetable_codes = sorted(reserved_codes - expected_vegetable_set)

    invalid_vegetable_records = []
    for code in EXPECTED_VEGETABLE_CODES:
        if code not in cache_by_code:
            continue
        record = cache_by_code[code]
        problems = []
        if not isinstance(record, (tuple, list)) or len(record) < 4:
            problems.append("record shape")
        else:
            if not normalize_product_choice_name(record[0]):
                problems.append("name")
            try:
                if float(record[1]) <= 0:
                    problems.append("selling price")
            except (TypeError, ValueError):
                problems.append("selling price")
            if not str(record[2] or "").strip():
                problems.append("unit")
            if str(record[3] or "").strip().casefold() != "vegetable":
                problems.append("category")
        if problems:
            invalid_vegetable_records.append(
                {"product_code": code, "invalid_fields": problems}
            )

    return {
        "cache_total": len(cache),
        "consumer_names": list(PRODUCT_NAME_CONSUMERS),
        "consumer_total": len(PRODUCT_NAME_CONSUMERS),
        "source_name_total": len(source_names),
        "expected_choice_total": len(source_names),
        "choice_total": len(choices),
        "choices": choices,
        "missing_choice_names": sorted(
            (expected_counts - actual_counts).elements(),
            key=str.casefold,
        ),
        "extra_choice_names": sorted(
            (actual_counts - expected_counts).elements(),
            key=str.casefold,
        ),
        "duplicate_source_name_total": duplicate_source_name_total,
        "choices_sorted": choices == sorted(choices, key=str.casefold),
        "invalid_name_codes": sorted(invalid_name_codes),
        "malformed_cache_codes": sorted(malformed_cache_codes),
        "expected_vegetable_total": len(EXPECTED_VEGETABLE_CODES),
        "available_vegetable_total": len(
            expected_vegetable_set & reserved_codes
        ),
        "missing_vegetable_codes": missing_vegetable_codes,
        "unexpected_vegetable_codes": unexpected_vegetable_codes,
        "invalid_vegetable_records": invalid_vegetable_records,
    }


def run_product_derived_ui_diagnostics(product_cache: Mapping | None) -> dict:
    """Validate cache-derived product choices and reserved vegetable slots."""
    started_clock = perf_counter()
    result = {
        "check": "Product search lists and vegetable slots",
        "status": "FAIL",
        "started_at": timestamp(),
        "completed_at": None,
        "duration_seconds": 0.0,
        "cache_total": len(product_cache or {}),
        "consumer_names": list(PRODUCT_NAME_CONSUMERS),
        "consumer_total": len(PRODUCT_NAME_CONSUMERS),
        "source_name_total": 0,
        "expected_choice_total": 0,
        "choice_total": 0,
        "choices": [],
        "missing_choice_names": [],
        "extra_choice_names": [],
        "duplicate_source_name_total": 0,
        "choices_sorted": False,
        "invalid_name_codes": [],
        "malformed_cache_codes": [],
        "expected_vegetable_total": len(EXPECTED_VEGETABLE_CODES),
        "available_vegetable_total": 0,
        "missing_vegetable_codes": [],
        "unexpected_vegetable_codes": [],
        "invalid_vegetable_records": [],
        "limitations": [
            "This check validates the shared cache-derived data pipeline.",
            "It does not inspect unopened dialog widgets or confirm that an "
            "already-open widget model refreshed after a product change.",
        ],
        "issues": [],
    }
    try:
        result.update(analyze_product_derived_ui(product_cache))
        issue_specs = (
            ("missing_choice_names", "Product names missing from choices"),
            ("extra_choice_names", "Unexpected product-name choices"),
            ("invalid_name_codes", "Cache products with empty names"),
            ("malformed_cache_codes", "Malformed cache records"),
            (
                "unexpected_vegetable_codes",
                "Reserved vegetable codes outside VEG01-VEG16",
            ),
            ("invalid_vegetable_records", "Invalid fixed vegetable records"),
        )
        if not result["choices_sorted"]:
            result["issues"].append("Product-name choices are not sorted")
        for key, label in issue_specs:
            if result[key]:
                result["issues"].append(f"{label}: {len(result[key])}")
        result["status"] = "WARNING" if result["issues"] else "PASS"
    except Exception as exc:
        result["issues"].append(
            f"{type(exc).__name__}: "
            f"{str(exc) or 'Product-derived UI diagnostic failed'}"
        )
    finally:
        result["completed_at"] = timestamp()
        result["duration_seconds"] = round(perf_counter() - started_clock, 3)
    return result
