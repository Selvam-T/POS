"""Text formatting for completed POS diagnostic results."""

from __future__ import annotations

from datetime import datetime
from typing import Mapping


def _append_database_report(lines: list[str], database: Mapping) -> None:
    status = str(database.get("status") or "NOT RUN")
    lines.extend(
        [
            "DATABASE COUNTS AND SQLITE INTEGRITY",
            "-" * 64,
            f"Status: {status}",
            f"Started: {database.get('started_at') or 'N/A'}",
            f"Completed: {database.get('completed_at') or 'N/A'}",
            f"Duration: {float(database.get('duration_seconds') or 0.0):.3f} seconds",
            f"Database path: {database.get('database_path') or 'N/A'}",
            f"Database size: {database.get('database_size_bytes') if database.get('database_size_bytes') is not None else 'N/A'} bytes",
            f"Connection mode: {'Read-only' if database.get('read_only') else 'Unknown'}",
            "Foreign-key enforcement: "
            + ("Enabled" if database.get("foreign_keys_enabled") else "Disabled"),
            "",
            "Required tables:",
        ]
    )

    missing_keys = {
        str(name).casefold() for name in (database.get("missing_tables") or [])
    }
    required_tables = list(database.get("required_tables") or [])
    lines.extend(
        [
            f"- {table}: "
            + ("MISSING" if str(table).casefold() in missing_keys else "Present")
            for table in required_tables
        ]
        or ["- N/A"]
    )
    lines.extend(["", "Table counts:"])
    table_counts = dict(database.get("table_counts") or {})
    lines.extend(
        [f"- {table}: {count}" for table, count in table_counts.items()]
        or ["- N/A"]
    )

    quick_check = list(database.get("quick_check") or [])
    lines.extend(
        [
            "",
            "SQLite quick_check:",
            *([f"- {item}" for item in quick_check] or ["- No result"]),
            "",
            "Foreign-key violations:",
        ]
    )
    violations = list(database.get("foreign_key_violations") or [])
    if violations:
        for violation in violations:
            lines.append(
                "- "
                f"table={violation.get('table')}, "
                f"rowid={violation.get('rowid')}, "
                f"parent={violation.get('parent')}, "
                f"foreign_key_id={violation.get('foreign_key_id')}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "Issues:"])
    lines.extend(
        [f"- {issue}" for issue in (database.get("issues") or [])]
        or ["- None"]
    )
    lines.append("")


def _append_product_cache_report(lines: list[str], cache: Mapping) -> None:
    lines.extend(
        [
            "PRODUCT CACHE CONSISTENCY",
            "-" * 64,
            f"Status: {cache.get('status') or 'NOT RUN'}",
            f"Started: {cache.get('started_at') or 'N/A'}",
            f"Completed: {cache.get('completed_at') or 'N/A'}",
            f"Duration: {float(cache.get('duration_seconds') or 0.0):.3f} seconds",
            f"Database path: {cache.get('database_path') or 'N/A'}",
            f"Product_list total: {cache.get('database_total', 0)}",
            f"Live PRODUCT_CACHE total: {cache.get('cache_total', 0)}",
            f"Consistent entries: {cache.get('consistent_total', 0)}",
            f"Inconsistent entries: {cache.get('inconsistent_total', 0)}",
            "",
            "Missing from cache:",
            *(
                [
                    f"- {code}"
                    for code in (cache.get("missing_from_cache") or [])
                ]
                or ["- None"]
            ),
            "",
            "Extra in cache:",
            *(
                [f"- {code}" for code in (cache.get("extra_in_cache") or [])]
                or ["- None"]
            ),
            "",
            "Value mismatches:",
        ]
    )
    mismatches = list(cache.get("value_mismatches") or [])
    details = dict(cache.get("mismatch_details") or {})
    if mismatches:
        for code in mismatches:
            detail = details.get(code) or {}
            lines.append(
                f"- {code}: fields={', '.join(detail.get('fields') or [])}; "
                f"DB={detail.get('expected')!r}; cache={detail.get('actual')!r}"
            )
    else:
        lines.append("- None")

    for heading, key in (
        ("Invalid cache keys", "invalid_cache_keys"),
        ("Duplicate normalized cache keys", "duplicate_normalized_cache_keys"),
        ("Duplicate normalized database codes", "duplicate_database_codes"),
    ):
        lines.extend(["", f"{heading}:"])
        lines.extend(
            [f"- {value!r}" for value in (cache.get(key) or [])]
            or ["- None"]
        )
    lines.extend(["", "Issues:"])
    lines.extend(
        [f"- {issue}" for issue in (cache.get("issues") or [])]
        or ["- None"]
    )
    lines.append("")


def format_diagnostic_report(
    diagnostic_results: Mapping[str, Mapping],
    *,
    generated_at: datetime | None = None,
) -> str:
    """Format selected, completed diagnostic results as a UTF-8 report."""
    generated = generated_at or datetime.now().astimezone()
    database = dict((diagnostic_results or {}).get("database") or {})
    product_cache = dict((diagnostic_results or {}).get("product_cache") or {})
    completed = [item for item in (database, product_cache) if item]
    statuses = [str(item.get("status") or "FAIL") for item in completed]
    overall_status = (
        "FAIL" if "FAIL" in statuses else ("PASS" if statuses else "NOT RUN")
    )

    lines = [
        "SELVAM POS DIAGNOSTIC REPORT",
        "=" * 64,
        f"Generated: {generated.isoformat(timespec='seconds')}",
        f"Overall status: {overall_status}",
        "",
        "SELECTED CHECKS",
        "-" * 64,
    ]
    selected_number = 1
    if database:
        lines.append(f"{selected_number}. Database counts and SQLite integrity")
        selected_number += 1
    if product_cache:
        lines.append(f"{selected_number}. Product cache consistency")
    lines.append("")
    if database:
        _append_database_report(lines, database)
    if product_cache:
        _append_product_cache_report(lines, product_cache)

    lines.extend(["", "=" * 64, "END OF REPORT", ""])
    return "\n".join(lines)
