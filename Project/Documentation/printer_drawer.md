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
2. If structured receipt sections are supplied, apply the section style with
   `p.set(...)` and send each section with `p.text(...)`
3. If no sections are supplied, send the plain receipt text with `p.text(...)`
4. Ensure trailing newline if needed
5. Cut paper via `p.cut()`
6. Close connection

## ESC/POS receipt styling

Network receipt font/scale is controlled in:

```python
modules/devices/printer_and_drawer.py::_set_receipt_style(...)
```

Current section styles:

```python
company -> printer.set(align="left", font="a", width=1, height=2)
table   -> printer.set(align="left", font="b", width=1, height=1)
greeting-> printer.set(align="left", font="b", width=1, height=1)
normal  -> printer.set(align="left", font="a", width=1, height=1)
summary -> printer.set(align="left", font="a", width=1, height=1)
```

Change these `printer.set(...)` calls when revising ESC/POS font or scale.
Typical ESC/POS choices are:

- `font="a"`: normal font.
- `font="b"`: smaller/narrower font, if supported by the printer.
- `width=2`: double-width characters; fewer characters fit on a line.
- `height=2`: double-height characters; line width is unchanged.

Receipt sections are produced by `modules/payment/receipt_generator.py`:

- `generate_receipt_sections(receipt_no)` for saved receipts.
- `generate_receipt_sections_from_snapshot(...)` for temporary recovery receipts.

Console fallback still prints plain text only. ESC/POS font/scale changes affect
only network printer output.

## Receipt layout

Fixed-width receipt text is generated in `modules/payment/receipt_generator.py`.
Item table width is configured in `config.py`:

- `RECEIPT_DEFAULT_WIDTH`
- `RECEIPT_QTY_WIDTH`
- `RECEIPT_ITEM_AMOUNT_WIDTH`
- `RECEIPT_AMOUNT_WIDTH`
- `RECEIPT_GAP`

Item `Price` and `Total` columns omit `$` and use fixed two-decimal formatting.
Summary and payment lines keep `$` and use `RECEIPT_AMOUNT_WIDTH`.

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
	- Normal completed receipt reprint uses `generate_receipt_text(...)` plus
	  `generate_receipt_sections(...)`.
	- Current call uses **blocking** mode for immediate success/failure handling.
	- During the payment DB failure lock, Print uses
	  `modules/payment/recovery_receipt.py` to build a `TEMP-DB-FAIL` snapshot
	  receipt from the current UI state. It uses
	  `generate_receipt_text_from_snapshot(...)` plus
	  `generate_receipt_sections_from_snapshot(...)`. The same helper then
	  prints it to console or printer according to `ENABLE_PRINTER_PRINT`.

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
