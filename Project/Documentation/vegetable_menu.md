# Vegetable Menu Dialog Documentation


## Pipeline-Compliant Refactor Overview
The Vegetable Menu is now a fully declarative, pipeline-driven dialog for managing reserved vegetable slots `VEG01`–`VEG16`. It is DB-backed and uses standardized builder, widget resolution, and interaction patterns for robust, maintainable, and high-integrity data management.

### Key Architectural Changes
- **Builder Pattern:** Uses `build_dialog_from_ui` for dialog creation, handling geometry, flags, and QSS.
- **Single-Pass Widget Resolution:** All widgets are resolved in a single `require_widgets` block with hard-fail validation.
- **Emergency Fallback:** If the designer file is missing, `build_error_fallback_dialog` provides a consistent emergency UI.

### Slot Management (VEG01–VEG16)
- **Cache-Aware Startup:** On launch, the slot chooser iterates slots 1–16. If a product exists in `PRODUCT_CACHE`, it displays the real name; otherwise, it shows a placeholder.
- **Atomic Rewrite:** On save/remove, all slots are gathered, sorted A–Z, deleted, and refilled sequentially to maintain order and integrity.

### Visual & Focus Logic
- **Master Trigger:** The slot chooser acts as the gatekeeper, controlling form state and focus.
- **FocusGate:** Locks the Unit ComboBox and applies QSS for grayed-out appearance when no slot is selected.
- **Placeholder Policy:** Placeholders are wiped when the gate is closed and restored only when a slot is selected.
- **Conditional Jumps:** Focus jumps to Cancel for populated slots (safety) and to Product Name for empty slots (invitation to add).

### Shared Interaction Engine
- **Coordinator Wiring:** FieldCoordinator manages real-time mapping between chooser and form, Enter navigation, and sticky focus.
- **Standardized Markup:** `input_handler.wire_markup_logic` provides instant markup calculation, showing "NA" if either price is missing or cost is zero.
- **Correction Logic:** Error labels clear instantly when the user provides a valid correction.

### Validation & Feedback
- **Validation:** Product Name enforces "at least one letter" and checks for duplicates. Price/Cost use standardized handlers. Supplier enforces minimum length.
- **Error Propagation:** DB failures and rewrite errors are logged and queued for post-close StatusBar feedback. Success/failure intents use `set_dialog_main_status_max` and `set_dialog_error` for consistent user messaging.

### Outcome
This refactor eliminates 150+ lines of repetitive code, replacing manual widget handling with a centralized, utility-driven pipeline. The Vegetable Menu now acts as a specialized Slot Manager with professional feedback and high data integrity.

## UI Structure

### Dialog Properties
- **Size:** 600x600 (minimum 400x450)
- **Layout:** `QVBoxLayout` with zero margins
- **Style:** Applied from `dialog.qss` under `QDialog#VegetableMenuDialog` section

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


**Vegetable Selection**
- `vegMChooseLabel`: "Choose Vegetable * :"
- `vegMChooseComboBox`: Dropdown with placeholder + 16 vegetable slots (names populated from `PRODUCT_CACHE`)

**Row 1: Spacer**
- `gridRowSpacer`: Fixed 40px height spacer between selection and fields


**Product Code**
- `vegMProductCodeLabel`: "Product code :"
- `vegMProductCodeLineEdit`: Read-only QLineEdit (filled based on chosen slot)


**Product Name** (Required)
- `vegMProductNameLabel`: "Product Name * :"
- `vegMProductNameLineEdit`: Editable


**Unit** (Required)
- `vegMUnitLabel`: "Unit * :"
- `vegMUnitComboBox`: Dropdown with options:
  - "Select Unit" (default)
  - "KG"
  - "EACH"


**Selling Price** (Required)
- `vegMSellingPriceLabel`: "Selling Price * :"
- `vegMSellingPriceLineEdit`: Editable


**Row 6: Cost Price** (Optional)
- `vegMCostPriceLabel`: "Cost Price :"
- `vegMCostPriceLineEdit`: Editable, placeholder "Optional"


**Row 7: Supplier** (Optional)
- `vegMSupplierLabel`: "Supplier :"
- `vegMSupplierLineEdit`: Editable, placeholder "Optional"

### Status / Error Display
- `vegMStatusLabel`: Uses `ui_feedback` status properties for QSS-driven success/error styles.

### Button Layout
- **Horizontal layout with 10px spacing**
- Left spacer for right alignment
- `pushButton_ok`: "ACCEPT" button (min height 50px, font 12pt)
- `pushButton_cancel`: "CANCEL" button (min height 50px, font 12pt)

## Key Features

### Slot Semantics
- Slots are reserved product codes: `Veg01`–`Veg16`.
- The dialog rewrites these slots after every update by sorting vegetables A–Z and reassigning sequentially.

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
- All styling defined in `assets/dialog.qss`

## Implementation Notes

### Controller
Implemented in `modules/menu/vegetable_menu.py`.

Key behaviors:
- Uses `FieldCoordinator` to synchronize slot selection → form fields and to control Enter-to-next navigation.
- Performs input parsing/validation via `input_handler` and `input_validation`.
- Uses `ui_feedback` for all status/error display.
- Uses opt-in `placeholder_mode='reactive'` on the slot link so placeholders show only when a synced field is empty.
- Uses `coord.register_validator(...)` so an error clears automatically when the offending field becomes valid.

### Data Persistence
- Reads via `get_product_full(code)`.
- Writes via `delete_product(code)` and `add_product(...)`.
- `PRODUCT_CACHE` is updated in-place by the DB layer during these operations.

### Error handling and messaging

Vegetable Menu uses dialog-local status (`vegMStatusLabel`) for immediate user feedback.

Additional routing:

- DB exceptions are logged to `log/error.log` and queued as **post-close** StatusBar messages.
- Rewrite failures (delete/add returning `(ok=False, msg)`) are logged, and a post-close StatusBar error is queued.
- While the modal is open, the dialog avoids showing StatusBar messages directly (overlay UX).

See: `Documentation/error_logging_and_fallback.md` for hard-fail vs soft-fail definitions.

### Validation Rules (current)
- Slot must be selected.
- Product name is required.
- Unit must not be "Select Unit".
- Selling price is required and must be a valid number.
- Cost price is optional; when provided it must be a valid number.
- Supplier is optional and must pass `validate_supplier` rules.

## Example Workflow
1. User opens dialog
2. Selects vegetable from `comboVegetable`
3. Fields populate with existing data
4. User edits Product Name, selects Unit, updates prices
5. Optionally adds Cost Price and Supplier
6. Clicks ACCEPT to validate and save
7. Dialog emits `configChanged` and closes

## Related Files
- UI: `ui/vegetable_menu.ui`
- Controller: `modules/menu/vegetable_menu.py`
- Coordinator: `modules/ui_utils/focus_utils.py`
- Validation: `modules/ui_utils/input_handler.py`, `modules/ui_utils/input_validation.py`
- Feedback: `modules/ui_utils/ui_feedback.py`
- Styles: `assets/dialog.qss`

---

*Last updated: January 22, 2026*
