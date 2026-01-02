"""
Table operations module for the POS system.
Provides generic table setup and manipulation functions for product tables.
"""
from .table_operations import (
    setup_sales_table,
    recalc_row_total,
    get_row_color,
    bind_total_label,
    recompute_total,
    get_total,
    handle_barcode_scanned,
    find_product_in_table,
    increment_row_quantity,
    set_table_rows,
)
__all__ = [
    'setup_sales_table',
    'recalc_row_total',
    'get_row_color',
    'bind_total_label',
    'recompute_total',
    'get_total',
    'handle_barcode_scanned',
    'find_product_in_table',
    'increment_row_quantity',
    'set_table_rows',
]

