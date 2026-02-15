## Refactoring: Sales Frame Setup

The setup logic for the sales frame UI has been moved from `MainLoader.__init__` in `main.py` to a dedicated function in `modules/sales/sales_frame_setup.py`.

### How it works
- The function `setup_sales_frame(self, UI_DIR)` is called from `MainLoader.__init__`.
- This function loads the sales frame UI, wires up all widgets and buttons, and sets `self.sales_table` on the main window instance.
- Other methods in `MainLoader` (such as `_refocus_sales_table`) can use `self.sales_table` as before, because the setup function assigns it as an attribute.
- No return value is needed from `setup_sales_frame` because it modifies the main window instance directly.

### Why this is beneficial
- Keeps `main.py` cleaner and more maintainable.
- Groups all sales frame UI logic in a single, reusable module.
- Maintains compatibility with existing code that relies on `self.sales_table`.
## Why _perform_logout Should Remain in main.py

The `_perform_logout(self)` method is responsible for handling the core application-level logout logic, including:

- Stopping hardware devices (such as the scanner)
- Setting internal flags to allow the main window to close
- Closing the main application window and quitting the app

**Reason for Placement:**

This logic is tightly coupled to the main application window (`MainLoader`) and its lifecycle. Placing `_perform_logout` in `main.py` ensures that only the main window manages application shutdown and device cleanup, maintaining a clear separation of concerns. The logout dialog (in `logout_menu`) is responsible only for user interaction (confirmation, etc.), not for controlling the main window or device state.

**How _perform_logout is Accessed:**

The only intended way to trigger `_perform_logout` is via the Logout menu option:

1. The user clicks the Logout button in the menu frame.
2. This opens the logout dialog (from `logout_menu`).
3. Upon user confirmation, the dialog calls back to `MainLoader._perform_logout()` to perform the actual logout and application exit.

There are no other direct calls to `_perform_logout` in the codebase, ensuring that logout and shutdown are always user-confirmed and managed by the main window.
# Main Window Loader (`main.py`) — Documentation

## Overview

`main.py` is the entry point and central orchestrator for the ANUMANI POS System. It composes the main application window by dynamically loading modular UI components, manages dialog and panel launching, and coordinates barcode scanner integration and event filtering. The file is designed for maintainability, modularity, and a modern user experience.

---

## Key Responsibilities

- **UI Composition:**
  - Loads and assembles `main_window.ui`, `sales_frame.ui`, `payment_frame.ui`, and `menu_frame.ui` at runtime using PyQt5's `uic` module.
  - Applies a global QSS stylesheet from `assets/main.qss` for consistent theming.
  - Sets up header layout (`infoSection`) for date, company, and day/time display.

- **Dialog and Panel Launching:**
  - All dialogs and panels (menu, sales, payment, etc.) are launched using a single unified wrapper: `DialogWrapper.open_dialog_scanner_blocked()`.
  - Dialog and panel functions are now consistently named using the `launch_*_dialog` or `launch_*_entry_dialog` pattern (e.g., `launch_logout_dialog`, `launch_product_dialog`, `launch_vegetable_entry_dialog`).
  - This wrapper standardizes overlay management, dialog sizing/centering, and barcode scanner blocking/unblocking.
  - All dialog launcher methods in `MainLoader` delegate to this wrapper for consistent behavior.
  - **Clean callback pattern:** Dialog launchers use simple lambda callbacks (e.g., `lambda: self._add_items_to_sales_table('vegetable')`) instead of inline logic.
  - **Shared data handler:** `_add_items_to_sales_table(source_type)` method handles data transfer from both vegetable and manual entry dialogs.

- **Barcode Scanner Management:**
  - Integrates with `BarcodeManager` (from `modules/devices/barcode_manager.py`) for global event filtering, scan burst detection, and modal blocking.
  - All scanner logic, event filtering, and modal block/override handling are managed by `BarcodeManager`.

- **Menu and Sales Frame Wiring:**
  - Wires right-side menu buttons to their respective dialog launcher methods.
  - Wires sales frame buttons (e.g., Vegetable Entry, Manual Entry, On Hold, View Hold, Cancel All) to their dialog launcher methods.
  - Sets up icons, tooltips, and fallback text for menu buttons.
  - Cancel All button opens confirmation dialog; on confirm, clears all sales table rows and resets total to $0.00.

- **ReceiptContext Gating (Feb 2026):**
  - `receipt_context` keys: `active_receipt_id`, `source`, `status`.
  - `manual_entry` and `vegetable_menu` launchers are blocked when `source == HOLD_LOADED` (held receipts are read-only).
  - `hold_sales` launcher requires sales table rows > 0, `active_receipt_id is None`, and `source == ACTIVE_SALE`.
  - `view_hold` launcher requires sales table rows == 0, `active_receipt_id is None`, and payment total effectively zero; otherwise a status hint is shown.
  - Cancel All still requires an active sale (table rows) as before.
 
  ### Payment commit (Feb 2026)

  - The application finalizes payments in `main.py` to ensure all DB writes
    (receipt counter, receipts header, receipt_items, receipt_payments) occur
    inside a single atomic transaction. See `Documentation/payment_processing.md`
    for full details and the distinction between new-sale vs held-receipt flows.

