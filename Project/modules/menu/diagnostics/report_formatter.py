"""Text formatting for completed POS diagnostic results."""

from __future__ import annotations

from datetime import datetime
from typing import Mapping


def _format_bytes(value) -> str:
    if value is None:
        return "Unavailable"
    amount = float(value)
    units = ("bytes", "KB", "MB", "GB", "TB")
    unit = units[0]
    for unit in units:
        if abs(amount) < 1024.0 or unit == units[-1]:
            break
        amount /= 1024.0
    return f"{amount:.2f} {unit}"


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


def _append_product_code_report(lines: list[str], codes: Mapping) -> None:
    candidates = list(codes.get("candidates") or [])
    high_confidence_total = sum(
        1
        for candidate in candidates
        if str(candidate.get("confidence") or "").upper() == "HIGH"
    )
    lower_confidence_total = sum(
        1
        for candidate in candidates
        if str(candidate.get("confidence") or "").upper() == "LOWER"
    )
    suspicious_codes = {
        str(code)
        for candidate in candidates
        for code in (
            candidate.get("shorter_code"),
            candidate.get("longer_code"),
        )
        if code
    }
    excluded_total = sum(
        int(codes.get(key) or 0)
        for key in (
            "ignored_short_code_total",
            "ignored_vegetable_code_total",
            "ignored_other_code_total",
        )
    )
    lines.extend(
        [
            "SUSPICIOUS OR INCOMPLETE PRODUCT CODES",
            "-" * 64,
            f"Status: {codes.get('status') or 'NOT RUN'}",
            f"Started: {codes.get('started_at') or 'N/A'}",
            f"Completed: {codes.get('completed_at') or 'N/A'}",
            f"Duration: {float(codes.get('duration_seconds') or 0.0):.3f} seconds",
            f"Database path: {codes.get('database_path') or 'N/A'}",
            "",
            "CHECK SETTINGS",
            f"- Minimum barcode length checked: {codes.get('minimum_barcode_length', 5)} characters",
            "- Tail truncation range checked: "
            f"1 to {codes.get('maximum_missing_tail_characters', 3)} missing characters",
            "- Matching rule: shorter code must exactly match the start of a longer code",
            "",
            "SCAN SUMMARY",
            f"- Product codes read from database: {codes.get('database_total', 0)}",
            f"- Numeric barcode codes checked: {codes.get('eligible_numeric_total', 0)}",
            f"- Codes excluded from comparison: {excluded_total}",
            f"  - Short keyboard shortcut codes: {codes.get('ignored_short_code_total', 0)}",
            f"  - Automated vegetable codes: {codes.get('ignored_vegetable_code_total', 0)}",
            f"  - Other nonnumeric/internal codes: {codes.get('ignored_other_code_total', 0)}",
            "",
            "FINDINGS",
            f"- Suspicious product codes: {len(suspicious_codes)}",
            f"- Suspicious tail-truncation pairs found: {len(candidates)}",
            f"  - High-confidence pairs: {high_confidence_total}",
            f"  - Lower-confidence pairs: {lower_confidence_total}",
            "",
            "REVIEW CANDIDATES",
        ]
    )
    if candidates:
        for index, candidate in enumerate(candidates, start=1):
            lines.extend(
                [
                    f"{index}. Missing tail characters: "
                    f"{candidate.get('missing_tail_characters', 'N/A')}",
                    f"   Confidence: {candidate.get('confidence', 'N/A')}",
                    "   Prefix coverage: "
                    f"{float(candidate.get('prefix_coverage_percent') or 0.0):.2f}%",
                    f"   a) {candidate.get('shorter_code') or 'N/A'} - "
                    f"{candidate.get('product_name_1') or 'Unnamed product'}",
                    f"   b) {candidate.get('longer_code') or 'N/A'} - "
                    f"{candidate.get('product_name_2') or 'Unnamed product'}",
                    "",
                ]
            )
    else:
        lines.append("- None")
    lines.extend(["", "Issues:"])
    lines.extend(
        [f"- {issue}" for issue in (codes.get("issues") or [])]
        or ["- None"]
    )
    lines.append("")


