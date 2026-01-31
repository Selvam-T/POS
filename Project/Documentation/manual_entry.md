# Manual Entry Dialog Documentation

# January 2026: Pipeline Refactor & Modern Controller Design

The manual entry dialog controller has been fully refactored to use a declarative, pipeline-based architecture, matching the Product Menu and other modern dialogs. All legacy/manual widget setup, direct findChild calls, and procedural focus/validation logic have been removed. The new design is:

## Key Design Features

- **Declarative UI Construction:** Uses `build_dialog_from_ui` for dialog creation and `require_widgets` for all widget resolution. If a widget is missing, the app fails fast and clearly during development.
- **Gating (FocusGate):** The Quantity and OK button are locked by default and only enabled after a valid product lookup. The gate manages both functional and visual state (readOnly, gray background via QSS).
- **Exclusive Inputs:** `enforce_exclusive_lineedits` ensures that typing in Product Code clears and locks Name Search, and vice versa, preventing ambiguous input.
- **Coordinator-Driven Logic:** All field relationships, validation, and focus jumps are handled by the FieldCoordinator. Casing (UPPER for code, Title for name) is enforced in the coordinator links.
- **Focus & Placeholder Management:** Focus starts on Product Code and moves to Quantity after a valid lookup. The Quantity placeholder is reactive (e.g., "Enter weight" for KG, "Enter Quantity" for EACH).
- **Data Persistence:** The price is cached in the Quantity widget at lookup time, so the OK click is fast and safe.
- **Fallback UI:** If the .ui file is missing, a programmatic fallback dialog is shown, styled for visual consistency and with clear error messaging.
- **Status Messaging:** Uses `set_dialog_info` and `set_dialog_error` to provide post-close feedback to the main window, both for success and fallback/error cases.
- **No Local Product Cache:** The controller trusts that the product cache is loaded at app startup; no local checks or reloads are performed.
- **No Manual ReadOnly/Styling:** All readOnly and label styling is handled via the .ui file or QSS, not in the controller.

## Summary

The manual entry dialog is now:
- Shorter and easier to read
- More robust and maintainable
- Consistent with the rest of the POS dialog system
- Free of legacy/manual widget setup and procedural logic

All intelligence is now declarative and pipeline-driven, ensuring a predictable, testable, and user-friendly experience.


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
- **Function**: `launch_manual_entry_dialog(parent)`
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

## Function: `launch_manual_entry_dialog(parent)`

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

## Scanner/Keyboard Behavior Under open_dialog_scanner_blocked()

Manual Entry is launched via `DialogWrapper.open_dialog_scanner_blocked()`, which enables a modal scanner block and overlay so the main window cannot accidentally receive scan input while the dialog is open. Within the dialog, behavior is produced by the combination of:

- `DialogWrapper` (overlay + modal block + cleanup/focus restore)
- `BarcodeManager` (scan-burst key swallowing + leak cleanup; leak cleanup is length-independent)

Widget behavior summary:

1. **manualProductCodeLineEdit**
    - Accepts both keyboard typing and scanner keystrokes.
    - Works with the “product code field” convention (`*ProductCodeLineEdit`), so scan-burst characters are allowed to land here.
    - Once text changes, the dialog’s `FieldCoordinator` mapping updates Name/Unit when the lookup succeeds.

2. **manualNameSearchLineEdit**
    - Accepts normal keyboard typing for name search and QCompleter selection.
    - Scanner bursts are not permitted here, so burst characters are swallowed; a rare first-character leak may briefly trigger the dropdown before cleanup removes it.

3. **manualUnitLineEdit** (read-only)
    - Does not accept keyboard edits.
    - Scanner input is not permitted; any leakage is best-effort cleaned.
    - Value is filled programmatically via coordinator mapping.

4. **manualQuantityLineEdit**
    - Accepts keyboard typing.
    - Scanner bursts are swallowed here (not a permitted scan target); if any first character leaks, it is cleaned up best-effort.

5. **OK / Cancel / X Close buttons**
    - Scanner input does not leak to the main window while the dialog is open.
    - Enter/Return is briefly suppressed during scan activity to avoid accidental button activation.

On dialog close, the wrapper restores focus to the main window (sales table) in a gated, consistent way.

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


## Pipeline Refactor (Jan 2026)

The manual entry dialog now follows the same declarative, robust pipeline as the Product Menu:

1. **Builder & Widget Resolution**
    - Uses `build_dialog_from_ui` to construct the dialog, replacing manual QDialog and layout setup.
    - All widgets are resolved in a single `require_widgets` call. If a widget is missing from the .ui, the app fails loudly during development.

2. **Gating (The "Shield")**
    - A FocusGate is defined for `manualQuantityLineEdit`, `manualUnitLineEdit`, and `btnManualOk`.
    - The gate is locked by default. The on_sync callback in the FieldCoordinator unlocks the gate only when a valid product lookup occurs.
    - The gate manages the readOnly state of the Quantity field, ensuring it turns gray when locked (via QSS).

3. **Exclusive Inputs (Dual Search)**
    - `enforce_exclusive_lineedits` is applied to the Product Code and Name Search fields. Typing in one clears and locks the other, preventing ambiguous input.

4. **Standardized Interaction**
    - Casing is enforced: Product Code is UPPERCASE, Name Search is Title Case, handled in the coordinator links.
    - Focus is managed with `QTimer.singleShot` to start on Product Code and move to Quantity after a valid lookup.

5. **Redundancy Cleanup**
    - Manual `setProperty("readOnly", "true")` calls on labels are removed; these are now handled via the .ui file or QSS.
    - The local PRODUCT_CACHE load check is removed; the app startup ensures cache is ready.

6. **Data Persistence**
    - The price is cached in the Quantity widget at lookup time, so the final OK click is fast and safe.

7. **Placeholder Policy**
    - The Quantity placeholder is reactive: e.g., "Enter Weight" for KG items, "Enter Quantity" for EACH.

8. **Standardized Cleanup**
    - All manual findChild and layout code is gone, replaced by the pipeline's `build_dialog_from_ui` and `require_widgets`.

**Summary:**
The dialog is now shorter, easier to read, and matches the Product Menu Update tab in behavior and robustness. All intelligence is declarative, not manual.

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

---

## Global Row Limit Guards (Jan 2026)

### Pre-Entry Guard
- Before the Manual Entry dialog opens, the code checks if the main sales table has reached `MAX_TABLE_ROWS`.
- If the table is full, a modal dialog informs the user and the entry dialog is not opened.
- This prevents unnecessary dialog launches and provides immediate feedback.

### In-Entry Guard
- While the dialog is open, any attempt to add a new row checks the combined total of rows in the main sales table and the dialog.
- If adding a row would exceed `MAX_TABLE_ROWS`, a modal dialog informs the user and the addition is blocked.
- This ensures the global limit is never exceeded, regardless of entry method or dialog state.

### Dialog Wrapper Handling
- The dialog wrapper now handles cases where the dialog returns `None` (e.g., when the table is full or the parent is misconfigured) without error.
- Overlay and scanner state are restored cleanly, and no error is shown to the user.

---
