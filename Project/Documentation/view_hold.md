# View Hold Dialog Documentation

## Overview

The View Hold dialog allows the cashier to browse previously held **UNPAID** receipts and perform one of three actions:

- **LOAD**: load a held receipt back into the Sales table and prepare the Payment panel
- **PRINT**: print the selected receipt via the configured printer (no console fallback)
- **VOID**: cancel the selected receipt (status → `CANCELLED`) with an optional note

The dialog is opened through the standard DialogWrapper pipeline (scanner blocked, modal lifecycle, overlay, post-close StatusBar handling).

When a receipt is loaded, the application enters a protected state (`ReceiptContext.source = 'HOLD_LOADED'`) intended for payment-only workflows:

- Barcode scanner “scan-to-cart” routing is blocked (scans are ignored)
- Sales table quantity widgets are locked (no manual typing in SalesFrame)
- Payment panel remains keyboard-typable for tender/split entry

## Files Involved

- Controller: `modules/sales/view_hold.py`
- UI: `ui/view_hold.ui`
- Dialog style: `assets/dialog.qss`

Launch + wiring:
- Main launch guard + wrapper open: `main.py` (`open_viewhold_panel`)
- Button wiring: `modules/sales/sales_frame_setup.py` (`viewholdBtn`)
- Signal target: `modules/sales/sales_frame_setup.py` (`viewHoldLoaded(int, float)`) and `main.py` (`_on_view_hold_loaded`)

DB layer:
- SQL repo: `modules/db_operation/hold_receipts_repo.py`
- DB facade exports: `modules/db_operation/__init__.py` (exports `list_unpaid_receipts`, `search_unpaid_receipts_by_customer`, `void_receipt`)
- Receipt reads (header/items): `modules/db_operation/receipt_repo.py`

Shared helpers:
- Dialog utilities + error routing: `modules/ui_utils/dialog_utils.py`
- Status label feedback: `modules/ui_utils/ui_feedback.py`
- Note parsing/validation: `modules/ui_utils/input_handler.py`
- Keyboard coordinator (debounced live lookup): `modules/ui_utils/focus_utils.py` (`FieldCoordinator`)
- Error logging: `modules/ui_utils/error_logger.py`

## Launch Rules (Click-Time Guard)

View Hold is intentionally restricted to “no active sale in progress”. The guard is enforced in `main.py` (`open_viewhold_panel`):

- Sales table must be empty (`sales_table.rowCount() == 0`)
- `receipt_context['active_receipt_id']` must be `None`
- Payment total label (`totalValPayLabel`) must be effectively `0.0`

If any rule fails, the dialog is not opened and a short StatusBar hint is shown.

## Dialog Construction Pattern

The controller uses shared dialog utilities:

- `build_dialog_from_ui(...)` to load UI and apply `dialog.qss`
- `require_widgets(...)` to resolve required controls (fail-fast)

Required controls (objectName):

- `viewHoldSearchLineEdit` (search)
- `receiptsTable` (table)
- `viewHoldNoteLineEdit` (note for VOID)
- `viewHoldStatusLabel` (dialog-local feedback)
- `btnViewHoldOk`, `btnViewHoldCancel`
- `viewHoldLoadRadioBtn`, `viewHoldPrintRadioBtn`, `viewHoldVoidRadioBtn`
- `customCloseBtn` (optional)

## Receipts Table Contract

The table is configured as a read-only row selector:

- 5 columns:
  1) Receipt No
  2) Customer Name
  3) Grand Total
  4) Created At
  5) Note
- Select rows, single selection, no in-table edits
- Sorting enabled (sorting is temporarily disabled during refresh fill)

### Receipt ID storage

When available, `receipt_id` is stored in the **Receipt No** cell using `Qt.UserRole`.
This enables a reliable linkage back to the existing DB receipt row.

If `receipt_id` is missing for any reason, the controller attempts to resolve it by calling:

- `receipt_repo.get_receipt_header_by_no(receipt_no)`

## Initial Load Behavior

On open, the dialog loads UNPAID receipts via:

- `list_unpaid_receipts()`

