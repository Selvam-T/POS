# Vegetable Entry Dialog and Selection Workflow

This document describes the workflow for the Vegetable Entry dialog, where users select vegetables with unit-aware behavior: KG items require weighing scale input (simulated 600g), while EACH items use editable quantity counts. All units are canonicalized to "Kg" or "Each" at every entry point, and all merging, display, and table logic is unified and robust.

## Key Components

- **UI File:** `ui/vegetable_entry.ui` — layout for the entry dialog (16 button grid, table, OK/CANCEL controls).
- **Logic:** `modules/sales/vegetable_entry.py` — controller for dialog, table setup, button selection, unit-based behavior, and duplicate handling.
- **Settings:** `modules/wrappers/settings.py` — manages vegetable label configuration and persistence (used by the Vegetable Menu editor).
- **Database:** `modules/db_operation/database.py` — provides product info with canonical unit ("Kg"/"Each") from PRODUCT_CACHE. All units are canonicalized before any operation.

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
- **Buttons:** `btnVeg01` to `vegEButton16` mapped to Veg01-Veg16 product codes
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
    - All merging is handled via a canonical data list and table rebuild, ensuring no duplicate rows.

### EACH Items (Count-Based)
When user clicks an EACH vegetable button:
1. Adds row to vegEntryTable with:
    - `quantity`: Numeric count (default: `1`)
    - **Display**: Integer (e.g., "1") in Quantity column, "ea" in Unit column
    - `editable`: `True` (quantity cell is EDITABLE, integer only, max 9999)
2. **Duplicate handling:** If same EACH item clicked again, INCREMENTS quantity by 1
    - All merging is handled via a canonical data list and table rebuild, ensuring no duplicate rows.

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
- **Add row:** `_add_vegetable_row()` checks for duplicates and merges using canonical units and a single data list, then calls `set_table_rows()` to rebuild the table.
- **Remove row:** Click DEL button (SVG icon, 32x32, row height 48px)
- **Rebuild table:** `_rebuild_vegetable_table()` respects per-row editable states

### Duplicate Detection
All duplicate detection and merging is handled by scraping the table to a canonical data list, merging by product name and canonical unit, and then rebuilding the table. No in-place cell updates are performed; all changes go through the data list and `set_table_rows()`.

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
# 4. Rebuild table with set_table_rows()
```

## QSS Styling

- Dialog-specific styles are loaded from `assets/sales.qss` and applied to the dialog.
- Styles for buttons, labels, and table headers are modularized for maintainability.



## Recent Changes (Jan 2026)

### Centralized Keyboard Orchestration & UI Architecture

**FieldCoordinator (focus_utils.py):**
- Now acts as the global event interceptor for all registered widgets in the dialog.
- **Enter-Key Hijacking:** Intercepts Return/Enter keys and prevents QDialog from performing native Accept or "Ghost Click" behaviors.
- **Smart Swallowing:** If Enter is pressed on an empty field, the Coordinator highlights the field and refuses to move focus, trapping the user until a valid value is entered.
- **Simple Jump Support:** Supports next_focus jumps even without a lookup function.
- **Button Triggering:** If Enter is pressed on a QPushButton, manually triggers obj.click() for Enter-to-Submit.
- **Dynamic Registration:** Controllers must register new qtyInput widgets with the coordinator as soon as they are created (e.g., after adding a vegetable row).

**table_operations.py:**
- **Regex Validation:** Uses QRegularExpressionValidator (pattern `^[1-9][0-9]{0,3}$`) for quantity input, blocking '0', letters, and symbols at the source.
- **No Manual Focus Management:** All setFocus, clearFocus, and selection logic removed; focus is managed by the FieldCoordinator.
- **bind_next_focus_widget:** Allows controllers to define post-edit focus flow without hardcoding logic in the table layer.

**vegetable_entry.py:**
- **Global Button Neutralization:** Recursively strips autoDefault and default from all buttons to prevent ghost clicks.
- **Speed-of-Sale Optimization:** Focus flow automatically shifts to OK ALL after a vegetable is selected or quantity is edited, supporting rapid workflows.

**menu.qss:**
- **Selector Precision:** Uses *= (contains) for vegEButton selectors, ensuring all 16 buttons are styled.
- **State-Based Styling:** [state="active"] and [state="unused"] properties allow dynamic visual feedback for vegetable slots.

### Final Workflow Summary

| Action                | Character Logic      | Enter Key Logic         | Result                                 |
|-----------------------|---------------------|-------------------------|----------------------------------------|
| Typing '0' or 'a'     | Swallowed by Regex  | N/A                    | Character never appears                |
| Enter on Empty Box    | N/A                 | Swallowed by Coordinator| Focus stays; Box highlights            |
| Enter on Valid Qty    | N/A                 | Jump by Coordinator     | Focus moves to OK Button               |
| Enter on OK Button    | N/A                 | Click by Coordinator    | _handle_ok_all validates & closes      |
| Enter on Veg Button   | N/A                 | Click by Coordinator    | Row added; Focus jumps to OK           |

## Quick Reference

- Entry dialog: `modules/sales/vegetable_entry.py: open_vegetable_entry_dialog`
- Stylesheet: `assets/sales.qss`
- UI file: `ui/vegetable_entry.ui`
