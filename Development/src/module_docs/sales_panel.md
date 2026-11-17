
# sales_panel.py Documentation

**Location:** `modules/sales/sales_panel.py`

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

`MainLoader` listens to these signals and updates the shared `ReceiptContext` accordingly; logging is currently used to surface the updates before the database layer is wired in.

The total listener mentioned above keeps `saleTotalChanged` in sync with `bind_total_label` so the controller doesn't need to duplicate total math. Payment Panel totals refresh from this signal without pre-filling payment allocations or moving focus into the payment fields. Barcode scans, Manual Entry, Vegetable Entry, and Qty edits can therefore keep the cashier in the sales workflow while the payment total stays live. When Qty is accepted with Enter, focus leaves the row editor and returns to the Sales table rather than jumping to payment. Moving into payment is treated as an explicit user action, such as clicking a `*PayLineEdit` or payment control.

## Sales Table Focus Indicator

`assets/qss/sales.qss` applies a 4 px orange border to `salesTable` while the
table itself has focus. The normal border returns when focus moves elsewhere.
This gives the cashier an immediate visual indication that barcode scans have
the safe sales-table focus target. It does not change scanner routing, and it
does not highlight a row `qtyInput`; quantity editors retain their own focus
style.

## Sales Table Readiness Gate

The Sales table is considered ready only after `setup_sales_frame(...)`
completes and registers `main_window.sales_table`. `MainLoader` owns the shared
health state and exposes:

- `_require_sales_table_ready()`: returns `True` for a usable table; otherwise
  shows the common transaction-disabled StatusBar message.
- `_mark_sales_table_unavailable(exc, where=...)`: marks the subsystem
  unavailable, records the failure reason, logs the exception once, and shows
  the StatusBar message.

The gate protects Vegetable Entry, Manual Entry, Clear Cart, Hold Sale, View
Hold, PAY, and scan-to-cart routing. Runtime failures while rebuilding the main
Sales table from dialogs, View Hold, or barcode scans also mark the subsystem
unavailable. Repeated button clicks repeat the user-facing StatusBar message
without duplicating the original error-log entry.

## Canonical Unit Handling and Robust Merging (2026 Update)

- All sales table operations (add, update, delete, barcode scan, dialog transfer) use only canonical units: "Kg" or "Each".
- All merging, duplicate detection, and display logic is handled via a canonical data list and table rebuild (`set_table_rows`).
- KG items are always read-only; EACH items are always editable.
- Barcode scanning blocks KG items and prompts the user to use Vegetable Entry.
- All table operations are robust and unified for maintainability.

**Example:**
```python
from modules.sales.sales_panel import setup_sales_frame
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
- `modules/table_ui/table_operations.py`: Provides `setup_sales_table`, row rebuilding, and total-value management.

---
*Last updated: June 22, 2026*
