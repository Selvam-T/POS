# BarcodeManager — Documentation

## Overview

`BarcodeManager` (located in `modules/devices/barcode_manager.py`) is the central component responsible for all barcode scanner integration, event filtering, and scanner-related logic in the ANUMANI POS System. It abstracts away the complexities of scanner input, modal blocking, and focus management, providing a clean interface for the main application and dialogs.

---

## Key Responsibilities

- **Scanner Event Filtering:**
  - Installs itself as a global event filter to intercept and process all barcode scanner input events.
  - Detects scan bursts and routes barcode data to the appropriate handlers.

- **Modal Scanner Blocking:**
  - Provides methods to temporarily block scanner input during modal dialogs or critical UI operations.
  - **Input Whitelist for Modal Dialogs:** Allows keyboard input in specific editable fields during modals (see Whitelisted Fields below).
  - Ensures that scanner input does not interfere with dialogs or data entry when the UI is in a modal state.
  - Automatically unblocks scanner input when dialogs are closed.

## Whitelisted Fields for Modal Input

### Generalized Product Code Field Detection (2025-12-30)

Barcode scanning is now allowed in any field whose `objectName` ends with `ProductCodeLineEdit` (e.g., `addProductCodeLineEdit`, `removeProductCodeLineEdit`, `updateProductCodeLineEdit`, etc.). This convention applies across all dialogs that support barcode entry.

**Editable Fields:**
- Any `QLineEdit` whose `objectName` ends with `ProductCodeLineEdit` (for product code entry in any dialog)
- `qtyInput` — Quantity input in manual entry and vegetable entry dialogs
- `refundInput` — Refund amount input
- Other fields as needed for manual entry (see code for full list)

**Purpose:**
- Prevents barcode scanner leaks while allowing barcode entry only in the correct product code field for each dialog
- Automatically supports new dialogs as long as they follow the naming convention
- Reduces code duplication and improves maintainability

**Implementation:**
- BarcodeManager checks the focused widget's `objectName` using `.endswith('ProductCodeLineEdit')` to determine if barcode input is allowed
- If focus is not in a product code field, barcode input is blocked, the leaked character is cleaned up, and an error message is shown in the dialog's status label (if present)

- **Barcode Override Handling:**
  - Supports barcode override logic, allowing certain dialogs or UI states to temporarily take exclusive control of scanner input.
  - Ensures that override logic is safely installed and removed as dialogs open and close.

- **Scanner Cleanup and Lifecycle:**
  - Manages scanner resource initialization and cleanup.
  - Ensures that scanner event filters and overrides are properly removed on application exit or logout.

---

## Integration Points

- **Main Window (`main.py`):**
  - Instantiates `BarcodeManager` and installs it as an event filter for the application or main window.
  - Delegates all scanner blocking, override, and cleanup logic to `BarcodeManager`.
  - No scanner logic remains in `main.py` — all related helpers and state are now encapsulated in `BarcodeManager`.

- **Dialogs and Panels:**
  - Use the unified dialog wrapper (`open_dialog_wrapper`) to automatically block/unblock scanner input via `BarcodeManager` during modal dialogs.
  - Dialogs that require exclusive scanner input can use the override mechanism provided by `BarcodeManager`.

---

## Example Usage

```python
# In main.py
self.barcode_manager = BarcodeManager(self)
app = QApplication.instance()
if app is not None:
    self.barcode_manager.install_event_filter(app)
else:
    self.barcode_manager.install_event_filter(self)

# In dialog wrapper
if not is_product_menu:
    self.barcode_manager._start_scanner_modal_block()
# ...
self.barcode_manager._end_scanner_modal_block()
```

---

## Extensibility

- To add new scanner-related features, extend `BarcodeManager` rather than adding logic to `main.py` or dialogs.
- For custom scanner handling in a dialog, use the override mechanism to temporarily redirect scanner input.

---

### Changelog

- **2025-12-30:** Barcode scan logic generalized to allow scanning in any field whose objectName ends with `ProductCodeLineEdit`. No need to hardcode field names for each dialog. Error feedback and cleanup are handled generically.

---

_Last updated: December 30, 2025_
