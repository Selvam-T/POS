"""
Sales module for the POS system.
"""
from modules.table import (
    setup_sales_table,
    recalc_row_total,
    get_row_color,
    bind_total_label,
    recompute_total,
    get_total,
)

__all__ = [
    'setup_sales_table',
    'recalc_row_total',
    'get_row_color',
    'bind_total_label',
    'recompute_total',
    'get_total',
]
