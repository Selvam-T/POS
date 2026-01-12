# Table Operations Module (`modules/table/table_operations.py`)

## Overview
This module provides generic table operations for product tables in the POS system, including setup, row management, and automatic total value binding. Used by both the sales table and vegetable entry table.

## Table Structure (7 Columns)
- **Column 0**: No. (row number, auto-renumbered)
- **Column 1**: Product (product name)
- **Column 2**: Quantity (numeric value only, QLineEdit with validation)
- **Column 3**: Unit (displays 'g', 'kg', or 'ea' - empty header)
- **Column 4**: Unit Price
- **Column 5**: Total (calculated: quantity × unit price)
- **Column 6**: Del (delete button)


## Key Functions
- `setup_sales_table(table)`: Configures table columns, headers, and default appearance. Should be called once after creating or loading the table widget.
- `set_sales_rows(table, rows, status_bar=None, editable=True)`: Populates the table with product rows. Applies single editable state to ALL rows.
- `set_table_rows(table, rows, status_bar=None)`: Rebuilds table with per-row editable states. Used when mixing KG (read-only) and EACH (editable) items. **Display logic uses the `numeric_value` property to preserve high-precision weights (KG) while showing user-friendly units (g/kg/ea).**
- `remove_table_row(table, row)`: Removes a row and updates numbering and colors.
- `recalc_row_total(table, row)`: Recomputes the total for a row when quantity or price changes. **Handles ValueError from input_handler if invalid characters are typed.**
- `bind_total_label(table, label)`: Binds a QLabel (usually `totalValue` in the UI) to the table. The label will automatically update whenever the table's contents change.
- `recompute_total(table)`: Recomputes and returns the grand total from all rows, updating the bound label if present.
- `get_total(table)`: Returns the last computed grand total.
- `handle_barcode_scanned(table, barcode, status_bar=None)`: Processes barcode scans. **BLOCKS KG items** (shows message to use Vegetable Entry), adds EACH items normally.

### Centralized Quantity Validation (2026 Update)
- `get_sales_data(table)`: Now uses `input_handler.handle_quantity_input` for extracting and validating quantity from each row. This ensures all numeric checks, limits (e.g., 9999), and error handling are consistent and centralized. Manual `float()` conversion is no longer used for editable rows.
- `recalc_row_total(table, row)`: Now catches `ValueError` from the input handler, so invalid user input (e.g., non-numeric) does not crash the table. Invalid or empty input results in a quantity of 0.0 for that row.

### Display Logic and Numeric Value Property
- `set_table_rows`: Always sets the `numeric_value` property on the quantity editor widget. For KG items, this preserves the high-precision weight (in kg) for calculations, while the display text shows grams or kg as appropriate. For EACH items, the property matches the integer value shown. This ensures calculations and display remain accurate and user-friendly.

## Product Cache Integration

### Canonical Unit Handling (2026 Update)
**PRODUCT_CACHE** stores: `{PRODUCT_CODE: (display_name, price, display_unit)}`
- **Cache keys**: normalized to `strip().upper()` for stable barcode/product_code matching.
- **Unit values**: always non-empty. Blank/NULL units are defaulted to `Each` when loading the cache.
- `get_product_info(code)` returns `(found, name, price, unit)`.

### KG vs EACH Item Display and Behavior
**KG Items** (weight-based):
- Require weighing scale input
- Can ONLY be added via Vegetable Entry dialog
- Barcode scanning is BLOCKED (shows: "KG item - use Vegetable Entry to weigh")
- Quantity cells are READ-ONLY (non-editable)
- **Quantity Display**: 
  - < 1000g: Shows grams (e.g., "600" with unit "g")
  - ≥ 1000g: Shows kg with 2 decimals (e.g., "1.20" with unit "kg")
- **Storage**: Always stored in kg for calculations (e.g., 0.6 kg for 600g)


**EACH Items** (count-based):
- Can be added via barcode scan or manual entry
- Quantity cells are EDITABLE
- **Quantity Display**: Integer only (e.g., "5" with unit "ea")
**Validation**: 
    - **Regex Validator (2026 Update):** Uses `QRegularExpressionValidator` with the pattern `^[1-9][0-9]{0,3}$`.
        - The first digit must be 1-9, so '0' is instantly blocked and cannot appear.
        - Only allows 1-4 digit positive integers (1-9999).
        - Letters, symbols, and leading zeros are instantly rejected.
        - User can press '0' as much as they want, but it is swallowed and never appears.
        - This solves the "0" problem and prevents invalid input at the source.

### Centralized Keyboard Orchestration (2026 Model)
- **No Manual Focus Management:** All focus, Enter key, and navigation logic is now handled by the FieldCoordinator (see focus_utils.md).
- **Dynamic Focus Binding:** Table logic is generic; controllers use `bind_next_focus_widget` to define post-edit focus flow.
- **No setFocus/cell selection in Table:** All focus jumps and error trapping are delegated to the FieldCoordinator, preventing focus conflicts.
- **Dynamic Registration:** For runtime-created widgets (e.g., new table rows), controllers must register each new qtyInput with the FieldCoordinator to ensure Enter key behavior.

## Advanced Features

### Mixed Editable States and Robust Merging with `set_table_rows()`
When tables contain both KG and EACH items, use this function to preserve per-row editable states. All merging, duplicate detection, and display logic is handled via a canonical data list and table rebuild:

```python
from modules.table import set_table_rows

rows = [
    {
        'product': 'Carrot',
        'quantity': 0.6,  # kg (stored in kg, displays as "600" with unit "g")
        'unit_price': 3.0,
        'unit': 'Kg',
        'editable': False,  # KG item - read-only
        'display_text': '600 g'
    },
    {
        'product': 'Onion',
        'quantity': 2,
        'unit_price': 1.5,
        'unit': 'Each',
        'editable': True,  # EACH item - editable
    }
]
set_table_rows(sales_table, rows)
```

### Editable State Determination
Editable state is set automatically based on canonical unit type when products are added:
- **Vegetable Entry dialog**: Checks canonical unit from `get_product_full()`, sets `editable=False` for KG
- **Barcode scan**: Blocks KG items entirely, only adds EACH items with `editable=True`
- **Transfer operations**: Preserve `editable` flag from source table

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
        'unit': 'Kg' or 'Each',  # Canonical unit only
        'editable': True,  # Whether quantity cell is editable
        'display_text': '1.5 kg'  # Optional: custom display for read-only fields
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

## Case-Insensitive Product Lookup and Normalization

- **Cache keys:** `PRODUCT_CACHE` keys are normalized to uppercase (`strip().upper()`).
- **Display strings:** names/units are stored in display-friendly Title Case via `_to_camel_case`.
- Code lookups are case-insensitive because input is normalized before cache access.

### Technical Details
- Normalization helpers live in `modules/db_operation/product_cache.py`.

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
