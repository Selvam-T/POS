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
    REQUIRED_CATEGORY_NAMES,
    REQUIRED_ICON_FILES,
    REQUIRED_QSS_FILES,
    REQUIRED_UI_FILES,
    analyze_category_integrity,
    analyze_device_readiness,
    analyze_product_derived_ui,
    analyze_runtime_assets,
    compare_product_cache,
    export_diagnostic_report,
    format_diagnostic_report,
    find_suspicious_product_codes,
    find_duplicate_product_names,
    find_missing_product_cost_prices,
    normalize_category_name,
    run_category_integrity_diagnostics,
    run_database_diagnostics,
    run_device_readiness_diagnostics,
    run_product_cache_diagnostics,
    run_product_code_diagnostics,
    run_product_name_diagnostics,
    run_product_cost_price_diagnostics,
    run_product_derived_ui_diagnostics,
    run_runtime_assets_diagnostics,
)


__all__ = [
    "CORE_TABLES",
    "DIAGNOSTIC_EXPORT_ROOT",
    "EXPECTED_VEGETABLE_CODES",
    "PRODUCT_NAME_CONSUMERS",
    "REQUIRED_CATEGORY_NAMES",
    "REQUIRED_ICON_FILES",
    "REQUIRED_QSS_FILES",
    "REQUIRED_UI_FILES",
    "analyze_category_integrity",
    "analyze_device_readiness",
    "analyze_product_derived_ui",
    "analyze_runtime_assets",
    "compare_product_cache",
    "export_diagnostic_report",
    "format_diagnostic_report",
    "find_suspicious_product_codes",
    "find_duplicate_product_names",
    "find_missing_product_cost_prices",
    "normalize_category_name",
    "run_category_integrity_diagnostics",
    "run_database_diagnostics",
    "run_device_readiness_diagnostics",
    "run_product_cache_diagnostics",
    "run_product_code_diagnostics",
    "run_product_name_diagnostics",
    "run_product_cost_price_diagnostics",
    "run_product_derived_ui_diagnostics",
    "run_runtime_assets_diagnostics",
]
