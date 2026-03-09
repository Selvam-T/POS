# Refund Dialog Documentation

## Overview
The Refund dialog is launched from the payment keypad and records refund outflows into `cash_outflows`.

- UI file: `ui/refund.ui`
- Controller: `modules/payment/refund.py`
- Payment keypad hook: `modules/payment/payment_panel.py` (`keyRefundBtn`)
- Main launcher: `main.py` (`open_refund_dialog`)
- DB writer: `modules/db_operation/cash_outflows_repo.py` via facade (`modules.db_operation.add_outflow`)

## Launch Flow
1. User clicks `keyRefundBtn` in Payment panel.
2. `PaymentPanel._open_refund_dialog()` calls `MainLoader.open_refund_dialog()`.
3. `MainLoader` opens modal using `DialogWrapper.open_dialog_scanner_blocked(...)` with `dialog_key='refund'`.
4. Scanner is blocked at wrapper level, overlay is shown, and focus is restored on close.

## Dialog Behavior
- Focus starts in `refundProductCodeLineEdit`.
- Product can be identified by:
  - `refundProductCodeLineEdit`, or
  - `refundNameSearchLineEdit` (with completer suggestions from `PRODUCT_CACHE`).
- Code and name fields are exclusive (typing one clears/locks dependent state for the other path until lookup succeeds).
- On successful lookup:
  - Price is populated into `refundPriceLineEdit`.
  - Quantity, Note, and OK are unlocked.
- Refund price is editable after lookup so the cashier can enter the original purchase price
  (product prices may have changed since the sale).
- `refundAmountLineEdit` is read-only and auto-calculated as:

`amount = unit_price * quantity`

## Validation Rules
- Product must be selected (code/name + mapped price).
- Quantity is validated using shared input handler:
  - `input_handler.handle_quantity_input(..., unit_type='unit')`
- Price is validated on ENTER using:
  - `input_handler.handle_selling_price(...)`
- Note is validated using shared input handler:
  - `input_handler.handle_note_input(...)`
- Computed refund amount must be `> 0`.

When price validation fails, the price field is highlighted, the status label shows the
error, and focus remains in the price field. On valid price input, the amount is
recomputed and focus moves to `refundNoteLineEdit`.

Errors are shown in `refundStatusLabel` using shared `ui_feedback` helpers.

## Barcode Handling
The dialog sets `dlg.barcode_override_handler`.

- Scanner input is accepted when focused in a `*ProductCodeLineEdit` field.
- Scanned code is injected directly into `refundProductCodeLineEdit`.
- Controller triggers lookup sync immediately after injection.

## DB Write Flow (OK click)
On `btnRefundOk`:
1. Re-validate quantity/note and recompute amount.
2. Ensure table exists: `ensure_cash_outflows_table()`.
3. Insert outflow:
  - `outflows_type='REFUND_OUT'`
  - `amount=<computed amount>`
  - `cashier_id=<best available user id (INTEGER) from parent context; NULL if unavailable; FK -> users(user_id)>`
  - `note=<validated note>`
4. Set post-close success message and accept dialog.

On failures:
- Validation failures remain in dialog with status label message.
- Unexpected exceptions are logged and surfaced via post-close error status intent.

## Startup Table Ensure
`main.py` calls `ensure_cash_outflows_table()` during `MainLoader` initialization.
This guarantees `cash_outflows` exists before any refund insert attempts.

## Related Files
- `modules/payment/refund.py`
- `modules/payment/payment_panel.py`
- `main.py`
- `modules/db_operation/cash_outflows_repo.py`
- `Documentation/db_operation.md`
- `Documentation/db_tables_explained.md`
