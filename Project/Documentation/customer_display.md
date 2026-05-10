# Customer Display (Screen 2)

## Overview

The customer-facing display is a secondary output-only window that mirrors
transaction status for customers. It must never control sales, payments,
refunds, database writes, or cashier actions.

Status: refactored to use overlay-based payment results instead of stacked pages.
Simplified state machine from 4 states to 2 states (idle, payment).
Full-screen overlay displays payment success/failure messages with auto-hide timer.
MainWindow integration complete in `main.py`.

## Configuration

Configured in `config.py`:

- `CUSTOMER_DISPLAY_ENABLED`
- `CUSTOMER_DISPLAY_TEST_MODE`
- `CUSTOMER_SCREEN_INDEX`
- `CUSTOMER_SCREEN_WIDTH`
- `CUSTOMER_SCREEN_HEIGHT`
- `CUSTOMER_DISPLAY_FULLSCREEN`
- `CUSTOMER_DISPLAY_AUTO_DETECT`
- `CUSTOMER_DISPLAY_IDLE_TIMEOUT`

Notes:
- Test mode shows the display on the main monitor as a normal window.
- Physical mode places the display on the configured screen index only
  when it exists.

## Module

File: `modules/customer_display/customer_display.py`
Class: `CustomerDisplayWindow`

Responsibilities:
- Load `ui/screen2.ui`.
- Manage page states (Idle, Scanning, Payment, Completed).
- Render the sales table and total.
- Render the QR label at fixed 250 x 250.
- Handle screen placement and connect/disconnect events.
- Avoid stealing focus from the cashier screen.
- Keep the sales table auto-scrolled with scrollbar hidden.

## UI Elements

The screen uses `ui/screen2.ui` with two main regions:
- Left panel: `screen2PurchaseFrame` and `screen2SalesTable`.
### Right Panel State Pages

The right panel `screen2AdDisplayStack` now contains 2 pages:
- index 0: `pageIdle` — displays rotating idle ads or promotions
- index 1: `pagePayment` — displays payment information and QR code

Note: `pageCompleted` has been removed. Payment results now display via
`paymentResultOverlay` (full-screen overlay with semi-transparent background).

The UI `screen2AdDisplayStack` defaults to index `0` (idle) in
`ui/screen2.ui`. `CustomerDisplayWindow` also defensively initializes both
`screen2AdDisplayStack` and `screen2ModeStack` to their idle/full-idle
positions on load to avoid showing an unintended page at startup.

### Top-Level Mode Stack

- The UI contains a top-level `QStackedWidget` named `screen2ModeStack`.
  - `pageIdleFull` (index 0): a fullscreen idle page used when there are no
    items in the sales table. This page contains `screen2IdleFullLabel` which
    displays fullscreen ads from `assets/ads` or fallback text when images
    aren't available.
  - `pageSplit` (index 1): the original split layout with the purchase frame
    on the left and `screen2AdDisplayStack` on the right.

Mode selection is driven solely by whether the main `sales_table` has rows
(uses existing `get_sales_data()` / `is_transaction_active()` semantics).
If the sales table is empty the display switches to `pageIdleFull`; otherwise
it shows `pageSplit`.

### Payment Result Overlay (New)

- `paymentResultOverlay` is a full-screen `QFrame` widget that sits above all content
  with semi-transparent background (`rgba(0, 0, 0, 180)`).
- Initially hidden; displayed only during payment result display.
- Positioned absolutely outside the layout to ensure Z-order priority.
- Contains `paymentResultLabel` which shows success/failure messages with color coding:
  - **Success**: Green background (#4CAF50) + "Payment Completed. Thank You!"
  - **Failure**: Red background (#F44336) + "Payment Failed. Please Retry."
- Auto-hides after `CUSTOMER_DISPLAY_IDLE_TIMEOUT` seconds via single-shot timer.
- Can be immediately hidden if new items are scanned/entered or user retries payment.
- Uses `raise_()` and geometry management to ensure it stays on top.
- `resizeEvent()` handler keeps overlay synchronized with dialog resize.

### Controller Methods

- `set_mode_full_idle()` and `set_mode_split()`: change top-level mode.
- `show_payment_result(is_success: bool)`: display payment overlay with appropriate message and auto-hide.
- `hide_payment_result_overlay()`: immediately hide overlay and disconnect timer.
- When entering full-idle mode the window loads images from `assets/ads`
  and runs a timed rotation (slideshow) of available images.
- If an ad image fails at runtime the controller logs via `modules.ui_utils.error_logger.log_error_message`.

### Configuration

- New config key: `CUSTOMER_DISPLAY_IDLE_AD_INTERVAL` (seconds) controls the
  rotation interval for fullscreen idle ads. See `config.py` under the
  Customer Display settings section.

## Data Flow

The customer display must not read the cashier sales table directly.
It accepts clean transaction data from the main window via:

- `CustomerDisplayWindow.update_transaction(payload)`

Payload shape:
- `state`: `idle | payment` (state machine now simplified to 2 states)
- `items`: list of {quantity, description, amount, unit}
- `total`: float or numeric string

Payment result display is separate from state machine:
- `show_payment_result(is_success: bool)` — displays overlay with result message
- `hide_payment_result_overlay()` — hides overlay and stops auto-hide timer

## Behavior

- **App starts**: Idle page (full screen if no rows, split if rows exist).
- **Items added**: Split mode with idle ads on right panel.
- **Payment initiated**: Payment page with payment info and QR code.
- **Payment success**: Green overlay with success message appears, auto-hides after timeout, cart clears.
- **Payment failure**: Red overlay with failure message appears, auto-hides after timeout, cart remains for retry.
- **Sale cleared**: Idle page (full screen or split, depending on context).
- **New items scanned during overlay**: Overlay immediately hides, items merge into cart.

## Item Count Rule

Screen 2 shows a "Number of Items" summary. The count is calculated as:
- Each/unit items: sum of quantities (rounded to whole items).
- Kg items: counted as 1 item per line.

Reason: weighted produce can be fractional and should not inflate the item count
based on grams. Customers and cashiers expect one weighed product to read as one
item even if the weight is 0.25 kg or 1.75 kg.

## Customization - Payment Result Overlay

The payment result overlay can be customized via `show_payment_result()` method:
- Change message text
- Add success/failure icons
- Add greeting message (e.g., from `config.GREETING_SELECTED`)
- Adjust colors, fonts, and styling
- Modify auto-hide timeout via `CUSTOMER_DISPLAY_IDLE_TIMEOUT`
- Adjust transparency via stylesheet

All customization occurs in `customer_display.py` → `show_payment_result()` method.

## Work Pending

- Customization of overlay appearance (messages, icons, transparency)
- Barcode scan detection to hide overlay immediately
- Full payment flow integration testing

## MainWindow Integration

`MainLoader` creates a single `CustomerDisplayWindow` instance on startup
when `CUSTOMER_DISPLAY_ENABLED` is True. It updates the customer display
from sales and payment events.

Update hooks:
- Sales total updates → Payment state (updated items/total).
- Hold receipt loaded → Payment state (updated items/total).
- Payment requested → `hide_payment_result_overlay()` + Payment state.
- Payment success → `show_payment_result(is_success=True)` + overlay display.
- Payment failure → `show_payment_result(is_success=False)` + overlay display.
- Item entry (vegetable/manual) → `hide_payment_result_overlay()`.
- Cart cleared → Idle state.

Note: `show_payment_result()` handles all payment result display logic.
The state machine only manages display between Idle and Payment modes.
