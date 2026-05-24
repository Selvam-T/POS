# Printer Helper

## Files
- `modules/devices/printer_and_drawer.py`
- `config.py`
- `modules/payment/payment_panel.py`
- `main.py`

## Purpose
`modules/devices/printer_and_drawer.py` centralizes ESC/POS network transport for:
- Receipt printing (`print_receipt(...)`)
- Cash drawer pulse (`open_cash_drawer(...)`)

## Config
- `PRINTER_IP`
- `PRINTER_PORT`
- `ENABLE_PRINTER_PRINT`
- `ENABLE_CASH_DRAWER`
- `CASH_DRAWER_PIN`
- `CASH_DRAWER_TIMEOUT`

## Receipt print sequence
1. Open `Network(host=PRINTER_IP, port=PRINTER_PORT, timeout=...)`
2. Send text with `p.text(...)`
3. Ensure trailing newline if needed
4. Cut paper via `p.cut()`
5. Close connection

## Cash drawer sequence
1. Open `Network(host=PRINTER_IP, port=PRINTER_PORT, timeout=...)`
2. Send pulse via `p.cashdraw(pin)`
3. Close connection

## Blocking modes
- `blocking=True`: waits for final result and returns success/failure.
- `blocking=False`: starts a daemon thread and returns immediately.

## Integration points
- In `modules/payment/payment_panel.py::handle_print_clicked()`:
	- Console receipt text prints only when `ENABLE_PRINTER_PRINT` is `False`.
	- Network print runs when `ENABLE_PRINTER_PRINT` is `True`.
	- Current call uses **blocking** mode for immediate success/failure handling.
	- During the payment DB failure lock, Print uses
	  `modules/payment/recovery_receipt.py` to build a `TEMP-DB-FAIL` snapshot
	  receipt from the current UI state. The same helper then prints it to
	  console or printer according to `ENABLE_PRINTER_PRINT`.

- In `main.py::pay_current_receipt()`:
	- After commit success, cash drawer open is attempted through `modules.devices.printer_and_drawer.open_cash_drawer(...)`
		when `ENABLE_CASH_DRAWER` is on and payment includes cash+tender.

- In the payment DB failure recovery flow:
	- After three failed commit attempts, PAY is locked as `PAY err`.
	- If the cashier clears the sales table and cash was allocated, `main.py`
	  opens the cash drawer before clearing the payment fields.

## See also
- `Documentation/Payment_panel.md`
- `Documentation/cash_drawer.md`
