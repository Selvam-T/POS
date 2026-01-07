# Manual Entry Dialog Documentation
# January 2026 Update

## January 2026: Keyboard, Focus, and Feedback Finalization

### Unified Event Interception & Focus Optimization
- **Enter-to-Click:** The FieldCoordinator detects focus on QPushButton (including the Close button). Pressing Enter manually triggers `obj.click()`, ensuring consistent behavior across all button types.
- **Ghost Click Elimination:** All buttons have `autoDefault` and `default` stripped. The Coordinator swallows and redirects Enter events, eliminating the "Enter triggers Veg01" bug.
- **Dynamic Tab Order:** After selecting a product or entering a valid quantity, focus jumps to the OK button, enabling rapid dialog completion.
- **Dynamic Registration:** New input widgets (e.g., quantity fields) are registered with the FieldCoordinator as they are created at runtime.

### Advanced Keyboard Swallowing & Validation
- **Regex Bouncer:** Uses `QRegularExpressionValidator` (`^[1-9][0-9]{0,3}$`) to block '0' and non-digits from quantity fields at the source.
- **Empty-Field Trap:** The FieldCoordinator swallows Enter on empty fields, forcing the user to enter a value before moving focus.

### Visual & UI Polish
- **Conditional Borders:** QSS uses `:focus:!read-only` logic. Only editable fields show a highlight border; read-only fields remain visually locked.
- **Focus Visibility:** CSS specificity fixes ensure focus borders are visible on active fields and the custom title bar's Close button.
- **Table Outline Cleanup:** Dotted focus rectangles on table rows are disabled via `outline: 0` for a modern look.

### Cross-Window Feedback
- **Status Bar Integration:** Dialogs now set a `main_status_msg` property before closing. The Main Window displays this message in the status bar, providing final confirmation of success or cancellation.

---
**All enhancements are now fully implemented in both manual_entry and vegetable_entry dialogs.**

---


## Overview

The Manual Entry dialog allows users to manually input product information when items cannot be processed through the standard vegetable entry or barcode scanning methods. This is useful for miscellaneous items, special products, or when the barcode scanner is unavailable.

### January 2026 Workflow Enhancements
- **Focus Jump:** After selecting a product name from the dropdown or entering a valid product code, focus automatically moves to the Quantity field for faster entry.
- **Immediate Validation:** Pressing Enter in any field triggers immediate validation. If the input is valid, focus advances to the next logical field or submits the form (when in Quantity).
- **POS-Optimized Flow:** This workflow matches standard POS behavior: type/select product, type quantity, press Enter, done.

**Note:** All manual entries are treated as EACH (count-based) items with editable quantities (integer only, range 1-9999). They display with unit "ea" in the sales table.

## Files Involved

### UI Definition
- **File**: `ui/manual_entry.ui`
- **Class**: `manualEntryDialog`
- **Type**: QWidget (loaded into QDialog)
- **Dimensions**: 500×350px (minimum: 350×310px)

### Python Module
- **File**: `modules/sales/manual_entry.py`
- **Function**: `open_manual_entry_dialog(parent)`
- **Returns**: Dictionary with product data or None

### Styling
- **File**: `assets/sales.qss`
- **Selector**: `QWidget#manualEntryDialog`

## UI Layout Structure
### Title Bar Example

```
┌─────────────────────────────────────────┐
│ [customTitleBar] ────────────────────── │
│   [customTitle]   [customCloseBtn]      │
│─────────────────────────────────────────│
│  Enter Item Details Manually:           │
│  ...existing layout...                  │
└─────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────┐
│  Enter Item Details Manually:           │ ← lblGeneral (title label)
│  [spacing: 30px]                        │
│                                         │
│  Product Name:  [input field]           │
│  Quantity:      [input field]           │
│  Unit Price:    [input field]           │
│  [spacing: 30px]                        │
│  [Cancel Button] [OK Button]            │
│                                         │
└─────────────────────────────────────────┘
```

### Layout Components

#### Main Layout (QVBoxLayout: mainManualEntryLayout)
- **Spacing**: 0px
- **Margins**: 20px (left/right), 15px (top/bottom)
- **Children**:
  1. verticalSpacer_1 (Fixed: 25px)
  2. lblGeneral (Title label)
  3. verticalSpacer_2 (Fixed: 30px)
  4. inputFieldsLayout (QGridLayout)
  5. verticalSpacer_3 (Fixed: 30px) - **Critical spacing between inputs and buttons**
  6. buttonLayout (QHBoxLayout)
  7. verticalSpacer_4 (Fixed: 20px)

