# Payment Frame Controller

## Overview
The payment frame is controlled by `PaymentPanel` and is responsible for allocating payment methods, enforcing tender/balance rules, and enabling the Pay action only when valid. The controller emits payment events to the main window but does not perform database writes.

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
- **Voucher** is integer-only.
- **NETS / PayNow / Cash** accept 2-decimal floats.

**Allocation formula:**
```
unalloc = total - (nets + paynow + voucher + cash)
```

## UI Behavior
### Gating and Enablement (ReceiptContext-aware)
- `resetPayOpsBtn` is enabled only when `totalValPayLabel` > $0.00.
- `printPayOpsBtn` is enabled only when `totalValPayLabel` is $0.00 (or empty).
- `payPayOpsBtn` requires all of the following:
	- `total > 0`
	- `unalloc == 0`
	- `tender >= cash` when cash is present
	- `receipt_context.status` is `NONE` (new receipt will be created) or `UNPAID` (existing receipt will be marked PAID)

### Unallocated Amount
- Updated whenever any payment line changes or total changes.
- If `unalloc > 0`: highlight `unallocPayFrame` and show warning.
- If `unalloc == 0`: remove highlight and clear warning (unless a cash error is active).

### Cash Tender & Balance
- `tenderValLineEdit` is cash tendered only.
- `balanceValLineEdit = tender - cash` (can go negative while typing).
- If `balance < 0`, a status error is shown.
- Tender and balance widgets stay visible but are disabled when `cash == 0`.

### Pay Button Enable Rules
`payPayOpsBtn` is enabled only when:
- `total > 0`
- `unalloc == 0`
- `tender >= cash` (only enforced if `cash > 0`)

### Read-Only Policy
- When `unalloc == 0`, any empty or zero payment field becomes read-only.
- Fields with values > 0 remain editable to allow reductions.

### Pay Select Buttons
For each method button (cash/nets/paynow/voucher):
1. Clear the corresponding line edit.
2. Fill remaining allocation into that field.
3. If clicked again, only focus/select the field.

## Controller API
- `set_payment_default(total)`
- `clear_payment_frame()`
- `reset_payment_grid_to_default()`
- `recalc_unalloc_and_ui()`
- `recalc_cash_balance_and_ui()`
- `update_readonly_policy()`
- `update_pay_button_state()`
- `handle_pay_select(method)`
- `handle_pay_clicked()`
- `focus_jump_next_pay_field()`

## Integration Notes
- `MainLoader._on_payment_requested()` calls `pay_current_receipt(payment_split)` (stubbed).
- On success, `paymentSuccess` is emitted, the receipt context resets, sales table clears, and the payment frame resets.
