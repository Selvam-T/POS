"""
UI table operations module for the POS system.
Provides table setup and manipulation functions for application table widgets.
"""
from .table_operations import (
    setup_sales_table,
    recalc_row_total,
    get_row_color,
    bind_total_label,
    recompute_total,
    get_total,
    get_subtotal,
    handle_barcode_scanned,
    find_product_in_table,
    increment_row_quantity,
    set_table_rows,
    add_total_listener,
)
__all__ = [
    'setup_sales_table',
    'recalc_row_total',
    'get_row_color',
    'bind_total_label',
    'recompute_total',
    'get_total',
    'get_subtotal',
    'add_total_listener',
    'handle_barcode_scanned',
    'find_product_in_table',
    'increment_row_quantity',
    'set_table_rows',
]
