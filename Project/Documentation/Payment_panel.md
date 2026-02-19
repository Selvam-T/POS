# Payment Frame Controller

## Overview
`PaymentPanel` allocates payment splits, validates currency input, enforces tender/balance rules, and only enables Pay when the state is consistent. It emits payment events to the main window but does not write to the DB.

## Files
- Controller: `modules/payment/payment_panel.py`
- UI: `ui/payment_frame.ui`
- Styles: `assets/main.qss`, `assets/dialog.qss`

## Signals
**Outgoing**
- `payRequested(payload: dict)` — emitted when Pay is clicked and the state is valid.
	Payload includes payment splits plus `tender` and `change` (for CASH flows).
- `paymentSuccess()` — emitted by `notify_payment_success()` after payment processing is confirmed.

**Incoming (wired in MainLoader)**
- `saleTotalChanged(total: float)` → `set_payment_default(total)`

## Data Rules
- Voucher is integer-only.
- NETS / PayNow / Cash accept 2-decimal floats.

**Allocation formula:**
```
unalloc = total - (nets + paynow + voucher + cash)
```
**Tender/change:**
```
change = tender - cash
```

## UI Behavior (current)
- **Validation**: All payment fields (cash, nets, paynow, tender, voucher) are validated via `modules/ui_utils.input_handler` when the user presses Enter or leaves the field. Validation failures hold focus on the offending widget, surface an error through `payStatusLabel`, and block navigation/Pay until corrected. Editing or re-focusing the field clears the error via `ui_feedback` so the message goes away as soon as the value changes.
- **Unallocated tracking**: Recomputed on any payment change. Highlights the unalloc frame when `unalloc > 0`; clears highlight when `unalloc <= 0`. When `unalloc < 0`, the frame stays neutral but the status label shows `Warning: Payment Over-allocation.` so the user knows a warning state exists even though Pay remains reachable.
- **Status priority**: validation error > (cash>0 and tender<cash) > (unalloc>0) > (unalloc<0) > clear.
- **Tender/Balance**: Tender UI is shown/enabled only when `cash > 0`. `balance = tender - cash` (may go negative while typing); tender placeholder shows only when `cash > 0` and tender is empty.
- **Placeholders**: Pay-method placeholders show only when `unalloc > 0` and the field is empty. Tender placeholder is conditional on cash being present.
- **Read-only / focus gating**: When `unalloc == 0`, zero-valued pay fields become read-only and lose focusability; fields with values stay editable. Tender is locked/no-focus when `cash <= 0`.
- **Pay-select buttons**: Choosing a method fills that method with the full total (voucher uses int), clears the other methods, recalculates, and moves focus (cash→tender, others→Pay). A second click just focuses/selects.
- **Enter navigation**: Context-aware routing—cash with `unalloc <= 0` jumps to tender; pay fields with `unalloc <= 0` jump to Pay; tender enforces `tender >= cash` before advancing and will jump back/select-all if short; if tender>cash while `unalloc > 0`, focus jumps to the next pay field.
- **Pay button gating**: Requires `total > 0`, `unalloc <= 0`, no validation errors, receipt status in (`NONE`, `UNPAID`), and when `cash > 0`, `tender >= cash`. Reset is enabled only when total>0; Print only when total is zero/empty.

## Pay-Select Behavior
- Sets the chosen method to total (voucher rounded to int), clears others to zero/blank, recomputes unalloc, then focuses tender (if cash) or Pay (otherwise).

## Controller API
- `set_payment_default(total)` — prime fields for a new sale total and focus tender if visible.
- `clear_payment_frame()` — zero all fields, hide tender, clear status/highlights.
- `reset_payment_grid_to_default()` — reapply defaults using the current total.
- `recalc_unalloc_and_ui()` — recompute unalloc, update placeholders, status, and enablement.
- `recalc_cash_balance_and_ui()` — manage tender visibility, balance, placeholders, and status for cash flows.
- `update_readonly_policy()` — lock/unlock pay/tender focus based on unalloc and cash presence.
- `update_pay_button_state()` — enforce Pay/Reset/Print gating rules.
- `handle_pay_select(method)` — pay-select workflow described above.
- `handle_pay_clicked()` — final validation and emit `payRequested` payload.
- `focus_jump_next_pay_field()` — cycle focus to the next editable pay field.