#### Input Fields Layout (QGridLayout: inputFieldsLayout)
- **Spacing**: 10px (horizontal), 8px (vertical)
- **Margins**: None

| Row | Column 0 (Label) | Column 1 (Input) |
|-----|------------------|-----------------|
| 0   | lblProductName (Fixed: 100px) | inputProductName |
| 1   | lblQuantity (Fixed: 100px) | inputQuantity |
| 2   | lblUnitPrice (Fixed: 100px) | inputUnitPrice |

**Label Properties**:
- Width: Fixed at 100px
- Height: Auto (content-based)

**Input Field Properties**:
- Expanding horizontally
- Placeholder text: "Enter [field name]"

#### Button Layout (QHBoxLayout: buttonLayout)
- **Spacing**: 7px
- **Children**:
  1. buttonSpacer (Horizontal spacer: 40px)
  2. btnManualOk (MinimumExpanding, 0×50px, Font: 12pt)
  3. btnManualCancel (MinimumExpanding, 0×50px, Font: 12pt)

**Button Behavior**: Buttons expand equally to fill available horizontal space, positioned towards right side with leading spacer.

## Function: `open_manual_entry_dialog(parent)`

### Parameters
- `parent`: Parent window (typically the main sales window)

### Returns
- **Success**: Dictionary with keys:
  ```python
  {
      'product_name': str,      # Non-empty string
      'quantity': float,        # Positive number
      'unit_price': float,      # Positive number
      'total': float,           # quantity × unit_price
      'editable': bool          # Always True for manual entry (count-based items)
  }
  ```
- **Cancelled/Error**: `None`

**Note:** Manual entry items are always treated as count-based (like EACH units) with editable quantity cells. KG items requiring weighing must use the Vegetable Entry dialog instead.

### Process Flow

1. **Load UI**
   - Loads `manual_entry.ui` from UI directory
   - Handles missing file gracefully

2. **Create Dialog**
   - Creates QDialog with modal behavior
   - Sets window title: "Manual Product Input"
   - Window flags: Dialog | CustomizeWindowHint | WindowTitleHint | WindowCloseButtonHint
   - Removes min/max buttons, keeps title bar and close button

3. **Apply Styling**
   - Loads `sales.qss` and applies stylesheet
   - Includes specific styles for manual entry dialog

4. **Input Validation**
   - Product Name: Cannot be empty
   - Quantity: Must be a valid positive number
   - Unit Price: Must be a valid positive number

5. **Store Result**
   - On success, stores result as dialog attribute: `dlg.manual_entry_result = {...}`
   - Result structure: `{'product_name': str, 'quantity': float, 'unit_price': float}`
   - Dialog accepts (OK)

6. **Overlay & Scanner Management** (Handled by DialogWrapper)
   - DialogWrapper handles dimming overlay activation/deactivation
   - Scanner blocking/unblocking managed automatically
   - Dialog centering and focus restoration handled by wrapper

## Styling (sales.qss)

### Dialog Background

### Parameters
- `parent`: Parent window (typically the main sales window)

### Returns
- **Success**: Dictionary with keys:
    ```python
    {
            'product_name': str,      # Non-empty string
            'quantity': float,        # Positive number
            'unit_price': float,      # Positive number
            'editable': bool          # Always True for manual entry (count-based items)
    }
    ```
- **Cancelled/Error**: `None`

**Note:** Manual entry items are always treated as count-based (like EACH units) with editable quantity cells. KG items requiring weighing must use the Vegetable Entry dialog instead.

**Focus State**:
- Background: #FFF9C4 (lighter yellow)
- Border: 2px solid #4682B4 (blue)

**Error State** (when `error="true"` property set):
- Background: #FFCCCC (light red)
- Border: 2px solid #C0392B (red)

### Buttons

