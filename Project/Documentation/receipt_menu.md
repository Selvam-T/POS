# Receipt Menu

`receipt_menu.py` controls the Receipt History dialog loaded from `ui/receipt_menu.ui`.
The dialog is used to search historical receipts, preview receipt text, print selected
receipts, and void unpaid receipts.

## Dialog Loading

- Entry point: `modules.menu.receipt_menu.launch_receipt_dialog(host_window, ...)`
- UI: `ui/receipt_menu.ui`
- Stylesheet: `assets/dialog.qss`
- Loading uses `build_dialog_from_ui(...)`.
- If the UI cannot load, the controller returns the shared `build_error_fallback_dialog(...)`.
- Required widgets are resolved with `require_widgets(..., hard_fail=True)`.
- The dialog is intended to be opened through `DialogWrapper.open_dialog_scanner_blocked(...)`, so overlay, scanner block, geometry, cleanup, and post-close StatusBar messages follow the shared modal pipeline.
- Initial focus is scheduled to `receiptStatusComboBox`.

## Main Widgets

Important object names:

- `receiptTable`
- `receiptStatusComboBox`
- `receiptDateTypeComboBox`
- `receiptFromDateEdit`
- `receiptToDateEdit`
- `receiptNumberLineEdit`
- `receiptProductCodeLineEdit`
- `receiptProductNameComboBox`
- `receiptPreviewLabel`
- `receiptPrintRadioBtn`
- `receiptVoidRadioBtn`
- `receiptNoteLineEdit`
- `btnReceiptOk`
- `btnReceiptCancel`
- `receiptStatusLabel`

`receiptPreviewLabel` is a read-only `QPlainTextEdit`, not a `QLabel`. It is used because long generated receipts need vertical scrolling.

## Receipt Table

`receiptTable` is configured in the controller, not in the `.ui`.

Columns:

1. `No.`
2. `Receipt`
3. `Status`
4. `Transact`
5. `Paid`
6. `Cancelled`
7. `Amount`

The controller uses shared table helpers from `modules.table.table_widget_helpers`:

- `apply_table_columns(...)`
- `configure_readonly_row_selection_table(...)`

Table behavior:

- Read-only.
- Single-row selection.
- Vertical header hidden.
- Alternating row colors enabled.
- Header labels include sort indicators.
- Header and cell tooltips are populated.
- Compact table date format is `dd/MM/yy HH:mm`, for example `06/06/26 15:45`.
- Date tooltips use the fuller `format_datetime(...)` value, for example `06 Jun 2026  03:45 pm`.
- Empty date cells display an em dash.

Sorting behavior:

- `No.` is display-only and not sortable.
- Other columns sort when their header is clicked.
- Sorting uses hidden typed sort keys, not only visible text.
- `Amount` sorts numerically.
- After sorting, `No.` is renumbered from top to bottom.
- The previously selected receipt is preserved by receipt number where possible.

## Search Filters

Status choices:

- `All`
- `Paid`
- `Unpaid`
- `Cancelled`

Status maps to `receipts.status` values:

- `PAID`
- `UNPAID`
- `CANCELLED`

Date type choices:

- `All`
- `Transaction date`
- `Payment date`
- `Cancellation date`

Date type maps to receipt columns:

- `Transaction date` -> `receipts.created_at`
- `Payment date` -> `receipts.paid_at`
- `Cancellation date` -> `receipts.cancelled_at`
- `All` -> checks all three date columns

Default state:

- Status: `All`
- Date type: `All`
- From date: today
- To date: today

When Date Type is `All`, a receipt appears if any of `created_at`, `paid_at`, or `cancelled_at` falls in the selected date range. A receipt is returned once even if more than one date column matches.

Search inputs:

- `receiptNumberLineEdit` filters by receipt number.
- `receiptProductCodeLineEdit` filters by matching `receipt_items.product_code`.
- `receiptProductNameComboBox` filters by matching `receipt_items.product_name` / `name`.

The controller validates that From Date is not after To Date. Validation messages appear in `receiptStatusLabel`.

## Product Code And Name Sync

Product lookup uses `modules.db_operation.PRODUCT_CACHE` via `input_handler.get_coordinator_lookup(...)`.

