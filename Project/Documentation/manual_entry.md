# Manual Entry Dialog Documentation

## Overview
The Manual Entry dialog allows users to manually input product information when items cannot be processed through the standard vegetable entry or barcode scanning methods. This is useful for miscellaneous items, special products, or when the barcode scanner is unavailable.

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
      'total': float            # quantity × unit_price
  }
  ```
- **Cancelled/Error**: `None`

### Process Flow

1. **Load UI**
   - Loads `manual_entry.ui` from UI directory
   - Handles missing file gracefully

2. **Create Dialog**
   - Creates QDialog with modal behavior
   - Sets window title: "Manual Product Input"
   - Window flags: Dialog | CustomizeWindowHint | WindowTitleHint | WindowCloseButtonHint
   - Removes min/max buttons, keeps title bar and close button

3. **Apply Size Constraints**
   - Minimum size: 350×310px
   - Preferred size: 500×350px
   - Maximum size: Unlimited (from UI)

4. **Apply Styling**
   - Loads `sales.qss` and applies stylesheet
   - Includes specific styles for manual entry dialog

5. **Overlay Management**
   - Activates dimming overlay on main window
   - Blocks scanner input during dialog
   - Centers dialog on parent window

6. **Input Validation**
   - Product Name: Cannot be empty
   - Quantity: Must be a valid positive number
   - Unit Price: Must be a valid positive number
   - Calculates total: quantity × unit_price

7. **Cleanup**
   - Removes overlay
   - Restores focus to main window
   - Unblocks scanner input
   - Restores focus to sales table

## Styling (sales.qss)

### Dialog Background
```css
QWidget#manualEntryDialog {
    background-color: #EFF5F9;  /* Light blue background */
    font-family: "Verdana";
}
```

### Labels
- Font size: 11pt
- Color: #2C3E50 (dark grey)
- Font weight: Bold
- Font family: "Verdana"

### Input Fields
- Font size: 10pt
- Padding: 8px
- Background: #FFFBE6 (pale yellow)
- Border: 2px solid #BDC3C7 (grey)
- Border-radius: 4px

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

## Usage Example

```python
from modules.sales.manual_entry import open_manual_entry_dialog

# In your sales frame or main window:
product_data = open_manual_entry_dialog(self)

if product_data:
    print(f"Product: {product_data['product_name']}")
    print(f"Qty: {product_data['quantity']}")
    print(f"Price: ${product_data['unit_price']:.2f}")
    print(f"Total: ${product_data['total']:.2f}")
    # Process the product data...
else:
    print("Dialog was cancelled")
```

## Integration Points

### Scanner Manager Integration
- Dialog blocks scanner input via `barcode_manager._start_scanner_modal_block()`
- Unblocks scanner on dialog close via `barcode_manager._end_scanner_modal_block()`

### Overlay Manager Integration
- Activates dimming overlay: `parent.overlay_manager.toggle_dim_overlay(True)`
- Deactivates on close: `parent.overlay_manager.toggle_dim_overlay(False)`

### Sales Table Integration
- Restores focus to sales table on close: `parent._refocus_sales_table()`

## Known Limitations

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