#### OK Button (btnManualOk)
- **Normal**: Green (#27AE60) with dark green border (#1E8449)
- **Hover**: #2ECC71 (lighter green)
- **Pressed**: #196F3D (dark green)
- **Size**: MinimumExpanding, height 50px
- **Font**: 12pt, bold, Verdana

#### Cancel Button (btnManualCancel)
- **Normal**: Red (#C0392B) with dark red border (#922B21)
- **Hover**: #E74C3C (lighter red)
- **Pressed**: #922B21 (dark red)
- **Size**: MinimumExpanding, height 50px
- **Font**: 12pt, bold, Verdana

## Read-Only Unit Field & Label Styling

- The unit field (`manualUnitLineEdit`) is read-only and filled programmatically based on product selection.
- The corresponding label (`manualUnitFieldLbl`) uses a custom QSS property (e.g., `readonly-label`) for distinct styling (gray color, italic, etc.).
- The property is set in the controller, and QSS rules ensure consistent appearance for read-only fields and labels.
- This improves clarity for users, indicating which fields are not editable.

## Usage Example (Refactored Dec 2025)


1. **Load UI**
    - Loads `manual_entry.ui` from UI directory
    - Handles missing file gracefully

2. **Create Dialog**
    - Creates QDialog with modal behavior
    - Sets window title: "Manual Product Input"
    - Window flags: Dialog | CustomizeWindowHint | WindowTitleHint | WindowCloseButtonHint
    - Removes min/max buttons, keeps title bar and close button

3. **Apply Styling**
    - Loads `sales.qss` and applies stylesheet
    - Includes specific styles for manual entry dialog

4. **Input Validation & Focus Behavior**
    - Product Name: Cannot be empty. After selection (dropdown or Enter), focus jumps to Quantity.
    - Product Code: After valid entry, focus jumps to Quantity.
    - Quantity: Must be a valid positive number. Pressing Enter here submits the form if all fields are valid.
    - All fields: Pressing Enter triggers immediate validation and focus advancement.

5. **Store Result**
    - On success, stores result as dialog attribute: `dlg.manual_entry_result = {...}`
    - Result structure: `{'product_name': str, 'quantity': float, 'unit_price': float}`
    - Dialog accepts (OK)

6. **Overlay & Scanner Management** (Handled by DialogWrapper)
    - DialogWrapper handles dimming overlay activation/deactivation
    - Scanner blocking/unblocking managed automatically
    - Dialog centering and focus restoration handled by wrapper
        }]
        
        # Merge with existing rows and rebuild table
        # ... (see main.py for full implementation)
```

## Integration Points (Refactored Dec 2025)

### DialogWrapper Integration
- **All lifecycle management delegated to DialogWrapper**
- Scanner blocking/unblocking handled automatically
- Overlay activation/deactivation managed by wrapper
- Dialog sizing, centering, and focus restoration handled by wrapper

### Main Window Integration
- Dialog launched via: `self.dialog_wrapper.open_dialog_scanner_blocked(launch_manual_entry_dialog, ...)`
- Result processed by: `_add_items_to_sales_table('manual')` callback
- Shared handler reads `dlg.manual_entry_result` attribute
- Data merged into sales table using `set_table_rows()`

## Known Limitations
## Work in Progress

- The controller logic and documentation will be updated as development continues. For now, see `vegetable_menu.py` for reference implementation and integration details.
1. **Size Behavior**: The dialog size is controlled entirely by the `.ui` file properties. The Python code applies these constraints to the QDialog.

2. **Fixed Spacer**: The 30px spacing between input fields and buttons (`verticalSpacer_3`) is fixed and will not change with dialog resizing.

3. **Input Validation**: Basic validation only (non-empty, numeric, positive). No range checking or format validation beyond these basics.

## Future Enhancements

- [ ] Add unit selection (KG, EACH, etc.)
- [ ] Add product category selection
- [ ] Add barcode/SKU field
- [ ] Add tax rate configuration
- [ ] Add recent products quick-select
- [ ] Add input field validation with visual feedback
- [ ] Add keyboard shortcuts (Enter for OK, Esc for Cancel)
- [ ] Add number formatting in price/quantity fields

## Testing Notes

- Verify dialog appears centered on main window
- Test with different parent window sizes
- Verify 30px spacing remains consistent
- Test input validation with empty, invalid, and edge-case values
- Verify overlay appears and disappears correctly
- Check scanner blocking/unblocking behavior
- Verify focus returns to sales table

## Related Files

- `/modules/sales/vegetable_entry.py` - Similar dialog for vegetable selection
- `/ui/vegetable_menu.ui` - Reference for similar button layout patterns
- `/ui/vegetable_entry.ui` - Reference for dialog structure
- `/assets/sales.qss` - Shared stylesheet

---

**Last Updated**: December 12, 2025  
**Status**: In Development
