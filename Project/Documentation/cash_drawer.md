# Cash Drawer Flow

## Purpose
Document how cash drawer opening is triggered, where the logic lives, and how failures are surfaced.

## Related Files
- `main.py`
- `modules/devices/printer_and_drawer.py`
- `config.py`
- `Documentation/Payment_panel.md`

## Trigger Conditions
Cash drawer pulse is attempted only when all conditions below are true:
1. `ENABLE_CASH_DRAWER` is `True` in `config.py`
2. Payment is successfully committed in `MainLoader.pay_current_receipt(...)`
3. Payment includes cash: `cash > 0` (tender/change are not part of drawer gating)

Special recovery exception:
- If payment DB commit fails three times, the PAY button enters the `PAY err`
  recovery lock.
- When the cashier then confirms Clear Cart, `main.py` reads
  `cashPayLineEdit` before clearing the payment panel.
- If the locked recovery sale has cash allocated, the drawer is opened even
  though the DB commit did not succeed. This is only for manual cashier
  recovery; ordinary Clear Cart actions do not open the drawer this way.

## Runtime Flow
1. `PaymentPanel.handle_pay_clicked()` emits `payRequested(payload)`.
2. `MainLoader._on_payment_requested(...)` calls `pay_current_receipt(payload)`.
3. `PaidSaleCommitter.commit_payment(...)` persists payment and returns `receipt_no`.
4. `MainLoader._open_cash_drawer_if_needed(payload)` is called.
5. `modules/devices.printer_and_drawer.open_cash_drawer(...)` sends ESC/POS drawer pulse.

Recovery flow:
1. Payment DB commit fails three times.
2. `payPayOpsBtn` is locked as `PAY err`.
3. Cashier prints the `TEMP-DB-FAIL` receipt if needed.
4. Cashier clears the sales table.
5. If cash was allocated, `MainLoader._open_cash_drawer_if_needed({'cash': amount})`
   opens the drawer before payment fields are cleared.

## Why Logic is Split Across `main.py` and `printer.py`

### Why decision/orchestration is in `main.py`
- `main.py` owns transaction lifecycle (`pay_current_receipt`) and knows when commit succeeded.
- Drawer opening is a post-commit business side effect, not a UI widget concern.
- `main.py` already owns app-level status reporting (`report_to_statusbar`) and flow-level error routing.

### Why transport is in `modules/devices/printer_and_drawer.py`
- Drawer pulse is hardware/protocol behavior (ESC/POS via `python-escpos`).
- Device concerns (IP/port connection, protocol call, close, low-level errors) stay centralized.
- Keeps UI/business layers independent from transport details.

This separation follows: **what/when** in `main.py`, **how** in `printer_and_drawer.py`.

## Functions

### `main.py`
- `_should_open_cash_drawer(payment_split)`
  - Pure condition check (`cash > 0`).
  - No side effects.

- `_open_cash_drawer_if_needed(payment_split)`
  - Applies config gate (`ENABLE_CASH_DRAWER`).
  - Calls `_should_open_cash_drawer(...)`.
  - Calls device helper with config values:
    - `CASH_DRAWER_PIN`
    - `CASH_DRAWER_TIMEOUT`
  - On failure, reports to status bar and logs to `error.log`.

- `modules/devices/printer_and_drawer.py`
- `open_cash_drawer(pin=2, blocking=True, timeout=2.0)`
  - Public helper used by `main.py`.
  - Blocking: executes and returns final success/failure.
  - Non-blocking: starts daemon thread and returns immediately.

- `_open_cash_drawer_escpos(...)`
  - Opens `escpos.printer.Network(host=PRINTER_IP, port=PRINTER_PORT, timeout=...)`.
  - Sends pulse via `p.cashdraw(pin)`.
  - Closes transport in `finally`.

## Config
From `config.py`:
- `ENABLE_CASH_DRAWER = True`
- `CASH_DRAWER_PIN = 2`
- `CASH_DRAWER_TIMEOUT = 2.0`

Drawer toggle is intentionally independent from receipt printing toggle (`ENABLE_PRINTER_PRINT`).

## StatusBar + Logging on Failure

### StatusBar propagation
Failure is shown through `dialog_utils.report_to_statusbar(...)` in `main.py`:
- "Cash drawer failed to open." (helper returned `False`)
- "Cash drawer error." (unexpected exception)

### Error log entries
`modules/ui_utils/error_logger.log_error_message(...)` appends to `log/error.log`.

Typical messages include:
- Main-level:
  - `Cash drawer open failed (helper returned False).`
  - `Cash drawer helper call failed: <exception>`
- Device-level (`printer.py`):
  - `python-escpos import failed (cash drawer): ...`
  - `Cash drawer pulse failed (<ip>:<port>, pin=<pin>): ...`
  - `Failed to start cash-drawer thread: ...`

## Notes
- Current integration uses blocking drawer call (`blocking=True`) so failure is known immediately.
- Commit success is not rolled back when drawer pulse fails; payment remains completed and failure is reported/logged.
- The recovery drawer pulse does not imply a DB receipt exists. The failed DB
  transaction remains rolled back, and any `TEMP-DB-FAIL` receipt is a printed
  snapshot only.
