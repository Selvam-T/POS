# Sales Table Module (`modules/sales/salesTable.py`)

## Overview
This module provides all logic for the sales table in the POS system, including setup, row management, and automatic total value binding.

## Key Functions
- `setup_sales_table(table)`: Configures the sales table's columns, headers, and default appearance. Should be called once after creating or loading the table widget.
- `set_sales_rows(table, rows)`: Populates the table with product rows, including quantity input, unit price, and total calculation.
- `remove_table_row(table, row)`: Removes a row and updates numbering and colors.
- `recalc_row_total(table, row)`: Recomputes the total for a row when quantity or price changes.
- `bind_total_label(table, label)`: **Binds a QLabel (usually `totalValue` in the UI) to the sales table. The label will automatically update whenever the table's contents change.**
- `recompute_total(table)`: Recomputes and returns the grand total from all rows, updating the bound label if present.
- `get_total(table)`: Returns the last computed grand total.

## Total Value Binding
To ensure the total sales value is always up to date:
1. Call `bind_total_label(table, label)` after setting up the table and locating the `totalValue` label.
2. The label will automatically reflect the current total as products are added, removed, or quantities changed.

**Example:**
```python
from modules.sales.salesTable import setup_sales_table, bind_total_label
# ...
sales_table = ...  # QTableWidget instance
setup_sales_table(sales_table)
bind_total_label(sales_table, total_label)  # total_label is a QLabel instance
```

## Integration
- The sales table is set up and bound to the total label in `modules/sales/sales_frame_setup.py`.
- The main window (`main.py`) uses `setup_sales_frame` to ensure the table and total label are always correctly initialized and bound.

---
_Last updated: December 2, 2025_
