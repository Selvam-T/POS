
# sales_frame_setup.py Documentation

**Location:** `modules/sales/sales_frame_setup.py`

## Purpose
This module encapsulates the setup logic for the sales frame UI in the POS application. It is responsible for loading the `sales_frame.ui` file, inserting it into the main window's placeholder, and wiring up the main sales table widget and total value label for use throughout the application.

## Refactor Overview
The logic for setting up the sales frame UI has been refactored out of `main.py` and placed in this module. This improves modularity and maintainability by isolating all sales frame UI setup in one place.

## Usage
- The function `setup_sales_frame(main_window, UI_DIR)` should be called from the `MainLoader` class in `main.py`.
- It expects:
  - `main_window`: The main application window instance (typically `self` in `MainLoader`).
  - `UI_DIR`: The directory path where UI files are stored.
- This function will:
  - Load the `sales_frame.ui` file.
  - Insert the loaded widget into the `salesFrame` placeholder in the main window.
  - Set `main_window.sales_table` to the main sales table widget for later use (e.g., focus management, data updates).
  - **Bind the `totalValue` label to the sales table for automatic total updates.**

## Total Value Binding
After the sales table is set up, the `totalValue` label (a `QLabel` in the UI) is automatically bound to the table using `bind_total_label`. This ensures the displayed total is always up to date as products are added, removed, or quantities changed.

## Canonical Unit Handling and Robust Merging (2026 Update)

- All sales table operations (add, update, delete, barcode scan, dialog transfer) use only canonical units: "Kg" or "Each".
- All merging, duplicate detection, and display logic is handled via a canonical data list and table rebuild (`set_table_rows`).
- KG items are always read-only; EACH items are always editable.
- Barcode scanning blocks KG items and prompts the user to use Vegetable Entry.
- All table operations are robust and unified for maintainability.

**Example:**
```python
from modules.sales.sales_frame_setup import setup_sales_frame
# ...
setup_sales_frame(self, UI_DIR)
# self.sales_table is now available for use
# The totalValue label is automatically bound and updates in real time
```

## Notes
- All additional sales frame setup logic should be added to this module to keep `main.py` clean.
- If you need to access the sales table widget elsewhere in the main window, use `self.sales_table` after calling this setup function.

## Related Files
- `main.py`: Calls `setup_sales_frame` during main window initialization.
- `ui/sales_frame.ui`: The Qt Designer UI file loaded by this module.
- `modules/sales/salesTable.py`: Provides `setup_sales_table` and `bind_total_label` for table and total value management.

---
*Last updated: December 2, 2025*