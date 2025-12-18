# Vegetable Menu Dialog Documentation

## Overview
The `VegetableMenuDialog` is a PyQt5 dialog for editing vegetable product information including name, unit of measure, pricing, and supplier details. It allows selecting from up to 16 predefined vegetable slots and updating their properties.

## UI Structure

### Dialog Properties
- **Size:** 600x600 (minimum 400x450)
- **Layout:** `QVBoxLayout` with zero margins
- **Style:** Applied from `menu.qss` under `QDialog#VegetableMenuDialog` section

### Title Bar (`customTitleBar`)
- Custom frame with horizontal layout
- **Components:**
  - Left spacer
  - `titleLabel`: Displays "Edit Vegetables"
  - Right spacer
  - `customCloseBtn`: X button (30x30) for closing dialog

### Content Area (`contentLayout`)
- Left/right margins: 20px
- Contains a `QGridLayout` (`inputFieldsLayout`) with 10px spacing

### Input Fields Grid

**Row 0: Vegetable Selection**
- `lblChoose`: "Choose Vegetable * :"
- `comboVegetable`: Dropdown with "Select vegetable to update" placeholder + 16 vegetable slots

**Row 1: Spacer**
- `gridRowSpacer`: Fixed 40px height spacer between selection and fields

**Row 2: Product Code**
- `lblProductCode`: "Product code :"
- `inputProductCode`: Read-only QLineEdit

**Row 3: Product Name** (Required)
- `lblProductName`: "Product Name * :"
- `inputProductName`: Editable, placeholder "Enter product name"

**Row 4: Unit** (Required)
- `lblUnit`: "Unit * :"
- `comboUnit`: Dropdown with options:
  - "Select Unit" (default)
  - "KG"
  - "EACH"

**Row 5: Selling Price** (Required)
- `lblSellingPrice`: "Selling Price * :"
- `inputSellingPrice`: Editable, placeholder "Enter selling price"

**Row 6: Cost Price** (Optional)
- `lblCostPrice`: "Cost Price :"
- `inputCostPrice`: Editable, placeholder "Optional"

**Row 7: Supplier** (Optional)
- `lblSupplier`: "Supplier :"
- `inputSupplier`: Editable, placeholder "Optional"

### Error Display
- `lblError`: Center-aligned label for validation messages
- Surrounded by vertical spacers (15px each)

### Button Layout
- **Horizontal layout with 10px spacing**
- Left spacer for right alignment
- `pushButton_ok`: "ACCEPT" button (min height 50px, font 12pt)
- `pushButton_cancel`: "CANCEL" button (min height 50px, font 12pt)

## Key Features

### Unit Selection Logic
- **KG mode:** Vegetable entry expects weight from weighing scale
- **EACH mode:** Vegetable entry does not expect scale reading, uses piece count
- Controller must handle unit-specific behavior in `vegetable_entry.py`

### Required vs Optional Fields
- **Required (marked with *):**
  - Choose Vegetable
  - Product Name
  - Unit
  - Selling Price
- **Optional:**
  - Cost Price
  - Supplier

### Styling
- Input fields: Yellow background (#FFFBE6), 2px borders, 4px radius
- Focus: Brighter yellow (#FFF9C4), blue border (#4682B4)
- Read-only: Gray background (#f5f5f5)
- Buttons: Green (ACCEPT) and red (CANCEL) with hover/pressed states
- All styling defined in `assets/menu.qss`

## Implementation Notes

### Controller (`vegetable_menu.py`)
- Loads UI from `vegetable_menu.ui`
- Populates `comboVegetable` from vegetable data source
- Handles vegetable selection to populate fields
- Validates required fields before accepting
- Saves updated vegetable data
- Emits `configChanged` signal on successful save

### Data Persistence
- Loads vegetable configurations from `AppData/vegetables.json` (or similar)
- Saves using functions from `modules/wrappers/settings.py`

### Validation Rules
1. Vegetable must be selected (not "Select vegetable to update")
2. Product Name must not be empty
3. Unit must be selected (KG or EACH, not "Select Unit")
4. Selling Price must be a valid number
5. Cost Price (if provided) must be a valid number
6. Supplier is optional

## Example Workflow
1. User opens dialog
2. Selects vegetable from `comboVegetable`
3. Fields populate with existing data
4. User edits Product Name, selects Unit, updates prices
5. Optionally adds Cost Price and Supplier
6. Clicks ACCEPT to validate and save
7. Dialog emits `configChanged` and closes

## Related Files
- **UI:** `ui/vegetable_menu.ui`
- **Controller:** `modules/menu/vegetable_menu.py`
- **Styles:** `assets/menu.qss`
- **Config:** `config.py` (VEG_SLOTS constant)
- **Data:** `AppData/vegetables.json`

---

*Last updated: December 18, 2025*
