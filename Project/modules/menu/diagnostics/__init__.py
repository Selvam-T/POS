"""Public entry points for POS diagnostics."""

from .category_integrity_check import (
    REQUIRED_CATEGORY_NAMES,
    analyze_category_integrity,
    normalize_category_name,
    run_category_integrity_diagnostics,
)
from .database_check import CORE_TABLES, run_database_diagnostics
from .device_readiness_check import (
    analyze_device_readiness,
    run_device_readiness_diagnostics,
)
from .product_cache_check import (
    compare_product_cache,
    run_product_cache_diagnostics,
)
from .product_code_check import (
    find_suspicious_product_codes,
    run_product_code_diagnostics,
)
from .product_name_check import (
    find_duplicate_product_names,
    normalize_product_name_for_duplicate_check,
    run_product_name_diagnostics,
)
from .product_derived_ui_check import (
    EXPECTED_VEGETABLE_CODES,
    PRODUCT_NAME_CONSUMERS,
    analyze_product_derived_ui,
    run_product_derived_ui_diagnostics,
)
from .report_exporter import DIAGNOSTIC_EXPORT_ROOT, export_diagnostic_report
from .report_formatter import format_diagnostic_report
from .runtime_assets_check import (
    REQUIRED_ICON_FILES,
    REQUIRED_QSS_FILES,
    REQUIRED_UI_FILES,
    analyze_runtime_assets,
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
    "normalize_product_name_for_duplicate_check",
    "normalize_category_name",
    "run_category_integrity_diagnostics",
    "run_database_diagnostics",
    "run_device_readiness_diagnostics",
    "run_product_cache_diagnostics",
    "run_product_code_diagnostics",
    "run_product_name_diagnostics",
    "run_product_derived_ui_diagnostics",
    "run_runtime_assets_diagnostics",
]
