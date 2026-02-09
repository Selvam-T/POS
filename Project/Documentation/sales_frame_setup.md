
# sales_frame_setup.py Documentation

**Location:** `modules/sales/sales_frame_setup.py`

## Purpose
This module encapsulates the sales frame controller that loads `sales_frame.ui`, mounts it into the placeholder on `MainLoader`, configures the table/total widgets, and exposes signals so the rest of the app can react to sales-frame actions without digging into the UI internals.

## Refactor Overview
The sales frame setup moved out of `main.py` and is now embodied by the `SalesFrame` `QObject` controller exported from this module. It still handles loading the UI, applying the sales stylesheet, wiring the add/receipt buttons, and saving the table reference on `main_window`, but it additionally emits signals so `MainLoader` can drive payment/hold workflows from a shared `ReceiptContext`.

## Usage
- Call `SalesFrame` via `setup_sales_frame(main_window, UI_DIR)` from `MainLoader`.
- `main_window` should be the `MainLoader` instance; `UI_DIR` points to the `ui/` folder.
- The returned `SalesFrame` object is stored (e.g., `self.sales_frame_controller`) so you can connect to its signals.
- The controller still loads `sales_frame.ui`, inserts it into the `salesFrame` placeholder, and keeps `main_window.sales_table` populated for any legacy usages.
- `totalValue` is bound via `bind_total_label`, and we now also register `add_total_listener` so the controller can emit `saleTotalChanged` whenever the total changes.

## Signals & communication
`SalesFrame` publishes the following signals for `MainLoader` to consume:
* `saleTotalChanged(float)` – emitted each time the grand total changes.
* `holdRequested()` – fired when `holdSalesBtn` is clicked.
* `viewHoldLoaded(int receipt_id, float total)` – helper for future view-hold logic; call `notify_hold_loaded` to emit it from elsewhere.
* `cancelRequested()` – emitted when the cancel button is pressed (before the cancel dialog is shown).

`MainLoader` listens to these signals and updates the shared `ReceiptContext` accordingly; logging is currently used to surface the updates before the database layer is wired in.

The total listener mentioned above keeps `saleTotalChanged` in sync with `bind_total_label` so the controller doesn't need to duplicate total math.

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