def _append_product_name_report(lines: list[str], names: Mapping) -> None:
    lines.extend(
        [
            "DUPLICATE PRODUCT NAMES",
            "-" * 64,
            f"Status: {names.get('status') or 'NOT RUN'}",
            f"Started: {names.get('started_at') or 'N/A'}",
            f"Completed: {names.get('completed_at') or 'N/A'}",
            f"Duration: {float(names.get('duration_seconds') or 0.0):.3f} seconds",
            f"Database path: {names.get('database_path') or 'N/A'}",
            "",
            "CHECK SETTINGS",
            "- Matching is case-insensitive",
            "- Leading, trailing, and repeated whitespace is normalized",
            "- Punctuation is preserved",
            "- Near-duplicate or fuzzy matching is not performed",
            "",
            "SCAN SUMMARY",
            f"- Products read from database: {names.get('database_total', 0)}",
            f"- Nonempty product names checked: {names.get('names_checked_total', 0)}",
            f"- Empty product names skipped: {names.get('empty_name_total', 0)}",
            "",
            "FINDINGS",
            f"- Duplicate name groups found: {names.get('duplicate_group_total', 0)}",
            f"- Products in duplicate groups: {names.get('duplicate_product_total', 0)}",
            "",
            "REVIEW CANDIDATES",
        ]
    )
    groups = list(names.get("duplicate_groups") or [])
    if groups:
        for group_index, group in enumerate(groups, start=1):
            lines.append(
                f"{group_index}. Normalized name: "
                f"{group.get('normalized_name') or 'N/A'} "
                f"({group.get('product_count', 0)} products)"
            )
            for product_index, product in enumerate(
                group.get("products") or [],
                start=1,
            ):
                label = chr(ord("a") + product_index - 1)
                lines.append(
                    f"   {label}) {product.get('product_code') or 'N/A'} - "
                    f"{product.get('product_name') or 'Unnamed product'}"
                )
            lines.append("")
    else:
        lines.append("- None")
    lines.extend(["", "Issues:"])
    lines.extend(
        [f"- {issue}" for issue in (names.get("issues") or [])]
        or ["- None"]
    )
    lines.append("")


def _append_product_derived_ui_report(lines: list[str], ui_data: Mapping) -> None:
    lines.extend(
        [
            "PRODUCT SEARCH LISTS AND VEGETABLE SLOTS",
            "-" * 64,
            f"Status: {ui_data.get('status') or 'NOT RUN'}",
            f"Started: {ui_data.get('started_at') or 'N/A'}",
            f"Completed: {ui_data.get('completed_at') or 'N/A'}",
            f"Duration: {float(ui_data.get('duration_seconds') or 0.0):.3f} seconds",
            "",
            "CHECK SCOPE",
            "- Source: live PRODUCT_CACHE",
            "- Product-name consumers: "
            + ", ".join(ui_data.get("consumer_names") or ["None"]),
            "- Fixed vegetable slot range: VEG01 to VEG16",
            "- Ordinary barcoded Vegetable-category products are not checked",
            "",
            "PRODUCT SEARCH CHOICES",
            f"- Cache entries read: {ui_data.get('cache_total', 0)}",
            f"- Source product names: {ui_data.get('source_name_total', 0)}",
            f"- Expected choices: {ui_data.get('expected_choice_total', 0)}",
            f"- Shared choices produced: {ui_data.get('choice_total', 0)}",
            "- Duplicate source-name entries preserved: "
            f"{ui_data.get('duplicate_source_name_total', 0)}",
            f"- Choices sorted: {'PASS' if ui_data.get('choices_sorted') else 'FAIL'}",
        ]
    )
    for heading, key in (
        ("Missing choices", "missing_choice_names"),
        ("Extra choices", "extra_choice_names"),
        ("Products with empty names", "invalid_name_codes"),
        ("Malformed cache records", "malformed_cache_codes"),
    ):
        values = list(ui_data.get(key) or [])
        lines.append(f"- {heading}: {len(values)}")
        lines.extend(f"  - {value}" for value in values)

    lines.extend(
        [
            "",
            "FIXED VEGETABLE SLOTS",
            f"- Expected slots: {ui_data.get('expected_vegetable_total', 16)}",
            f"- Available slots: {ui_data.get('available_vegetable_total', 0)}",
        ]
    )
    for heading, key in (
        (
            "Unpopulated slot codes (informational)",
            "missing_vegetable_codes",
        ),
        (
            "Reserved codes outside VEG01-VEG16",
            "unexpected_vegetable_codes",
        ),
    ):
        values = list(ui_data.get(key) or [])
        lines.append(f"- {heading}: {len(values)}")
        lines.extend(f"  - {value}" for value in values)

    invalid_records = list(ui_data.get("invalid_vegetable_records") or [])
    lines.append(f"- Invalid slot records: {len(invalid_records)}")
    for record in invalid_records:
        lines.append(
            f"  - {record.get('product_code') or 'N/A'}: "
            + ", ".join(record.get("invalid_fields") or ["unknown"])
        )

    lines.extend(["", "LIMITATIONS"])
    lines.extend(
        [f"- {item}" for item in (ui_data.get("limitations") or [])]
        or ["- None"]
    )
    lines.extend(["", "Issues:"])
    lines.extend(
        [f"- {issue}" for issue in (ui_data.get("issues") or [])]
        or ["- None"]
    )
    lines.append("")


