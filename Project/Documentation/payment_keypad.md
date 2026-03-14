# Payment Keypad Controller

## Overview
The keypad maps [ui/payment_frame.ui](ui/payment_frame.ui) buttons to payment fields, providing numeric entry, fast amounts, and controlled Enter behavior without relying on system keyboard input.

## Files
- Controller: [modules/payment/keypad_controller.py](modules/payment/keypad_controller.py)
- UI: [ui/payment_frame.ui](ui/payment_frame.ui)
- Panel integration: [modules/payment/payment_panel.py](modules/payment/payment_panel.py)

## Wiring Rules
- Numeric buttons: `keyNumBtn0`-`keyNumBtn9`, `keyNumBtn00`, `keyNumBtndot` append input to the active field.
- Fast amounts: `keyDolBtn10`, `keyDolBtn50`, `keyDolBtn100` replace the active field with `10.00`, `50.00`, `100.00`.
- Clear/backspace: `keyFastBtnclr` clears, `keyFastBtnbksp` removes the last character.

## Targeting Behavior
- Input targets the last focused editable `QLineEdit`.
- Read-only line edits are skipped.
- The keypad tracks focus so button clicks do not steal the input target.

## Enter Key Behavior (Keypad)
- Allowed targets only:
  - Buttons: `*PaySlcBtn`, `*PayOpsBtn`, `keyVendorBtn`, `keyRefundBtn`.
  - Fields: `*PayLineEdit`, `tenderValLineEdit`.
- When focus is on an allowed button, keypad ENTER clicks the button.
- When focus is on an allowed field, keypad ENTER delegates to `PaymentPanel` to validate and jump using the existing Enter navigation rules.

## Notes
- Tab/Shift-Tab is intentionally left to the panel and UI tab order configuration.
- Validation and formatting still use [modules/ui_utils/input_handler.py](modules/ui_utils/input_handler.py) via `PaymentPanel`.
