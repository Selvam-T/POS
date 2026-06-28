"""
Sales module for the POS system.
"""
from modules.table_ui import (
    setup_sales_table,
    recalc_row_total,
    get_row_color,
    bind_total_label,
    recompute_total,
    get_total,
    get_subtotal,
)

__all__ = [
    'setup_sales_table',
    'recalc_row_total',
    'get_row_color',
    'bind_total_label',
    'recompute_total',
    'get_total',
    'get_subtotal',
]