## Integration Notes
- `MainLoader._on_payment_requested()` calls `pay_current_receipt(payment_split)` and forwards `tender` with the split.
- `PaidSaleCommitter` persists `tendered` for CASH in `receipt_payments` (non-cash sets `tendered = amount`).
- On success, `paymentSuccess` is emitted, the receipt context resets, sales table clears, and the payment frame resets.

## Cash Drawer (Network)
- Drawer opening is **independent** of receipt-printing toggle.
- Trigger point is in `main.py` after payment commit success (`pay_current_receipt`).
- Drawer is requested only when payment includes cash (`cash > 0`) and `tender > 0`.
- Drawer pulse uses `modules/devices/printer.py::open_cash_drawer(...)` (`python-escpos` Network transport).
- Failure path logs error and reports to main StatusBar via `dialog_utils.report_to_statusbar()`.

### Cash Drawer Config
- `ENABLE_CASH_DRAWER` — master toggle for drawer pulses.
- `CASH_DRAWER_PIN` — ESC/POS drawer pin (Epson commonly `2`).
- `CASH_DRAWER_TIMEOUT` — network timeout for drawer call.

## Receipt Printing (Network)
- `handle_print_clicked()` in `modules/payment/payment_panel.py` always generates and prints receipt text to console (`print(receipt_text)`) for debug visibility.
- Optional physical printing is gated by `ENABLE_PRINTER_PRINT` in `config.py`.
- When enabled, the panel calls `modules/devices/printer.py::print_receipt(receipt_text, blocking=True)`.
- With `blocking=True`, the return value is checked; on printer send failure, an error is logged and shown in the main status bar.
- Network destination is sourced from `config.py`: `PRINTER_IP` and `PRINTER_PORT` (TM-T82x on TCP 9100).
- The helper uses `python-escpos` `Network` transport and issues `text(...)` + `cut()`.

### Why this design
- Safety-first rollout: printer I/O can stay disabled (`ENABLE_PRINTER_PRINT = False`) while UI flow and receipt formatting continue to be verified via console output.
- Separation of concerns: `PaymentPanel` remains a UI/controller; printer transport details are isolated in `modules/devices/printer.py`.
- Toggle-friendly deployment: moving between development (no printer connected) and production (printer connected) only requires changing one config flag.

### Blocking vs Non-blocking
- Current print call is **blocking** (`blocking=True`) so the panel can show immediate success/failure in the status bar.
- In blocking mode, the call waits for network send completion and returns final success/failure immediately; slow/unreachable printers may pause UI briefly.
- In non-blocking mode (`blocking=False`), the function returns after starting a thread; final send outcome is asynchronous.

## Why shared focus helpers are not used here
- `FieldCoordinator` / `FocusGate` provide generic Enter→next/validate/status and static gating used by other dialogs (e.g., vegetable_menu). Payment flow depends on live allocation math (unalloc, tender vs cash), per-method auto-fill/zeroing, and conditional tender visibility. These dynamic rules require bespoke branching on every change, so adopting the shared coordinator would still leave most custom logic duplicated. Currency validation remains shared via `input_handler` (and `input_validation`/`ui_feedback`).

## See also

- `Documentation/payment_processing.md` — detailed commit flow and distinction between new-sale and held-receipt paths; the DB commit is executed by `main.py`.
- `Documentation/printer.md` — printer helper transport details, cut behavior, and config keys.
- `Documentation/cash_drawer.md` — drawer trigger conditions, config, error propagation/logging, and `main.py` vs `printer.py` responsibilities.
