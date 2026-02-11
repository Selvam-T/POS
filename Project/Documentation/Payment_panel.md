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

## UI Behavior (current)
- **Validation**: All payment fields (cash, nets, paynow, tender) are validated via `modules/ui_utils/input_handler.handle_currency_input` on focus-out/Enter. Validation failures block Pay and surface on `payStatusLabel`.
- **Unallocated tracking**: Recomputed on any payment change. Highlights the unalloc frame when `unalloc > 0`; clears highlight when `unalloc <= 0`.
- **Status priority**: validation error > (cash>0 and tender<cash) > (unalloc>0) > (unalloc<0) > clear.
- **Tender/Balance**: Tender UI is shown/enabled only when `cash > 0`. `balance = tender - cash` (may go negative while typing); tender placeholder shows only when `cash > 0` and tender is empty.
- **Placeholders**: Pay-method placeholders show only when `unalloc > 0` and the field is empty. Tender placeholder is conditional on cash being present.
- **Read-only / focus gating**: When `unalloc == 0`, zero-valued pay fields become read-only and lose focusability; fields with values stay editable. Tender is locked/no-focus when `cash <= 0`.
- **Pay-select buttons**: Choosing a method fills that method with the full total (voucher uses int), clears the other methods, recalculates, and moves focus (cash→tender, others→Pay). A second click just focuses/selects.
- **Enter navigation**: Context-aware routing—cash with `unalloc == 0` jumps to tender; pay fields with `unalloc == 0` jump to Pay; tender enforces `tender >= cash` before advancing and will jump back/select-all if short; if tender>cash while unalloc>0, focus jumps to the next pay field.
- **Pay button gating**: Requires `total > 0`, `unalloc == 0`, no validation errors, receipt status in (`NONE`, `UNPAID`), and when `cash > 0`, `tender >= cash`. Reset is enabled only when total>0; Print only when total is zero/empty.

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
- `MainLoader._on_payment_requested()` calls `pay_current_receipt(payment_split)` (stubbed).
- On success, `paymentSuccess` is emitted, the receipt context resets, sales table clears, and the payment frame resets.

## Why shared focus helpers are not used here
- `FieldCoordinator` / `FocusGate` provide generic Enter→next/validate/status and static gating used by other dialogs (e.g., vegetable_menu). Payment flow depends on live allocation math (unalloc, tender vs cash), per-method auto-fill/zeroing, and conditional tender visibility. These dynamic rules require bespoke branching on every change, so adopting the shared coordinator would still leave most custom logic duplicated. Currency validation remains shared via `input_handler` (and `input_validation`/`ui_feedback`).
