# Printer Helper

## Files
- `modules/devices/printer.py`
- `config.py`
- `modules/payment/payment_panel.py`
- `main.py`

## Purpose
`modules/devices/printer.py` centralizes ESC/POS network transport for:
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

- In `main.py::pay_current_receipt()`:
	- After commit success, cash drawer open is attempted through `open_cash_drawer(...)`
		when `ENABLE_CASH_DRAWER` is on and payment includes cash+tender.

## See also
- `Documentation/Payment_panel.md`
- `Documentation/cash_drawer.md`