def _append_category_integrity_report(
    lines: list[str],
    categories: Mapping,
) -> None:
    lines.extend(
        [
            "CATEGORY INTEGRITY",
            "-" * 64,
            f"Status: {categories.get('status') or 'NOT RUN'}",
            f"Started: {categories.get('started_at') or 'N/A'}",
            f"Completed: {categories.get('completed_at') or 'N/A'}",
            f"Duration: {float(categories.get('duration_seconds') or 0.0):.3f} seconds",
            f"Database path: {categories.get('database_path') or 'N/A'}",
            "",
            "DATABASE SUMMARY",
            f"- Categories read: {categories.get('category_total', 0)}",
            f"- Products checked: {categories.get('product_total', 0)}",
            "",
            "NAME INTEGRITY",
            f"- Blank category names: {categories.get('blank_category_total', 0)}",
        ]
    )
    for category in categories.get("blank_categories") or []:
        lines.append(
            f"  - category_id={category.get('category_id')}"
        )

    duplicate_groups = list(categories.get("duplicate_name_groups") or [])
    lines.append(
        f"- Duplicate normalized name groups: {len(duplicate_groups)}"
    )
    for group in duplicate_groups:
        lines.append(
            f"  - {group.get('normalized_name') or 'N/A'} "
            f"({group.get('category_count', 0)} categories)"
        )
        for category in group.get("categories") or []:
            lines.append(
                f"    - category_id={category.get('category_id')}: "
                f"{category.get('name') or 'Blank'}"
            )

    lines.extend(["", "REQUIRED CATEGORIES"])
    required = dict(categories.get("required_categories") or {})
    for required_name in ("Other", "Vegetable"):
        matches = list(required.get(required_name) or [])
        if not matches:
            lines.append(f"- {required_name}: MISSING")
        elif len(matches) == 1:
            match = matches[0]
            lines.append(
                f"- {required_name}: Present, "
                f"category_id={match.get('category_id')}, "
                f"protected={'Yes' if match.get('is_protected') else 'No'}"
            )
        else:
            ids = ", ".join(
                str(match.get("category_id")) for match in matches
            )
            lines.append(
                f"- {required_name}: MULTIPLE MATCHES, category_ids={ids}"
            )

    no_category = list(categories.get("products_without_category_id") or [])
    missing_category = list(
        categories.get("products_with_missing_category_id") or []
    )
    lines.extend(
        [
            "",
            "PRODUCT-CATEGORY RELATIONSHIPS",
            f"- Products with no category_id: {len(no_category)}",
        ]
    )
    for product in no_category:
        lines.append(
            f"  - {product.get('product_code') or 'N/A'} - "
            f"{product.get('product_name') or 'Unnamed product'}"
        )
    lines.append(
        "- Products referencing an ID that does not exist in the "
        f"Category table: {len(missing_category)}"
    )
    for product in missing_category:
        lines.append(
            f"  - {product.get('product_code') or 'N/A'} - "
            f"{product.get('product_name') or 'Unnamed product'}; "
            f"category_id={product.get('category_id')}"
        )

    wrong_vegetables = list(
        categories.get("fixed_vegetables_wrong_category") or []
    )
    lines.extend(
        [
            "",
            "FIXED VEGETABLE CATEGORY",
            "- Existing VEG01-VEG16 products not assigned to Vegetable: "
            f"{len(wrong_vegetables)}",
        ]
    )
    for product in wrong_vegetables:
        lines.append(
            f"  - {product.get('product_code') or 'N/A'} - "
            f"{product.get('product_name') or 'Unnamed product'}; "
            f"category_id={product.get('category_id')}; "
            f"category={product.get('category_name') or 'Missing'}"
        )

    lines.extend(["", "Issues:"])
    lines.extend(
        [f"- {issue}" for issue in (categories.get("issues") or [])]
        or ["- None"]
    )
    lines.append("")


