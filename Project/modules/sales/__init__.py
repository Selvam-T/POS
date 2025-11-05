"""
Sales module for the POS system.
"""
from .salesTable import (
    setup_sales_table,
    set_sales_rows,
    remove_table_row,
    recalc_row_total,
    get_row_color,
    bind_total_label,
    recompute_total,
    get_total,
)

__all__ = [
    'setup_sales_table',
    'set_sales_rows',
    'remove_table_row',
    'recalc_row_total',
    'get_row_color',
    'bind_total_label',
    'recompute_total',
    'get_total',
]
