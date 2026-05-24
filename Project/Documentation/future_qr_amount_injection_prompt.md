# Future Prompt: PayNow QR With Amount Injection

Use this prompt when asking an AI coding agent to reintroduce amount-specific
PayNow QR behavior into this POS project.

## Context

The current production flow intentionally uses a generic PayNow QR on Screen 2.
The QR does not include amount tag `54`; customers manually enter the
cashier-confirmed amount in their banking app. During an active sale, Screen 2
shows `pageSplit`, with cart details on `screen2LeftFrame` and the generic QR on
the right-side `pagePayment`.

Future work may require QR codes that include the PayNow amount. That is a
different state model and must be implemented deliberately.

## Goal

Reimplement amount-injected PayNow QR codes safely.

The system should:
- Show `pageIdleSplit` in the right panel during an active sale before a valid
  PayNow amount has been confirmed.
- Switch to `pagePayment` only when a valid PayNow amount is available and a QR
  has been generated for that exact amount.
- Regenerate the QR if the PayNow amount changes and is valid.
- Invalidate or hide the QR if the PayNow amount is cleared, reset, or becomes
  invalid.
- Show a short customer-facing notification before switching pages or replacing
  the QR, so the customer understands that the payment QR changed.

## Required UI Restoration

Restore `pageIdleSplit` inside `ui/screen2.ui` under:

`pageSplit / screen2RightFrame / screen2AdDisplayStack`

The right-side stack should contain:
- `pageIdleSplit`: right-panel idle/ads/message page
- `pagePayment`: QR/payment page

Restore an idle label/widget for the split page, for example:
- `idleAdsLabel`

Update `modules/customer_display/customer_display.py` to cache and use this
label again if right-panel split idle messages or ads are required.

## QR Payload Requirements

Restore amount support in `modules/payment/qr_generator.py`.

Suggested API:

```python
def build_paynow_payload(ref_value: str | None = None, amount_value: float | None = None):
    ...

def generate_qr_pixmap(
    ref_value: str | None = None,
    amount_value: float | None = None,
    target_size: int = 250,
):
    ...
```

When amount injection is enabled:
- Include merchant account tag `03` with value `"0"` so amount is fixed.
- Include payload tag `54` with the amount formatted to two decimals.
- Validate that amount is greater than zero.
- Raise a clear error if the amount is missing or invalid.

When amount injection is disabled:
- Omit tag `54`.
- Generate the generic merchant QR.

Add or restore a config flag only if the rest of the program logic supports both
modes. Do not expose a config flag that can break runtime behavior.

## State Model

Track the displayed QR state explicitly. Suggested fields in `main.py` or a
small controller:

```python
_customer_paynow_qr_active: bool
_customer_paynow_qr_amount: float | None
_customer_paynow_qr_stale: bool
```

Definitions:
- **PayNow field value**: current text/value in `paynowPayLineEdit`.
- **Displayed QR amount**: amount used to generate the QR currently visible on
  `pagePayment`.
- **Stale QR**: QR is visible but no longer matches the current payment state.

Do not treat "PayNow field has value" and "valid QR is visible" as the same
state.

## Activation Rules

`pageIdleFull`
- Active only when the sales table is empty.
- Triggered by startup/no sale, successful cleanup, or manual clear.

`pageSplit + pageIdleSplit`
- Active when the sales table has rows but there is no valid active PayNow QR.
- This should be the default active-sale right panel in amount-injection mode.

`pageSplit + pagePayment`
- Active only when a valid PayNow amount has generated a QR.
- The QR must match the currently accepted PayNow amount.

`paymentResultOverlay / paymentResultCard`
- Triggered by PAY button after valid payment allocation.
- It represents cashier-accepted payment completion, not DB commit success.
- If DB commit fails, keep the overlay pinned until staff clears the sale.

## Trigger Rules

### Generate QR

Trigger QR generation when:
- Focus is in `paynowPayLineEdit`.
- ENTER is pressed.
- The field validates successfully.
- The PayNow amount is greater than zero.

Then:
- Show a short message such as "Updating PayNow QR..."
- Wait about 2 seconds.
- Generate QR with the validated amount.
- Switch/show `pagePayment`.
- Display a short confirmation such as "PayNow QR updated."

### Clear QR

Trigger QR invalidation when:
- `paynowPayLineEdit` becomes empty or zero.
- Payment method selection changes away from PayNow.
- Sale rows change in a way that resets payment allocations.
- Cart total changes and the existing QR amount may no longer be valid.

Then:
- Show a short message such as "PayNow QR cleared. Payment amount changed."
- Wait about 2 seconds.
- Switch right panel to `pageIdleSplit`.
- Clear/stale the stored QR state.

### Regenerate QR

If `pagePayment` is active and `paynowPayLineEdit` changes to a new non-zero
valid amount:
- Mark the existing QR as stale.
- Do not silently replace it while the user is typing.
- Regenerate only after ENTER validates the new amount.
- Show the 2-second message before replacing the visible QR.

## PAY Button Rules

The PAY button should not generate QR codes.

PAY should:
- Validate the full payment allocation.
- Show `paymentResultOverlay` / `paymentResultCard`.
- Attempt the DB commit.
- On success, run normal cleanup, clear the sales table, and reach
  `pageIdleFull`.
- On DB failure, keep the overlay visible, preserve the sales table/payment
  panel/receipt context, and let staff manually clear or retry.

## Files Likely To Change

- `ui/screen2.ui`
- `modules/customer_display/customer_display.py`
- `modules/payment/qr_generator.py`
- `modules/payment/payment_panel.py`
- `main.py`
- `config.py` if a runtime flag is reintroduced
- `Documentation/customer_display.md`
- `Documentation/qr_generator.md`
- `Documentation/qr_code_generator.md`

## Tests And Verification

Add or update focused tests where practical:
- QR payload includes tag `54` only when amount mode is enabled.
- QR payload rejects invalid or zero amount.
- PAY button does not activate `pagePayment`.
- PayNow ENTER emits/activates QR generation only for valid positive amounts.
- Clearing PayNow invalidates QR state.
- Sale row update invalidates stale amount QR.

Manual verification:
- Active sale starts in `pageIdleSplit`.
- Enter valid PayNow amount and press ENTER: message appears, then QR appears.
- Change PayNow amount: old QR is not silently replaced; ENTER regenerates.
- Clear PayNow amount: message appears, then right panel returns to
  `pageIdleSplit`.
- Press PAY after valid allocation: overlay appears.
- Simulate DB failure: overlay remains pinned until staff clears sale.
- Clear sale: display returns to `pageIdleFull`.

## Important Constraint

Do not reintroduce amount injection as a partial flag-only change. The UI state,
payment field validation, QR regeneration, stale QR handling, and documentation
must be implemented together.