def _append_runtime_assets_report(lines: list[str], runtime: Mapping) -> None:
    lines.extend(
        [
            "RUNTIME ASSETS AND PATHS",
            "-" * 64,
            f"Status: {runtime.get('status') or 'NOT RUN'}",
            f"Started: {runtime.get('started_at') or 'N/A'}",
            f"Completed: {runtime.get('completed_at') or 'N/A'}",
            f"Duration: {float(runtime.get('duration_seconds') or 0.0):.3f} seconds",
            f"Execution layout: {'Packaged' if runtime.get('is_packaged') else 'Source'}",
            "",
            "RESOLVED PATHS",
            f"- Application directory: {runtime.get('app_dir') or 'N/A'}",
            f"  Exists: {'Yes' if runtime.get('app_dir_exists') else 'No'}",
            f"- Client root: {runtime.get('client_root') or 'N/A'}",
            f"  Exists: {'Yes' if runtime.get('client_root_exists') else 'No'}",
            f"- Database: {runtime.get('database_path') or 'N/A'}",
            f"  Exists: {'Yes' if runtime.get('database_exists') else 'No'}",
            f"  Readable: {'Yes' if runtime.get('database_readable') else 'No'}",
            "  Parent folder writable: "
            + ("Yes" if runtime.get("database_parent_writable") else "No"),
            f"- Diagnostic export folder: {runtime.get('export_path') or 'N/A'}",
            "  Ready or creatable: "
            + ("Yes" if runtime.get("export_path_ready") else "No"),
            "",
            "REQUIRED RUNTIME ASSETS",
            f"- UI files expected: {runtime.get('required_ui_total', 0)}",
            f"  Missing: {len(runtime.get('missing_ui_files') or [])}",
        ]
    )
    lines.extend(
        f"  - {name}" for name in (runtime.get("missing_ui_files") or [])
    )
    lines.extend(
        [
            f"- QSS files expected: {runtime.get('required_qss_total', 0)}",
            f"  Missing: {len(runtime.get('missing_qss_files') or [])}",
        ]
    )
    lines.extend(
        f"  - {name}" for name in (runtime.get("missing_qss_files") or [])
    )
    lines.extend(
        [
            f"- SVG icons expected: {runtime.get('required_icon_total', 0)}",
            f"  Missing: {len(runtime.get('missing_icon_files') or [])}",
        ]
    )
    lines.extend(
        f"  - {name}" for name in (runtime.get("missing_icon_files") or [])
    )
    invalid_icons = list(runtime.get("invalid_icon_files") or [])
    lines.append(f"  Qt load failures: {len(invalid_icons)}")
    lines.extend(f"  - {name}" for name in invalid_icons)

    lines.extend(
        [
            "",
            "DISK SPACE (INFORMATIONAL)",
            "- Database location available space: "
            + _format_bytes(runtime.get("database_disk_free_bytes")),
            "- Export location available space: "
            + _format_bytes(runtime.get("export_disk_free_bytes")),
            "- Disk-space values do not affect diagnostic status.",
            "",
            "Issues:",
        ]
    )
    lines.extend(
        [f"- {issue}" for issue in (runtime.get("issues") or [])]
        or ["- None"]
    )
    lines.append("")


