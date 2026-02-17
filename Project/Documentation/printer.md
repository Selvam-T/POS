# Printer Helper

## Files
- `modules/devices/printer.py`
- `config.py`
- `modules/payment/payment_panel.py`

## Purpose
`print_receipt(receipt_text, blocking, timeout)` sends receipt text to the network printer using `python-escpos` `Network`.

## Config
- `PRINTER_IP`
- `PRINTER_PORT`
- `ENABLE_PRINTER_PRINT`

## Print sequence
1. Open `Network(host=PRINTER_IP, port=PRINTER_PORT, timeout=...)`
2. Send receipt text with `p.text(...)`
3. Ensure trailing newline if needed
4. Cut paper with `p.cut()`
5. Close connection

## Blocking modes
- `blocking=True`: waits for send/cut result and returns success/failure.
- `blocking=False`: starts a daemon thread and returns immediately.

## Payment panel integration
In `handle_print_clicked()`:
- Console output `print(receipt_text)` stays for debug.
- Network print runs only when `ENABLE_PRINTER_PRINT` is `True`.
- Current call uses non-blocking mode.
