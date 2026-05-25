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
- **Validation**: All payment fields (cash, nets, paynow, tender, voucher) are validated via `modules/ui_utils.input_handler` when the user presses Enter (handled by `PaymentPanel._handle_enter_key()`) or leaves the field. Validation failures hold focus on the offending widget, surface an error through `payStatusLabel`, and block navigation/Pay until corrected. Editing or re-focusing the field clears the error via `ui_feedback` so the message goes away as soon as the value changes.
- **Unallocated tracking**: Recomputed on any payment change. Highlights the unalloc frame when `unalloc > 0`; clears highlight when `unalloc <= 0`. When `unalloc < 0`, the frame stays neutral but the status label shows `Warning: Payment Over-allocation.` so the user knows a warning state exists even though Pay remains reachable.
- **Status priority**: validation error > (cash>0 and tender<cash) > (unalloc>0) > (unalloc<0) > clear.
- **Tender/Balance**: Tender UI is shown/enabled only when `cash > 0`. `balance = tender - cash` (may go negative while typing); tender placeholder shows only when `cash > 0` and tender is empty.
- **Placeholders**: Pay-method placeholders show only when `unalloc > 0` and the field is empty. Tender placeholder is conditional on cash being present.
- **Read-only / focus gating**: When `unalloc == 0`, zero-valued pay fields become read-only and lose focusability; fields with values stay editable. Tender is locked/no-focus when `cash <= 0`.
- **Pay-select buttons**: Choosing a method fills that method with the full total (voucher uses int), clears the other methods, recalculates, and moves focus (cash→tender, others→Pay). A second click just focuses/selects.
- **Enter navigation**: Context-aware routing—cash with `unalloc <= 0` jumps to tender; pay fields with `unalloc <= 0` jump to Pay; tender enforces `tender >= cash` before advancing and will jump back/select-all if short; if tender>cash while `unalloc > 0`, focus jumps to the next pay field.
- **Pay button gating**: Requires `total > 0`, `unalloc <= 0`, no validation errors, receipt status in (`NONE`, `UNPAID`), and when `cash > 0`, `tender >= cash`. Reset is enabled only when total>0; Print normally only when total is zero/empty.
- **Payment DB failure lock**: After three failed DB commit attempts, `main.py` locks `payPayOpsBtn`, changes its text to `PAY err`, applies the red locked style, and keeps the recovery StatusBar message visible until the sales table is cleared. The lock is reversible and is cleared when the sales table is cleared through the recovery flow.
- **Print during failure lock**: While the DB failure lock is active, `printPayOpsBtn` is enabled even though the cart total is still present. It routes to `modules/payment/recovery_receipt.py` to print a `TEMP-DB-FAIL` snapshot receipt from the current sales table and payment split. This printout is not a DB receipt and does not write any rows.

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
- `set_pay_error_locked(locked)` - temporarily set or clear the `PAY err` state after repeated DB commit failures.
- `get_allocated_cash_amount()` - returns the current cash allocation before clear-cart resets the payment fields.
- `handle_pay_select(method)` — pay-select workflow described above.
- `handle_pay_clicked()` — final validation and emit `payRequested` payload.
- `focus_jump_next_pay_field()` — cycle focus to the next editable pay field.

## Integration Notes
- `MainLoader._on_payment_requested()` calls `pay_current_receipt(payment_split)` and forwards `tender` with the split.
- `PaidSaleCommitter` persists `tendered` for CASH in `receipt_payments` (non-cash sets `tendered = amount`).
- On success, `paymentSuccess` is emitted, the receipt context resets, sales table clears, and the payment frame resets.
- On repeated DB commit failure, `main.py` preserves the sale for retry. After the third failed attempt, it locks PAY, enables Print for the temporary recovery receipt, and instructs the cashier to print and clear the sales table.

## Cash Drawer (Network)
- Drawer opening is **independent** of receipt-printing toggle.
- Trigger point is in `main.py` after payment commit success (`pay_current_receipt`).
- Drawer is requested only when payment includes cash (`cash > 0`). Tender or change does not affect drawer gating.
	- Drawer pulse uses `modules/devices/printer_and_drawer.py::open_cash_drawer(...)` (`python-escpos` Network transport).
- Failure path logs error and reports to main StatusBar via `dialog_utils.report_to_statusbar()`.
- Special recovery path: if the cashier clears the sales table while the payment failure lock is active and `cashPayLineEdit` has a cash allocation, `main.py` opens the drawer before clearing payment fields. Ordinary clear cart actions do not open the drawer through this recovery path.

### Cash Drawer Config
- `ENABLE_CASH_DRAWER` — master toggle for drawer pulses.
- `CASH_DRAWER_PIN` — ESC/POS drawer pin (Epson commonly `2`).
- `CASH_DRAWER_TIMEOUT` — network timeout for drawer call.

## Receipt Printing (Network)
- `handle_print_clicked()` in `modules/payment/payment_panel.py` prints the last completed DB receipt in normal mode.
- During the payment DB failure lock, `handle_print_clicked()` prints a temporary `TEMP-DB-FAIL` recovery receipt from the current UI snapshot via `modules/payment/recovery_receipt.py`.
- Optional physical printing is gated by `ENABLE_PRINTER_PRINT` in `config.py`.
	- When disabled, `modules/devices/print_helper.py` prints receipt text to console.
	- When enabled, the helper calls `modules/devices/printer_and_drawer.py::print_receipt(receipt_text, blocking=True)`.
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

	Additionally, local keypad Tab navigation rules (keyboard Tab remains global; see keypad doc for details).