def _append_device_readiness_report(
    lines: list[str],
    devices: Mapping,
) -> None:
    scanner = dict(devices.get("scanner") or {})
    printer = dict(devices.get("printer") or {})
    drawer = dict(devices.get("cash_drawer") or {})
    monitor = dict(devices.get("second_monitor") or {})
    lines.extend(
        [
            "DEVICE READINESS",
            "-" * 64,
            f"Status: {devices.get('status') or 'NOT RUN'}",
            f"Started: {devices.get('started_at') or 'N/A'}",
            f"Completed: {devices.get('completed_at') or 'N/A'}",
            f"Duration: {float(devices.get('duration_seconds') or 0.0):.3f} seconds",
            "",
            "CHECK SCOPE",
            "- Software, configuration, controller, and display detection only",
            "- No receipt is printed",
            "- No cash-drawer pulse is sent",
            "- No scanner input is requested",
            "- No second-monitor test pattern is shown",
            "",
            "BARCODE SCANNER",
            f"- State: {scanner.get('state') or 'N/A'}",
            f"- Scanner module available: {'Yes' if scanner.get('module_available') else 'No'}",
            f"- pynput dependency available: {'Yes' if scanner.get('pynput_available') else 'No'}",
            f"- Controller: {scanner.get('controller_state') or 'N/A'}",
            f"- Scanner timing valid: {'Yes' if scanner.get('timing_valid') else 'No'}",
            f"- Physical input test: {scanner.get('physical_test') or 'NOT TESTED'}",
            "",
            "RECEIPT PRINTER",
            f"- State: {printer.get('state') or 'N/A'}",
            f"- Printing enabled: {'Yes' if printer.get('enabled') else 'No'}",
            f"- Printer module available: {'Yes' if printer.get('module_available') else 'No'}",
            f"- python-escpos available: {'Yes' if printer.get('escpos_available') else 'No'}",
            f"- Configured address: {printer.get('ip') or 'Not configured'}",
            f"- Address valid: {'Yes' if printer.get('ip_valid') else 'No'}",
            f"- Configured port: {printer.get('port') if printer.get('port') is not None else 'Not configured'}",
            f"- Port valid: {'Yes' if printer.get('port_valid') else 'No'}",
            f"- Print test: {printer.get('physical_test') or 'NOT TESTED'}",
            "",
            "CASH DRAWER",
            f"- State: {drawer.get('state') or 'N/A'}",
            f"- Cash drawer enabled: {'Yes' if drawer.get('enabled') else 'No'}",
            f"- Configured pin: {drawer.get('pin') if drawer.get('pin') is not None else 'Not configured'}",
            f"- Pin valid: {'Yes' if drawer.get('pin_valid') else 'No'}",
            f"- Timeout valid: {'Yes' if drawer.get('timeout_valid') else 'No'}",
            f"- Open test: {drawer.get('physical_test') or 'NOT TESTED'}",
            "",
            "SECOND MONITOR",
            f"- State: {monitor.get('state') or 'N/A'}",
            f"- Customer display enabled: {'Yes' if monitor.get('enabled') else 'No'}",
            f"- Test-window mode: {'Yes' if monitor.get('test_mode') else 'No'}",
            f"- Customer-display module available: {'Yes' if monitor.get('module_available') else 'No'}",
            f"- screen2.ui available: {'Yes' if monitor.get('screen2_ui_available') else 'No'}",
            f"- Configured screen index: {monitor.get('configured_screen_index') if monitor.get('configured_screen_index') is not None else 'Not configured'}",
            f"- Displays detected by Qt: {monitor.get('detected_screen_total', 0)}",
            "- Physical second display detected: "
            + (
                "Yes"
                if monitor.get("physical_second_display_detected")
                else "No"
            ),
            f"- Presentation test: {monitor.get('physical_test') or 'NOT TESTED'}",
            "",
            "PHYSICAL VERIFICATION",
            "- "
            + (
                devices.get("physical_verification_message")
                or "Physical operation was not tested."
            ),
            "",
            "Issues:",
        ]
    )
    lines.extend(
        [f"- {issue}" for issue in (devices.get("issues") or [])]
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
    product_codes = dict((diagnostic_results or {}).get("product_codes") or {})
    product_names = dict((diagnostic_results or {}).get("product_names") or {})
    product_derived_ui = dict(
        (diagnostic_results or {}).get("product_derived_ui") or {}
    )
    category_integrity = dict(
        (diagnostic_results or {}).get("category_integrity") or {}
    )
    runtime_assets = dict(
        (diagnostic_results or {}).get("runtime_assets") or {}
    )
    device_readiness = dict(
        (diagnostic_results or {}).get("device_readiness") or {}
    )
    completed = [
        item
        for item in (
            database,
            product_cache,
            product_codes,
            product_names,
            product_derived_ui,
            category_integrity,
            runtime_assets,
            device_readiness,
        )
        if item
    ]
    statuses = [str(item.get("status") or "FAIL") for item in completed]
    overall_status = (
        "FAIL"
        if "FAIL" in statuses
        else (
            "WARNING"
            if "WARNING" in statuses
            else ("PASS" if statuses else "NOT RUN")
        )
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
        selected_number += 1
    if product_codes:
        lines.append(
            f"{selected_number}. Suspicious or incomplete product codes"
        )
        selected_number += 1
    if product_names:
        lines.append(f"{selected_number}. Duplicate product names")
        selected_number += 1
    if product_derived_ui:
        lines.append(
            f"{selected_number}. Product search lists and vegetable slots"
        )
        selected_number += 1
    if category_integrity:
        lines.append(f"{selected_number}. Category integrity")
        selected_number += 1
    if runtime_assets:
        lines.append(f"{selected_number}. Runtime assets and paths")
        selected_number += 1
    if device_readiness:
        lines.append(f"{selected_number}. Device readiness")
    lines.append("")
    if database:
        _append_database_report(lines, database)
    if product_cache:
        _append_product_cache_report(lines, product_cache)
    if product_codes:
        _append_product_code_report(lines, product_codes)
    if product_names:
        _append_product_name_report(lines, product_names)
    if product_derived_ui:
        _append_product_derived_ui_report(lines, product_derived_ui)
    if category_integrity:
        _append_category_integrity_report(lines, category_integrity)
    if runtime_assets:
        _append_runtime_assets_report(lines, runtime_assets)
    if device_readiness:
        _append_device_readiness_report(lines, device_readiness)

    lines.extend(["", "=" * 64, "END OF REPORT", ""])
    return "\n".join(lines)
