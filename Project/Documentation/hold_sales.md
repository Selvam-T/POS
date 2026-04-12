# Hold Sales Dialog Documentation

## Overview

The Hold Sales dialog allows the cashier to suspend the current active sale and store it in the database as an UNPAID receipt without creating any payment rows.

This dialog is launched from the Sales Frame Hold button and is executed through the DialogWrapper pipeline (modal lifecycle, scanner block, overlay, geometry, focus restore, and post-close StatusBar handling).

## Files Involved

# Hold Sales Dialog Documentation

## Overview

The Hold Sales dialog allows the cashier to suspend the current active sale and store it in the database as an UNPAID receipt (no payment rows).

This dialog is launched from the Sales Frame Hold button and uses the shared DialogWrapper/modal pipeline.

## Files Involved

- Controller: modules/sales/hold_sales.py
- UI file: ui/hold_sales.ui
- Dialog style: assets/dialog.qss
- DB writer: modules/db_operation/held_sale_committer.py
- Shared helpers: modules/ui_utils/* (dialog_utils, input_handler, input_validation, ui_feedback, error_logger)

## Launch Rules (Click-Time Guard)

The dialog is opened only when the normal hold preconditions are met (active sale with at least one row, no active receipt id, etc.). These guards are evaluated at click time by the calling code.

## Dialog Construction Pattern

The controller uses `build_dialog_from_ui(...)` and `require_widgets(...)` to construct the modal and resolve required widgets.

Required controls (current):

- `holdSalesCustomerLineEdit` (mandatory)
- `holdSalesStatusLabel`
- `btnHoldSalesOk`
- `btnHoldSalesCancel`
- Optional `customCloseBtn`

Note: The note field has been removed from the UI/controller. The dialog no longer presents or validates a `Note` input.

## Focus & Enter Navigation

Initial focus:

- The dialog now initially focuses `btnHoldSalesOk` so the cashier can quickly accept the default customer value shown in the UI.

Enter-key / flow rules:

1. Customer field Enter
  - Validates using `input_handler.handle_customer_input(...)` -> `input_validation.validate_customer(...)`.
  - On success: focus moves to `btnHoldSalesOk`.
  - On failure: the status label shows the error, focus remains on the customer field and the text is selected.

2. There is no Note field step.

Behavioral detail: if the customer field is empty and the user presses Enter, validation will fail and focus will remain on the customer field (no gating object is required to enforce this — validation keeps focus sticky as before).

## Placeholder / UI Defaults

The controller no longer wipes or modifies placeholder/texts at dialog open. Default text authored in the `.ui` (`Ongoing-shopping` default in `holdSalesCustomerLineEdit`) remains intact and visible when the dialog opens.

## Validation Pipeline

Validation continues to use the shared input pipeline:

- Customer: `input_handler.handle_customer_input()` -> `input_validation.validate_customer()`

Inline errors are displayed in `holdSalesStatusLabel` using `ui_feedback.set_status_label(..., ok=False)`.

## Database Behavior (On OK)

On OK the controller validates the customer and then commits a held receipt. The commit is transactional and inserts a receipts header (status=UNPAID) and the receipt_items snapshot.

Key change: the hold controller no longer supplies a `note` value to the committer, and the committer has been changed to not write the `note/notes` column for held receipts. With your current database schema the `receipts.note` column is nullable, so held receipts will store `NULL` in the note column.

Implication and caution:
- Current schema: `receipts.note` is nullable. No further action required.
- If the schema is later changed to require `note` (NOT NULL), the hold insert will fail unless a default or fallback is provided. Keep that in mind for future migrations.

## Post-Commit UI Actions

On successful commit:

1. Main sales table is cleared
2. Payment frame is cleared
3. Dialog is accepted
4. StatusBar is updated with a success message

## Cancel / Close Behavior

- Cancel and the titlebar close button reject the dialog and perform no DB changes.

## Error Handling Policy

Runtime exceptions are logged and reported via `log_exception_traceback_and_postclose_statusBar(...)`, and a snapshot receipt (HOLD-FAILED) is printed if configured when a DB commit fails.

## Notes for Maintainers

- This controller is the only code path that creates UNPAID receipts in your codebase. Because the note column is intentionally left untouched here, review DB migrations or schema changes to ensure `receipts.note` remains nullable or provide a compatible fallback.
- The controller change intentionally removed placeholder reset and focus-gating to simplify the dialog flow and preserve UI defaults authored in the `.ui` file.
### Receipts Header Rules

- status = UNPAID
- customer_name = validated customer input
- note/notes column:
  - non-empty note -> saved as text
  - empty note -> saved as NULL if column allows NULL
  - empty note -> saved as empty string if schema marks note column NOT NULL
- paid_at remains NULL
- `cashier_id` (INTEGER `user_id`) is populated (required for schemas with NOT NULL constraint; FK -> `users(user_id)`)

## Post-Commit UI Actions

On successful commit:

1. Main sales table is cleared
2. Payment frame is cleared
3. Dialog is accepted
4. Post-close StatusBar message intent is set (Sale held successfully)

Context reset is not forcibly changed by this controller.

## Cancel / Close Behavior

- Cancel button and titlebar close button reject the dialog.
- No DB write occurs.
- Sales table remains unchanged.

## Error Handling Policy

Handled runtime exceptions inside controller:

- Logged to log/error.log using log_exception_traceback_and_postclose_statusBar(...)
- Generic post-close StatusBar error intent is set
- Inline label can show a short failure message during dialog lifetime

### Snapshot Receipt on DB Failure

If the hold commit fails to write to the database, the controller prints a
snapshot receipt from the current cart:

- Printed to console when `ENABLE_PRINTER_PRINT = False`
- Sent to the printer when `ENABLE_PRINTER_PRINT = True`
- On successful print, the sales table and payment panel are cleared
- Dialog closes after handling the failure

**Receipt number:** The snapshot receipt does not generate a DB receipt number.
It is explicitly labeled as `Not generated - HOLD-FAILED",` to indicate a non-persisted fallback.
This avoids reserving a receipt number when the DB write failed.

**Limitation:** The snapshot receipt has no DB receipt number, so only a single
copy is produced. Once printed and the UI is cleared, the data is no longer in
the system; a duplicate cannot be reprinted. Cashiers must keep this copy to
collect payment from the customer.

Unexpected controller escapes are still protected by DialogWrapper hard-fail boundary.

## Related Implementation Notes

- holdRequested signal wiring was removed from SalesFrame/Main because Hold launch is directly handled by button click callback.
- Hold gating remains centralized at click-time in main.py launch_hold_sales_dialog.
- Scanner blocking during modal execution is handled by DialogWrapper.open_dialog_scanner_blocked(...), not by hold_sales.py directly.
