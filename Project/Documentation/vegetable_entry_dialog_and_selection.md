# Vegetable Entry Dialog and Selection Workflow

This document describes the workflow for the Vegetable Entry dialog, where users select vegetables with unit-aware behavior: KG items require weighing scale input (simulated 600g), while EACH items use editable quantity counts.

## Key Components

- **UI File:** `ui/vegetable_entry.ui` — layout for the entry dialog (16 button grid, table, OK/CANCEL controls).
- **Logic:** `modules/sales/vegetable_entry.py` — controller for dialog, table setup, button selection, unit-based behavior, and duplicate handling.
- **Settings:** `modules/wrappers/settings.py` — manages vegetable label configuration and persistence (used by the Vegetable Menu editor).
- **Database:** `modules/db_operation/database.py` — provides product info with unit (KG/EACH) from PRODUCT_CACHE.

## Dialog Layout

## Product Dropdown Model (Model/View Architecture)

 
 ## Dialog Layout
 
 ## Unit-Based Behavior
 
 ### KG Items (Weight-Based)
 When user clicks a KG vegetable button:
 1. Dialog reads weighing scale (simulated: 600g = 0.6 kg)
 2. Adds row to vegEntryTable with:
     - `quantity`: Numeric weight in kg (e.g., `0.6`, stored for calculations)
     - **Display**: "600" in Quantity column, "g" in Unit column
     - `editable`: `False` (quantity cell is READ-ONLY)
 3. **Duplicate handling:** If same KG item clicked again, ADDS weights (e.g., 600g + 600g = 1200g)
     - Updates to display "1.20" in Quantity, "kg" in Unit
 
 ### EACH Items (Count-Based)
 When user clicks an EACH vegetable button:
 1. Adds row to vegEntryTable with:
     - `quantity`: Numeric count (default: `1`)
     - **Display**: Integer (e.g., "1") in Quantity column, "ea" in Unit column
     - `editable`: `True` (quantity cell is EDITABLE, integer only, max 9999)
 2. **Duplicate handling:** If same EACH item clicked again, INCREMENTS quantity by 1

### Button Grid (16 Buttons)
- **Buttons:** `btnVeg01` to `btnVeg16` mapped to Veg01-Veg16 product codes
- **Enabled buttons:** Show product name from database (fetched via `get_product_info()`)
- **Disabled buttons:** Display "Not Used" when no product configured for slot

### Table (vegEntryTable) - 7 Columns
- **Columns:** `['No.', 'Product', 'Quantity', '', 'Unit Price', 'Total', 'Del']`
  - Column 3 has empty header, displays unit ('g', 'kg', or 'ea')
- **Purpose:** Temporary staging area for vegetable items before transfer to sales table
- **Quantity Display:**
  - KG items < 1000g: Shows grams (e.g., "600")
  - KG items ≥ 1000g: Shows kg with 2 decimals (e.g., "1.20")
  - EACH items: Shows integer count
- **Unit Display:** Separate column shows 'g', 'kg', or 'ea'
- **Editable behavior:** Per-row based on unit type (see below)

### Control Buttons
- **OK ALL:** Transfers all rows from vegEntryTable to salesTable, preserves editable states
- **CANCEL ALL:** Closes dialog without transfer

## Unit-Based Behavior

### KG Items (Weight-Based)
When user clicks a KG vegetable button:
1. Dialog reads weighing scale (simulated: 600g = 0.6 kg)
2. Adds row to vegEntryTable with:
   - `quantity`: Numeric weight in kg (e.g., `0.6`, stored for calculations)
   - **Display**: "600" in Quantity column, "g" in Unit column
   - `editable`: `False` (quantity cell is READ-ONLY)
3. **Duplicate handling:** If same KG item clicked again, ADDS weights (e.g., 600g + 600g = 1200g)
   - Updates to display "1.20" in Quantity, "kg" in Unit

### EACH Items (Count-Based)
When user clicks an EACH vegetable button:
1. Adds row to vegEntryTable with:
   - `quantity`: Numeric count (default: `1`)
   - **Display**: Integer (e.g., "1") in Quantity column, "ea" in Unit column
   - `editable`: `True` (quantity cell is EDITABLE, integer only, max 9999)
