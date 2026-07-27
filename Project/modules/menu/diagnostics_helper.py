"""Compatibility imports for the organized diagnostics package.

New code should import from ``modules.menu.diagnostics`` or its focused
submodules. This facade keeps earlier callers and external developer tools
working without duplicating diagnostic logic.
"""

from modules.menu.diagnostics import (
    CORE_TABLES,
    DIAGNOSTIC_EXPORT_ROOT,
    compare_product_cache,
    export_diagnostic_report,
    format_diagnostic_report,
    run_database_diagnostics,
    run_product_cache_diagnostics,
)


__all__ = [
    "CORE_TABLES",
    "DIAGNOSTIC_EXPORT_ROOT",
    "compare_product_cache",
    "export_diagnostic_report",
    "format_diagnostic_report",
    "run_database_diagnostics",
    "run_product_cache_diagnostics",
]