- **Sales Table Management:**
  - Loads and configures the sales table, binds the total label, and manages row operations.
  - **Unit-aware editable states:** KG items have read-only quantity cells, EACH items have editable quantity cells.
  - **Mixed table rebuilding:** Uses `set_table_rows()` when combining KG and EACH items from dialogs.
  - **Barcode blocking:** KG items cannot be added via barcode scan (shows message to use Vegetable Entry).
  - **PRODUCT_CACHE integration:** Fetches product info as 4-tuple `(found, name, price, unit)` for unit-based behavior.

- **Sales Dialog Data Transfer (Refactored Dec 2025):**
  - **Unified handler:** `_add_items_to_sales_table(source_type)` processes results from both vegetable and manual entry dialogs.
  - **Data normalization:** Converts different dialog result formats (`vegetable_rows` property vs. `manual_entry_result` attribute) to unified row structure.
  - **Smart merging:** Handles duplicate detection and quantity merging for vegetable items (EACH: increment count, KG: add weights).
  - **Simple callbacks:** Dialog launchers use `on_finish=lambda: self._add_items_to_sales_table('vegetable')` instead of 100+ line inline functions.
  - **Maintainability:** Eliminates ~200 lines of duplicated code across `launch_vegetable_entry_dialog()` and `launch_manual_entry_dialog()`.

- **Window and Application Behavior:**
  - Disables the main window's close (X) button to enforce logout flow.
  - Handles focus change logging and debug helpers.
  - Manages application exit and cleanup on logout.

---

## Notable Implementation Details

- **Dynamic UI Loading:**
  - All `.ui` files are loaded at runtime, allowing for rapid UI iteration without recompilation.

- **Unified Dialog Wrapper:**
  - `open_dialog_wrapper()` is the single entry point for all modal dialogs and panels, ensuring consistent overlay/scanner handling and sizing.
  - Dialog and panel functions are imported and aliased for clarity, e.g.:
    ```python
    from modules.menu.logout_menu import launch_logout_dialog
    from modules.sales.vegetable_entry import launch_vegetable_entry_dialog as launch_vegetable_entry_dialog
    ```
  - Example usage:
    ```python
    self.open_dialog_wrapper(launch_product_dialog, initial_mode='edit')
    self.open_dialog_wrapper(launch_vegetable_entry_dialog)
    ```

- **Barcode Scanner Blocking:**
  - During modal dialogs, the scanner is blocked and the background is dimmed to prevent stray input.
  - Scanner block is automatically released when dialogs close.

- **Menu Button Wiring:**
  - Menu buttons are mapped to icons and tooltips, and are programmatically wired to their respective dialog launcher methods.

- **Focus and Debug Helpers:**
  - Includes helpers for focus path tracing, widget description, and verbose debug output (toggleable via config).

- **Extensibility:**
  - To add a new dialog or panel, implement its controller and simply call `self.open_dialog_wrapper(new_dialog_func)` from a launcher method.

---

## Global Row Limit Guards (Jan 2026)

### Overview
To robustly enforce the global `MAX_TABLE_ROWS` limit for the sales table, the following guard mechanisms are implemented for all entry dialogs (vegetable, manual, barcode, etc.):

#### 1. Pre-Entry Guard
- Before opening any entry dialog (e.g., vegetable or manual entry), the code checks if the main sales table is already at the row limit.
- If the table is full, a modal dialog informs the user and the entry dialog is not opened.
- This prevents unnecessary dialog launches and provides immediate feedback.

#### 2. In-Entry Guard
- While an entry dialog is open, any attempt to add a new row checks the combined total of rows in the main sales table and the entry dialog.
- If adding a row would exceed `MAX_TABLE_ROWS`, a modal dialog informs the user and the addition is blocked.
- This ensures the global limit is never exceeded, regardless of entry method or dialog state.

#### 3. Dialog Wrapper Handling
- The unified `DialogWrapper` now gracefully handles cases where an entry dialog returns `None` (e.g., when the table is full or the parent is misconfigured).
- No error is shown to the user in these cases; the overlay and scanner state are restored cleanly.
- This prevents confusing error messages like "Expected QDialog, got <class 'NoneType'>" and ensures a smooth user experience.

Additional behavior:
- If a dialog throws an unexpected exception (hard-fail), `DialogWrapper` logs details to `log/error.log` and shows a short StatusBar hint after overlay/scanner cleanup.

#### 4. Consistency
- These guards are implemented in both `launch_vegetable_entry_dialog` and `launch_manual_entry_dialog`, and should be used in any future entry dialogs.
- All dialog launches in `main.py` and related modules use the wrapper, ensuring consistent enforcement and feedback.

---

## File Structure Reference

- `main.py` — Main application loader and orchestrator
- `config.py` — Configuration constants (colors, paths, debug flags)
- `assets/main.qss` — Global stylesheet
- `ui/` — Qt Designer UI files
- `modules/` — Modular controllers for dialogs, sales, devices, etc.
- `Documentation/` — Project documentation (this file)

---

## See Also

- `Documentation/dialog_pipeline.md`: Details on the unified dialog launching standard
- `Documentation/error_logging_and_fallback.md`: Hard-fail vs soft-fail and StatusBar policy
- `Project_Journal.md`: In-depth development notes and rationale
- `Documentation/scanner_input_infocus.md`: Barcode scanner routing and debug options
- `Documentation/logout_and_titlebar.md`: Logout dialog and custom title bar

---
_Last updated: January 22, 2026_