2. **Duplicate handling:** If same EACH item clicked again, INCREMENTS quantity by 1

### Unit Detection Logic
```python
# From _handle_vegetable_button_click()
_, name, price, unit = get_product_info(product_code)
unit_upper = unit.upper() if unit else 'EACH'

if unit_upper == 'KG':
    editable = False
    weight = 0.6  # Simulated weighing scale
    display_text = format_weight(weight)  # "600 g"
else:
    editable = True
    weight = 1
    display_text = None  # Use numeric display
```

## Table Operations Integration

### Table Setup
Uses `modules.table.table_operations.setup_sales_table()` for column configuration and styling.

### Row Management
- **Add row:** `_add_vegetable_row()` checks for duplicates, handles unit-specific behavior
- **Remove row:** Click DEL button (SVG icon, 32x32, row height 48px)
- **Rebuild table:** `_rebuild_vegetable_table()` respects per-row editable states

### Duplicate Detection
```python
# From _add_vegetable_row()
existing_row_index = _find_product_in_table(vegEntryTable, product_name)
if existing_row_index is not None:
    if unit_upper == 'EACH':
        # Increment quantity by 1
        current_qty = get_numeric_value(qty_widget)
        new_qty = current_qty + 1
        qty_widget.setText(str(int(new_qty)))
    elif unit_upper == 'KG':
        # Add weights
        current_weight = get_numeric_value(qty_widget)
        new_weight = current_weight + weight
        qty_widget.setText(format_weight(new_weight))
        qty_widget.setProperty('numeric_value', new_weight)
```

## Transfer to Sales Table

### OK ALL Button Handler
Extracts rows from vegEntryTable and stores them on the dialog object:
```python
# From _handle_ok_all()
rows_to_transfer = []
for row in range(vegEntryTable.rowCount()):
    product_name = vegEntryTable.item(row, 1).text()
    qty_widget = vegEntryTable.cellWidget(row, 2)
    qty_val = qty_widget.property('numeric_value') or float(qty_widget.text())
    
    # PRESERVE editable flag
    is_readonly = qty_widget.isReadOnly()
    editable = not is_readonly
    
    rows_to_transfer.append({
        'product': product_name,
        'quantity': qty_val,
        'unit_price': unit_price,
        'editable': editable
    })

# Store on dialog for retrieval by main window
dlg.setProperty('vegetable_rows', rows_to_transfer)
dlg.accept()
```

### Main Window Processing (Refactored Dec 2025)
The main window uses a unified handler to process dialog results:
```python
# From main.py: open_vegetable_entry_dialog()
self.dialog_wrapper.open_dialog_scanner_blocked(
    launch_vegetable_entry_dialog, 
    dialog_key='vegetable_entry',
    on_finish=lambda: self._add_items_to_sales_table('vegetable')
)

# _add_items_to_sales_table() handles:
# 1. Read dialog results (vegetable_rows property)
# 2. Extract existing sales table rows
# 3. Merge with duplicate detection (EACH: increment, KG: add weights)
# 4. Rebuild table with _rebuild_mixed_editable_table()
```

## QSS Styling

- Dialog-specific styles are loaded from `assets/sales.qss` and applied to the dialog.
- Styles for buttons, labels, and table headers are modularized for maintainability.

## Recent Changes (Dec 2025)

- **Unit-aware behavior:** KG items read-only with weighing, EACH items editable with counts
- **Duplicate handling:** EACH increments quantity, KG adds weights
- **Clean architecture:** Unit detection from PRODUCT_CACHE (3-tuple with unit)
- **Transfer preservation:** Editable flag preserved when moving to sales table
- **Mixed table support:** Uses `_rebuild_mixed_editable_table()` for per-row editable states

## Quick Reference

- Entry dialog: `modules/sales/vegetable_entry.py: open_vegetable_entry_dialog`
- Stylesheet: `assets/sales.qss`
- UI file: `ui/vegetable_entry.ui`
