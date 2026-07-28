"""Tail-truncated numeric product-code diagnostic."""

from __future__ import annotations

import re
from pathlib import Path
from time import perf_counter
from typing import Mapping, Sequence

from modules.db_operation.sqlite_runtime import get_db_path
from modules.menu.diagnostics.common import read_only_connection, timestamp
from modules.ui_utils.canonicalization import canonicalize_product_code


MIN_BARCODE_LENGTH = 5
MAX_MISSING_TAIL_CHARACTERS = 3
VEGETABLE_CODE_PATTERN = re.compile(r"^VEG-?\d{2}$", re.IGNORECASE)


def _tail_candidate(
    shorter: str,
    longer: str,
    names: Mapping[str, str],
) -> dict:
    missing_count = len(longer) - len(shorter)
    confidence = "HIGH" if missing_count == 1 else "LOWER"
    return {
        "code_1": shorter,
        "product_name_1": names.get(shorter, ""),
        "code_2": longer,
        "product_name_2": names.get(longer, ""),
        "shorter_code": shorter,
        "longer_code": longer,
        "classification": "trailing_truncation",
        "missing_tail_characters": missing_count,
        "confidence": confidence,
        "prefix_coverage_percent": round(
            100.0 * len(shorter) / len(longer),
            2,
        ),
    }


def find_suspicious_product_codes(
    database_rows: Sequence[Mapping],
    *,
    minimum_length: int = MIN_BARCODE_LENGTH,
    maximum_missing_tail_characters: int = MAX_MISSING_TAIL_CHARACTERS,
) -> dict:
    """Find codes that are exact prefixes of longer numeric product codes.

    This models premature scanner termination. It deliberately does not flag
    same-length similarity, middle deletions, substitutions, or transpositions.
    """
    names: dict[str, str] = {}
    duplicate_codes: list[str] = []
    ignored_short_codes: list[str] = []
    ignored_vegetable_codes: list[str] = []
    ignored_other_codes: list[str] = []

    for row in database_rows:
        code = canonicalize_product_code(row.get("product_code"))
        if not code:
            continue
        if code in names:
            duplicate_codes.append(code)
            continue
        names[code] = str(row.get("name") or "").strip()

    eligible: set[str] = set()
    for code in names:
        if VEGETABLE_CODE_PATTERN.fullmatch(code):
            ignored_vegetable_codes.append(code)
        elif len(code) < minimum_length:
            ignored_short_codes.append(code)
        elif not (code.isascii() and code.isdecimal()):
            ignored_other_codes.append(code)
        else:
            eligible.add(code)

    candidates = []
    for longer in eligible:
        for missing_count in range(1, maximum_missing_tail_characters + 1):
            if len(longer) - missing_count < minimum_length:
                continue
            shorter = longer[:-missing_count]
            if shorter in eligible:
                candidates.append(_tail_candidate(shorter, longer, names))

    candidates.sort(
        key=lambda item: (
            item["missing_tail_characters"],
            -item["prefix_coverage_percent"],
            item["shorter_code"],
            item["longer_code"],
        )
    )
    return {
        "database_total": len(names),
        "eligible_numeric_total": len(eligible),
        "ignored_short_code_total": len(ignored_short_codes),
        "ignored_short_codes": sorted(ignored_short_codes),
        "ignored_vegetable_code_total": len(ignored_vegetable_codes),
        "ignored_vegetable_codes": sorted(ignored_vegetable_codes),
        "ignored_other_code_total": len(ignored_other_codes),
        "ignored_other_codes": sorted(ignored_other_codes),
        "duplicate_database_codes": sorted(set(duplicate_codes)),
        "candidate_total": len(candidates),
        "candidates": candidates,
    }


def _read_product_rows(database_path: str) -> list[dict]:
    conn = read_only_connection(database_path)
    try:
        rows = conn.execute(
            """
            SELECT product_code, name
              FROM Product_list
             ORDER BY product_code
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def run_product_code_diagnostics(
    *,
    db_path: str | None = None,
    database_rows: Sequence[Mapping] | None = None,
) -> dict:
    """Run the tail-truncated product-code check against Product_list."""
    started_clock = perf_counter()
    result = {
        "check": "Suspicious or incomplete product codes",
        "status": "FAIL",
        "started_at": timestamp(),
        "completed_at": None,
        "duration_seconds": 0.0,
        "database_path": "",
        "minimum_barcode_length": MIN_BARCODE_LENGTH,
        "maximum_missing_tail_characters": MAX_MISSING_TAIL_CHARACTERS,
        "database_total": 0,
        "eligible_numeric_total": 0,
        "ignored_short_code_total": 0,
        "ignored_short_codes": [],
        "ignored_vegetable_code_total": 0,
        "ignored_vegetable_codes": [],
        "ignored_other_code_total": 0,
        "ignored_other_codes": [],
        "duplicate_database_codes": [],
        "candidate_total": 0,
        "candidates": [],
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

        comparison = find_suspicious_product_codes(rows)
        result.update(comparison)
        if result["duplicate_database_codes"]:
            result["issues"].append(
                "Duplicate normalized database product codes: "
                f"{len(result['duplicate_database_codes'])}"
            )
        if result["candidate_total"]:
            result["issues"].append(
                "Possible tail-truncated product-code pairs requiring review: "
                f"{result['candidate_total']}"
            )
        result["status"] = "WARNING" if result["issues"] else "PASS"
    except Exception as exc:
        result["issues"].append(
            f"{type(exc).__name__}: "
            f"{str(exc) or 'Product-code diagnostic failed'}"
        )
    finally:
        result["completed_at"] = timestamp()
        result["duration_seconds"] = round(perf_counter() - started_clock, 3)
    return result