Behavior:

- Typing or scanning a product code can fill `receiptProductNameComboBox`.
- Selecting or typing an exact product name can fill `receiptProductCodeLineEdit`.
- Editing one product field clears the other until a valid lookup is committed.
- Pressing Enter in product code or product name syncs fields and runs the search.

Barcode behavior:

- The dialog exposes `dlg.barcode_override_handler`.
- Scans are accepted only when focus is in `receiptProductCodeLineEdit`.
- Scans in other widgets are rejected by `BarcodeManager` with the existing “Scan only in Product Code field” behavior.

Known caveat:

- The current scanner timing heuristic can treat very fast manual typing as scanner input in non-product-code fields. This is documented in `Documentation/scanner_input_infocus.md` and should be fixed separately with deliberate scanner-focused testing.

## Preview

Selecting a row renders the receipt into `receiptPreviewLabel`.

Preview text is generated with:

```python
generate_receipt_text(receipt_no)
```

from `modules.payment.receipt_generator`.

Preview properties:

- Read-only.
- Plain text.
- Monospace font.
- No wrap.
- Horizontal document alignment is set in the controller.
- Vertical centering is not supported by `QPlainTextEdit` document alignment; scrollable text naturally starts from the top.

If preview generation fails:

- `receiptPreviewLabel` shows `Receipt preview unavailable.`
- `receiptStatusLabel` shows the failure message.
- Details are logged to `log/error.log`.

## Print And Void Actions

Action radios:

- `receiptPrintRadioBtn` is selected by default.
- `receiptVoidRadioBtn` is available only for selected receipts with status `UNPAID`.

`btnReceiptOk` behavior:

- If Print is selected, generates receipt text and calls `print_receipt(...)`.
- If Void is selected, voids the selected unpaid receipt.

Print behavior:

- Uses the same generated receipt text as preview.
- Sends text through `modules.devices.printer_and_drawer.print_receipt(...)`.
- Success or failure appears in `receiptStatusLabel`.
- Runtime failures are logged and routed to the post-close StatusBar message pipeline.

Void behavior:

- Only `UNPAID` receipts can be voided.
- `PAID` and `CANCELLED` receipts cannot be voided.
- This protects accounting integrity because VOID is not connected to REFUND.
- Note is optional.
- `receiptNoteLineEdit` is locked unless Void is selected for an unpaid receipt.
- `receiptNoteFieldLbl` is also given the `locked` dynamic property so QSS can gray it.
- Pressing Enter in the note field while Void is selected also performs the void action.

Successful void:

- Calls `dbop.void_unpaid_receipt(...)`.
- Updates receipt status to `CANCELLED`.
- Updates `cancelled_at`.
- Saves optional note when supported by the schema.
- Refreshes the table using the current filters.
- Re-selects the first visible row if any remain.
- Shows success in `receiptStatusLabel`.

## Database Support

Receipt History uses functions exported through `modules.db_operation`:

- `search_receipts(...)`
- `void_unpaid_receipt(...)`

Implementation lives in `modules/db_operation/receipt_repo.py`.

`search_receipts(...)`:

- Reads from `receipts`.
- Aggregates receipt amount from `receipt_items.line_total` where available.
- Falls back to quantity times price when needed.
- Supports schema variants such as `receipt_no` / `receipt_number` and `id` / `receipt_id`.
- Supports status, date, receipt number, product code, and product name filters.

`void_unpaid_receipt(...)`:

- Requires either `receipt_id` or `receipt_no`.
- Updates only rows whose current status is `UNPAID`.
- Runs inside the shared `transaction(...)` context.
- If status, cancelled date, or note update fails, the transaction rolls back.
- The repo raises/returns results; the controller owns logging and UI feedback.

## Error Handling

In-dialog user-facing messages go to `receiptStatusLabel`.

Unexpected DB/runtime failures use:

- `log_exception_traceback_and_postclose_statusBar(...)`
- `log_error_message(...)`

This writes details to `log/error.log` and schedules a concise post-close StatusBar message when appropriate.

Expected user errors, such as invalid date range, no selected receipt, or trying to void a paid receipt, are shown in `receiptStatusLabel` without being treated as hard failures.
