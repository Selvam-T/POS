"""Compatibility imports for the organized diagnostics package.

New code should import from ``modules.menu.diagnostics`` or its focused
submodules. This facade keeps earlier callers and external developer tools
working without duplicating diagnostic logic.
"""

from modules.menu.diagnostics import (
    CORE_TABLES,
    DIAGNOSTIC_EXPORT_ROOT,
    EXPECTED_VEGETABLE_CODES,
    PRODUCT_NAME_CONSUMERS,
    analyze_product_derived_ui,
    compare_product_cache,
    export_diagnostic_report,
    format_diagnostic_report,
    find_suspicious_product_codes,
    find_duplicate_product_names,
    run_database_diagnostics,
    run_product_cache_diagnostics,
    run_product_code_diagnostics,
    run_product_name_diagnostics,
    run_product_derived_ui_diagnostics,
)


__all__ = [
    "CORE_TABLES",
    "DIAGNOSTIC_EXPORT_ROOT",
    "EXPECTED_VEGETABLE_CODES",
    "PRODUCT_NAME_CONSUMERS",
    "analyze_product_derived_ui",
    "compare_product_cache",
    "export_diagnostic_report",
    "format_diagnostic_report",
    "find_suspicious_product_codes",
    "find_duplicate_product_names",
    "run_database_diagnostics",
    "run_product_cache_diagnostics",
    "run_product_code_diagnostics",
    "run_product_name_diagnostics",
    "run_product_derived_ui_diagnostics",
]
