# Receipt Menu

`receipt_menu.py` controls the Receipt History dialog loaded from `ui/receipt_menu.ui`.
The dialog is used to search historical receipts, preview receipt text, print selected
receipts, and void unpaid receipts.

## Dialog Loading

- Entry point: `modules.menu.receipt_menu.launch_receipt_dialog(host_window, ...)`
- UI: `ui/receipt_menu.ui`
- Stylesheet: `assets/qss/dialog.qss`
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
- `receiptProductNameLineEdit`
- `receiptPreviewLabel`
- `receiptPrintRadioBtn`
- `receiptVoidRadioBtn`
- `receiptNoteLineEdit`
- `btnReceiptOk`
- `btnReceiptCancel`
- `receiptStatusLabel`

## Receipt Table

`receiptTable` is configured in code, not in the `.ui`.

The controller delegates receipt-table setup, filling, selection, and sorting to
`modules.table_ui.receipt_table_helpers`.

Visible columns depend on `receiptStatusComboBox`:

- `All`: `No.`, `Receipt`, `Status`, `Transact`, `Paid`, `Cancelled`, `Amount`
- `Paid`: `No.`, `Receipt`, `Status`, `Transact`, `Paid`, `Amount`
- `Unpaid`: `No.`, `Receipt`, `Status`, `Transact`, `Amount`
- `Cancelled`: `No.`, `Receipt`, `Status`, `Transact`, `Cancelled`, `Amount`, `Note`

The table layout is refreshed when Search runs and the active status filter
requires a different column set.

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
- `Note` is shown only in the `Cancelled` status layout.
- `Amount` display uses `modules/ui_utils/money_format.format_currency(...)`
  as `$ 1,234.56`.

Sorting behavior:

- `No.` is display-only and not sortable.
- Other visible columns sort when their header is clicked.
- Sorting uses hidden typed sort keys, not only visible text.
- `Amount` sorts numerically using the hidden typed sort key, independent of
  the formatted currency text.
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

Date range behavior:

- `receiptFromDateEdit` and `receiptToDateEdit` are initialized through the shared date-range helpers in `modules.date_time.date_gating`.
- Both date edits are capped at today, so future dates cannot be selected.
- `receiptToDateEdit` cannot be earlier than `receiptFromDateEdit`.
- If From Date is moved after To Date, To Date is clamped forward to match From Date.

When Date Type is `All`, a receipt appears if any of `created_at`, `paid_at`, or `cancelled_at` falls in the selected date range. A receipt is returned once even if more than one date column matches.

Search inputs:

- `receiptNumberLineEdit` filters by receipt number.
- `receiptProductCodeLineEdit` filters by matching `receipt_items.product_code`.
- `receiptProductNameLineEdit` is a lookup helper that fills `receiptProductCodeLineEdit`; product-name text is not sent separately in search params.

Focus and search behavior:

- Pressing Enter in `receiptStatusComboBox` or `receiptDateTypeComboBox` moves focus to `searchReceiptBtn`.
- Pressing Enter in `receiptFromDateEdit` moves focus to `receiptToDateEdit`.
- Pressing Enter in `receiptToDateEdit` moves focus to `searchReceiptBtn`.
- Pressing Enter in `receiptNumberLineEdit` moves focus to `searchReceiptBtn`; it does not validate or search by itself.
- Clicking `searchReceiptBtn` applies the current filters, receipt number, and product code, refreshes `receiptTable`, and then moves focus to `resetReceiptBtn`.

Search does not perform separate input validation for the filter/search widgets. The date edits are clamped while the user selects dates, so future dates and To-before-From ranges are prevented before search. If receipts are found, `receiptStatusLabel` shows the receipt count. If no rows match, it shows `No receipts found.` Runtime/DB failures are shown in `receiptStatusLabel` and logged.

## Product Code And Name Sync

Product lookup uses `modules.db_operation.PRODUCT_CACHE` via `input_handler.get_coordinator_lookup(...)`.

Behavior:

- Typing or scanning a product code can fill `receiptProductNameLineEdit`.
- Selecting or typing an exact product name can fill `receiptProductCodeLineEdit`.
- Editing one product field clears the other until a valid lookup is committed.
- Pressing Enter in an empty product field moves focus to `searchReceiptBtn`.
- Pressing Enter with a valid product code or exact product name cross-fills the paired field and moves focus to `searchReceiptBtn`.
- Pressing Enter with an invalid product code or product name selects the invalid text, keeps focus in that field, applies the red input-error border, and shows the lookup error in `receiptStatusLabel`.
- Product code/name Enter handling does not refresh `receiptTable`; only `searchReceiptBtn` does that.

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

Receipt text intentionally keeps local amount formatting inside
`receipt_generator.py` instead of using the shared UI currency formatter. The
printed receipt is fixed-width, printer-oriented text, so amounts must be
right-aligned within `RECEIPT_AMOUNT_WIDTH` and fitted to the configured receipt
line width.

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
- Details are logged to `logs/error.log`.

## Print And Void Actions

Action radios:

- `receiptPrintRadioBtn` is selected by default.
- `receiptVoidRadioBtn` is available only for selected receipts with status `UNPAID`.

`btnReceiptOk` behavior:

- If Print is selected, generates receipt text and calls `print_receipt_with_fallback(...)`.
- If Void is selected, voids the selected unpaid receipt.

Print behavior:

- Uses the same generated receipt text as preview.
- Keeps receipt-specific amount formatting from `receipt_generator.py` so printed columns stay aligned within the configured receipt width.
- Shows true item subtotal plus a computed rounding adjustment when the stored payable `grand_total` differs from the sum of item line totals.
- Sends text through `modules.devices.print_helper.print_receipt_with_fallback(...)`.
- Honors `config.ENABLE_PRINTER_PRINT`: network printer when enabled, console fallback when disabled.
- Success or failure appears in `receiptStatusLabel`.
- Runtime failures are logged and routed to the post-close StatusBar message pipeline.

Void behavior:

- Only `UNPAID` receipts can be voided.
- `PAID` and `CANCELLED` receipts cannot be voided.
- This protects accounting integrity because VOID is not connected to REFUND.
- Note is optional.
- `receiptNoteLineEdit` is locked unless Void is selected for an unpaid receipt.
- `receiptNoteFieldLbl` is also given the `locked` dynamic property so QSS can gray it.
- Pressing Enter in the note field while Void is selected moves focus to `btnReceiptOk`; the void DB update only runs from `btnReceiptOk`.

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
- Uses the stored payable `receipts.grand_total` where available and falls back to summing `receipt_items.line_total` for compatible schemas.
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

This writes details to `logs/error.log` and schedules a concise post-close StatusBar message when appropriate.

Expected user errors, such as invalid date range, no selected receipt, or trying to void a paid receipt, are shown in `receiptStatusLabel` without being treated as hard failures.