If no UNPAID receipts exist:

- Input widgets/actions are disabled
- The status label shows: “No UNPAID receipts found.”

If receipts exist:

- LOAD action radio is selected
- The first row is selected automatically
- A short success message is shown for 2000ms:
  - `"{customer_name} : {receipt_no} loaded."`

The same short success message is also shown whenever the table selection changes.

## Search (Debounced Live Lookup)

The search field uses `FieldCoordinator` with **live lookup** enabled:

- Debounce: 180ms
- Minimum characters: 0
- Lookup functions:
  - Empty search → `list_unpaid_receipts()`
  - Non-empty search → `search_unpaid_receipts_by_customer(query)`

### No-match behavior

When a non-empty search returns no rows:

- The dialog-local status label shows “No matching receipts.”
- The search text is selected (highlighted) and focus returns to the search box

Enter key behavior on the search field:

- If the search text is empty: focus jumps to `viewHoldLoadRadioBtn`
- If the search text is non-empty and yielded no matches: pressing Enter clears the search text and reloads UNPAID receipts, selecting the top row

## Action Modes

The OK button dispatches based on the selected radio action.
The OK button is disabled until a receipt row is selected.

### 1) LOAD

Goal: Load held receipt items into the Sales table and set Payment defaults.

Flow:

1. Read selected `receipt_no` (and `receipt_id` if present)
2. Ensure `receipt_id` is resolvable (required for correct payment/commit context)
3. Load items:
   - `receipt_repo.list_receipt_items_by_no(receipt_no, receipt_id=receipt_id)`
4. Convert items into canonical sales rows:
   - Uses `modules.table.table_operations.set_table_rows(...)`
   - Canonicalizes unit via `modules.table.unit_helpers.canonicalize_unit(...)`
5. Apply payment defaults:
   - `payment_panel_controller.set_payment_default(total)`
6. Emit held-load signal (to update ReceiptContext):
   - `sales_frame_controller.notify_hold_loaded(receipt_id, total)`
  - Main window handler (`_on_view_hold_loaded`) sets `ReceiptContext.source = 'HOLD_LOADED'` and applies a SalesFrame qty lock
7. Close the dialog (`accept()`)

### 2) PRINT

Goal: Printer-only printing of a receipt.

- Generates receipt text:
  - `modules.payment.receipt_generator.generate_receipt_text(receipt_no)`
- Prints via device printer:
  - `modules.devices.printer.print_receipt(receipt_text, blocking=True)`

On success:

- StatusBar shows “Printed receipt <receipt_no>”
- Status label shows “Printed.” (2000ms)

On failure:

- StatusBar shows a short error
- Failure is logged to `log/error.log`
- No console fallback printing is used

### 3) VOID

Goal: Cancel a held receipt.

- Only available when a row is selected
- Note field is enabled **only in VOID mode**
- The note may be empty:
  - Empty note clears the existing note (NULL if allowed, else empty string)

DB call:

- `void_receipt(receipt_id=..., receipt_no=..., note=note_or_none)`

On success:

- StatusBar shows “Receipt <receipt_no> voided.”
- Status label shows “Voided.” (2000ms)
- Table refreshes using the current search text (so the user stays in-context)

## Error Handling Policy

- Expected operational errors are handled inside the controller:
  - Dialog-local feedback uses `viewHoldStatusLabel`
  - StatusBar feedback uses dialog utils (`report_to_statusbar`) or post-close intent (`set_dialog_main_status_max`)
- Exceptions are logged via shared logging helpers (and shown with a user-safe message)

## DB Repo Notes (Schema Flexibility)

The SQL repo `modules/db_operation/hold_receipts_repo.py` is schema-tolerant:

- Detects column names using `table_columns(...)` and `first_existing(...)`
- Supports common variants:
  - `receipt_id` vs `id`
  - `receipt_no` vs `receipt_number`
  - `note` vs `notes`
  - `grand_total` vs `total`
- `void_receipt(...)` respects NOT NULL constraints on the note column (writes empty string instead of NULL when required)

---

*Last updated: February 21, 2026*
