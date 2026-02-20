# Hold Sales Dialog Documentation

## Overview

The Hold Sales dialog allows the cashier to suspend the current active sale and store it in the database as an UNPAID receipt without creating any payment rows.

This dialog is launched from the Sales Frame Hold button and is executed through the DialogWrapper pipeline (modal lifecycle, scanner block, overlay, geometry, focus restore, and post-close StatusBar handling).

## Files Involved

- Controller: modules/sales/hold_sales.py
- Main launch guard: main.py
- Sales button wiring: modules/sales/sales_frame_setup.py
- UI file: ui/hold_sales.ui
- Dialog style: assets/dialog.qss
- Shared helpers:
  - modules/ui_utils/dialog_utils.py
  - modules/ui_utils/input_handler.py
  - modules/ui_utils/input_validation.py
  - modules/ui_utils/ui_feedback.py
  - modules/ui_utils/error_logger.py
- DB helpers:
  - modules/db_operation/db.py
  - modules/db_operation/receipt_numbers.py
  - modules/db_operation/held_sale_committer.py

## Launch Rules (Click-Time Guard)

The Hold dialog opens only when all conditions are true:

1. ReceiptContext.source == ACTIVE_SALE
2. ReceiptContext.active_receipt_id is None
3. ReceiptContext.status is NA, NONE, or None
4. Sales table row count > 0

If any rule fails, the dialog is not opened and the Main StatusBar shows a short hint.

Note: Guarding is done at click time (no proactive background enable/disable refresh loop).

## Dialog Construction Pattern

The controller uses shared dialog utilities:

- build_dialog_from_ui(...) to construct the modal frameless dialog with QSS
- require_widgets(...) to resolve required controls with fail-fast behavior

Required controls:

- holdSalesCustomerLineEdit (mandatory)
- holdSalesNoteLineEdit (optional)
- holdSalesStatusLabel
- btnHoldSalesOk
- btnHoldSalesCancel
- customCloseBtn (optional lookup)

## Focus & Enter Navigation

Initial focus:

- holdSalesCustomerLineEdit receives focus when opened.

Enter-key flow (FieldCoordinator + FocusGate):

1. Customer field Enter
  - Validates with input_handler.handle_customer_input(...)
  - On success: unlocks Note field and jumps focus to it
  - On failure: focus stays on Customer and selects all

2. Note field Enter
  - Validates with input_handler.handle_note_input(...)
  - On success: focus jumps to OK button
  - On failure: focus stays on Note and selects all

## Placeholder Behavior

The controller applies a simple placeholder reset:

- UI-authored placeholder text is preserved and re-applied on dialog open.

## Validation Pipeline

Validation follows shared input pipeline:

- Customer: input_handler.handle_customer_input(...) -> input_validation.validate_customer(...)
- Note: input_handler.handle_note_input(...) -> input_validation.validate_note(...)

Inline error feedback:

- Validation failures are shown in holdSalesStatusLabel via ui_feedback.set_status_label(..., ok=False).
- The current invalid field remains focused and highlighted via selectAll().

## Database Behavior (On OK)

The hold commit is transactional and atomic:

1. Build sales snapshot from main window sales table
2. Open DB connection
3. Start transaction
4. Generate next receipt number (YYYYMMDD-####)
5. Insert receipt header with status UNPAID
6. Insert receipt_items snapshot rows
7. Do not insert into receipt_payments
8. Commit transaction

If any step fails, transaction is rolled back.

### Receipts Header Rules

- status = UNPAID
- customer_name = validated customer input
- note/notes column:
  - non-empty note -> saved as text
  - empty note -> saved as NULL if column allows NULL
  - empty note -> saved as empty string if schema marks note column NOT NULL
- paid_at remains NULL
- cashier_name is populated (required for schemas with NOT NULL constraint)

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

- Logged to log/error.log using report_exception_post_close(...)
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
It is explicitly labeled as `HOLD-FAILED` to indicate a non-persisted fallback.
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
