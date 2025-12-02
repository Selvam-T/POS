# Main Window Loader (`main.py`) — Documentation

## Overview

`main.py` is the entry point and central orchestrator for the ANUMANI POS System. It composes the main application window by dynamically loading modular UI components, manages dialog and panel launching, and coordinates barcode scanner integration and event filtering. The file is designed for maintainability, modularity, and a modern user experience.

---

## Key Responsibilities

- **UI Composition:**
  - Loads and assembles `main_window.ui`, `sales_frame.ui`, `payment_frame.ui`, and `menu_frame.ui` at runtime using PyQt5's `uic` module.
  - Applies a global QSS stylesheet from `assets/style.qss` for consistent theming.
  - Sets up header layout (`infoSection`) for date, company, and day/time display.

- **Dialog and Panel Launching:**
  - All dialogs and panels (menu, sales, payment, etc.) are launched using a single unified wrapper: `open_dialog_wrapper()`.
  - Dialog and panel functions are now consistently named using the `launch_*_dialog` or `launch_*_entry_dialog` pattern (e.g., `launch_logout_dialog`, `launch_product_dialog`, `launch_vegetable_entry_dialog`).
  - This wrapper standardizes overlay management, dialog sizing/centering, and barcode scanner blocking/unblocking.
  - All dialog launcher methods in `MainLoader` delegate to this wrapper for consistent behavior.

- **Barcode Scanner Management:**
  - Integrates with `BarcodeManager` (from `modules/devices/barcode_manager.py`) for global event filtering, scan burst detection, and modal blocking.
  - All scanner logic, event filtering, and modal block/override handling are managed by `BarcodeManager`.

- **Menu and Sales Frame Wiring:**
  - Wires right-side menu buttons to their respective dialog launcher methods.
  - Wires sales frame buttons (e.g., Vegetable Entry, Manual Entry, On Hold, View Hold, Cancel Sale) to their dialog launcher methods.
  - Sets up icons, tooltips, and fallback text for menu buttons.

- **Sales Table Management:**
  - Loads and configures the sales table, binds the total label, and manages row operations.

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
    from modules.menu.logout_menu import open_logout_dialog as launch_logout_dialog
    from modules.sales.vegetable_entry import open_vegetable_entry_dialog as launch_vegetable_entry_dialog
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

## File Structure Reference

- `main.py` — Main application loader and orchestrator
- `config.py` — Configuration constants (colors, paths, debug flags)
- `assets/style.qss` — Global stylesheet
- `ui/` — Qt Designer UI files
- `modules/` — Modular controllers for dialogs, sales, devices, etc.
- `Documentation/` — Project documentation (this file)

---

## See Also

- `dialog_wrapper.md` (if present): Details on the unified dialog launching standard
- `Project_Journal.md`: In-depth development notes and rationale
- `Documentation/scanner_input_infocus.md`: Barcode scanner routing and debug options
- `Documentation/logout_and_titlebar.md`: Logout dialog and custom title bar

---
_Last updated: December 2, 2025_
