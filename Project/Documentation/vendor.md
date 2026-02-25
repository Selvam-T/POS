**Vendor Dialog**

- **Purpose:** Capture vendor cash payments (outflows) and record them in the `cash_outflows` table with `movement_type`/`outflow_type` = `VENDOR_OUT`.
- **Location:** UI file: `ui/vendor.ui`. Controller: `modules/payment/vendor.py`. DB helper: `modules/db_operation/cash_outflows_repo.py` (exposed via `modules.db_operation.add_outflow`).

Behavior summary
- Dialog is modal and opened through the main window wrapper to block global scanner input. Use `main.open_vendor_dialog()` or the payment keypad `VENDOR` key which routes to `open_vendor_dialog()`.
- On open: focus is set to `vendorNameLineEdit`.
- Scanner bursts must be swallowed while the dialog is open; the dialog exposes `dlg.barcode_override_handler` to intercept barcode input.

Widgets and validation
- `vendorNameLineEdit` (landing focus)
  - Accepts normal keyboard typing. Scanner bursts are not permitted here.
  - Validation: `input_handler.handle_customer_input()` (canonicalizes & validates). Must be non-empty.
  - On valid entry, focus jumps to `vendorAmountLineEdit`.

- `vendorAmountLineEdit`
  - Accepts normal keyboard typing. Scanner bursts are not permitted here.
  - Validation: `input_handler.handle_currency_input(..., asset_type='Amount')`.
  - Value must be numeric and > 0 (validation logic lives in `modules/ui_utils/input_validation.py`). After validation the widget text is canonicalized to two-decimal format.
  - On valid entry, focus jumps to `vendorNoteLineEdit`.

- `vendorNoteLineEdit`
  - Optional. Accepts normal typing. Validation/canonicalization via `input_handler.handle_note_input()` when present.
  - Empty value is accepted and should not block the OK action.

- `vendorStatusLabel`
  - Displays validation or error messages from the FieldCoordinator and controller.

- Buttons
  - `btnVendorOk`: Validates `vendorNameLineEdit` and `vendorAmountLineEdit`. If valid, records an outflow via `modules.db_operation.add_outflow(outflow_type='VENDOR_OUT', ...)`. On success shows a confirmation and closes the dialog. On validation error shows message on `vendorStatusLabel`. On DB/exception error the dialog reports via `report_exception_post_close()` (or status bar) and rejects/closes per caller policy.
  - `btnVendorCancel` and `customCloseBtn`: call `reject()` and show a small cancellation info message.

Implementation notes
- Follow the same patterns as `modules/payment/refund.py`: use `build_dialog_from_ui()`, `require_widgets()`, `FieldCoordinator` to add links and `register_validator()` so errors auto-clear when corrected.
- Use `input_handler` functions as validate_fn lambdas in `coord.add_link(...)`, not local wrapper functions. Example:
  - `validate_fn=lambda: input_handler.handle_customer_input(name_le)`

DB flow
- Ensure the `cash_outflows` table exists by calling `ensure_cash_outflows_table()` before writing.
- Insert via `add_outflow(outflow_type='VENDOR_OUT', amount=..., cashier_name=..., note=...)`.
- `add_outflow` validates `outflow_type` and `amount` and returns the inserted row id on success; errors are raised as exceptions.

Testing and QA checklist
- Manual flow
  1. Open Payment panel and press the `VENDOR` key or invoke `open_vendor_dialog()` from main.
  2. Type vendor name; press Enter — focus should move to Amount.
  3. Type an invalid amount (e.g., "abc") and press Enter — `vendorStatusLabel` should show an error and focus should remain.
  4. Type a valid amount (e.g., "12.50") and press Enter — focus moves to Note.
  5. Leave Note empty and hit Enter — focus should move to OK and `OK` should be enabled.
  6. Click `OK` — verify a row is inserted into `cash_outflows` with `outflow_type='VENDOR_OUT'` and correct values.

- Simulating DB failure (for error-path testing)
  - In `modules/payment/vendor.py` temporarily raise an exception before the call to `ensure_cash_outflows_table()` to exercise error handling. The dialog should call `report_exception_post_close()` (or similar) and reject/close. Remove the injected error after testing.

Notes for maintainers
- Keep validation logic in `modules/ui_utils/input_handler.py` and `modules/ui_utils/input_validation.py`. Do not reimplement validation in the controller.
- Use `FieldCoordinator` consistently to manage focus, enter-key behavior, and status label messaging.
- Add unit tests that mock `db_operation.add_outflow` to assert correct parameters and that the controller handles DB exceptions gracefully.

Change log
- Created: February 26, 2026 — initial documentation for Vendor dialog and integration notes.
