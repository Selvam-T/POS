# Input Validation Documentation

This document outlines the validation requirements and logic for all dialogs and frames in the POS application. It will be updated as development progresses.

## General Guidelines
- Centralized validation module to be reused across dialogs and frames.
- Error messages propagate to appropriate UI elements (QLabel, status bar, etc.).

## Validation Rules
### Numeric Fields
- **Quantity**: DECIMAL(10,3), min 0.01 (KG) or 1 (unit), max 9999
- **Unit Price**: DECIMAL(13,2), min 0.1, max 5000
- **Total Price**: DECIMAL(15,2), min 0, max 10000
- **Grand Total**: DECIMAL(17,2), min 0, max 100000

### String Fields
- All user string inputs limited to 15 characters.

## Dialog/Frame Specific Validation
### Sales Frame
- Quantity: Integer (unit) or float (KG), validated per above.
- Error messages to main window status bar.

### Vegetable Entry Table
- Editable quantity, same validation as sales table.

### Manual Entry Dialog
- Product name: string, not empty, max 15 chars.
- Quantity: integer, not empty.
- Unit price: float, not empty.
- Error messages to `lblError` QLabel.

### Payment Frame
- Amount tendered, change due, refund: float.
- Refund: barcode must exist in DB, else error.
- Error messages to main window status bar.

### Menu Frame
- Error/info messages to dedicated QLabel.

### Admin Menu
- New password: min 8 chars.
- New email: standard email validation.

### Reports Dialog
- Date/time selection: validate that "from" is not after "to".

### Vegetable Menu
- comboVegetable, product name, unit, selling price: mandatory, not empty.
- Product name: string, max 15 chars.
- Unit, selling price, cost price: float.
- Supplier: optional.

### Product Menu
- **ADD TAB**: product code, product name, selling price: mandatory, not empty.
- Product code: must exist in DB.
- Product name: string, max 15 chars.
- Unit: default value, no validation.
- Supplier: optional.
- **REMOVE TAB**: search by name can be empty/any string; product code must exist if provided.
- **UPDATE TAB**: product name mandatory, max 15 chars; selling price mandatory, float; cost price optional, float; supplier optional.

### Other Dialogs
- Greeting and logout: no user input.
- History: search only, not validation.

## Validation Timing
- Mandatory field checks are performed only when the dialog action button (e.g., OK, Submit) is clicked.
- Input field value validation is performed after typing (on field focus-out or input completion).

## Error Propagation
- Error messages are routed to the appropriate UI element depending on the dialog/frame.
- For dynamic error styling, use helpers from ui_utils/ui_feedback.py.

## Implementation Notes

Validation functions now return a tuple: (is_valid, error_message). This allows UI code to display specific error messages and handle focus management consistently.

- Quantity validation for tables (salesTable, vegEntryTable) enforces that quantity cannot be empty or zero. If violated, the error message is: "Minimum qty is 1, delete row if you don't want item."
- All other validation functions provide clear error messages for invalid input.

Update this section as new validation logic is added or integrated.

## Folder and File Location (Updated)
- input_validation.py has been moved from modules/validation/ to modules/ui_utils/.
- The validation folder has been deleted.
- All imports should now use:
  ```python
  from modules.ui_utils import input_validation
  ```
- Error message dynamic styling is now handled by ui_utils/ui_feedback.py.

---
*Update this document as new validation requirements are discovered or implemented.*
