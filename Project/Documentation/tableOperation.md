# Table Operations Module (`modules/table/table_operations.py`)

## Overview
This module provides generic table operations for product tables in the POS system, including setup, row management, and automatic total value binding. Used by both the sales table and vegetable entry table.

## Key Functions
- `setup_sales_table(table)`: Configures table columns, headers, and default appearance. Should be called once after creating or loading the table widget.
- `set_sales_rows(table, rows, status_bar=None, editable=True)`: Populates the table with product rows, including quantity input, unit price, and total calculation. Supports custom display text and editability control.
- `remove_table_row(table, row)`: Removes a row and updates numbering and colors.
- `recalc_row_total(table, row)`: Recomputes the total for a row when quantity or price changes.
- `bind_total_label(table, label)`: **Binds a QLabel (usually `totalValue` in the UI) to the table. The label will automatically update whenever the table's contents change.**
- `recompute_total(table)`: Recomputes and returns the grand total from all rows, updating the bound label if present.
- `get_total(table)`: Returns the last computed grand total.
- `handle_barcode_scanned(table, barcode, status_bar=None)`: Processes barcode scans, adding or updating products in the table.

## Advanced Features

### Editable vs Read-Only Quantity Fields
The `editable` parameter in `set_sales_rows()` and `_add_product_row()` controls whether quantity cells can be edited:
- **`editable=True`** (default): Quantity cells are editable, totals recalculate on text change
- **`editable=False`**: Quantity cells are read-only, useful for weight-based products

### Custom Display Text
The `display_text` parameter allows custom formatting in quantity cells while preserving numeric values for calculations:
- **Example**: Display "500 g" while storing numeric value `0.5` for calculations
- Numeric value is stored in widget property: `qty_edit.setProperty('numeric_value', float(qty_val))`
- Read-only fields use stored numeric value; editable fields parse and update from text

### Row Data Format
```python
rows = [
    {
        'product': 'Product Name',
        'quantity': 1.5,  # Numeric value for calculations
        'unit_price': 50.0,
        'display_text': '1.5 kg'  # Optional: custom display (e.g., "500 g", "1 Each")
    }
]
```

## Total Value Binding
To ensure the total value is always up to date:
1. Call `bind_total_label(table, label)` after setting up the table and locating the `totalValue` label.
2. The label will automatically reflect the current total as products are added, removed, or quantities changed.

**Example:**
```python
from modules.table import setup_sales_table, bind_total_label
# ...
sales_table = ...  # QTableWidget instance
setup_sales_table(sales_table)
bind_total_label(sales_table, total_label)  # total_label is a QLabel instance
```

## Integration
- The sales table is set up and bound to the total label in `modules/sales/sales_frame_setup.py`.
- The vegetable entry table uses the same functions with `editable=False` for weight-based products.
- The main window (`main.py`) uses `setup_sales_frame` to ensure the table and total label are always correctly initialized and bound.

## Migration Notes
- Migrated from `modules/sales/salesTable.py` to `modules/table/table_operations.py` on December 19, 2025
- All import statements updated across the codebase
- Backward compatible: existing code works without modifications
- New features: `editable` parameter, `display_text` support, numeric value storage

---
_Last updated: December 19, 2025_
