# Customer Display (Screen 2)

## Overview

The customer-facing display is a secondary output-only window that mirrors
transaction status for customers. It must never control sales, payments,
refunds, database writes, or cashier actions.

Status: refactored to use overlay-based payment results instead of stacked pages.
Simplified state machine from 4 states to 2 states (idle, payment).
Full-screen overlay displays a success payment message with auto-hide timer.
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
- Manage the idle/full-screen and active-sale split display.
- Render the sales table and total.
- Render the generic PayNow QR label at fixed 250 x 250 during active sales.
- Handle screen placement and connect/disconnect events.
- Avoid stealing focus from the cashier screen.
- Keep the sales table auto-scrolled with scrollbar hidden.

## UI Elements

The screen uses `ui/screen2.ui` with two main regions:
- Left panel: `screen2LeftFrame` and `screen2SalesTable`.
- Right panel: `screen2RightFrame` and `screen2AdDisplayStack`.
  - `screen2QrLabel`: a `QLabel` (250x250) placed on the `pagePayment` view. The generated generic PayNow QR `QPixmap` is set here by `CustomerDisplayWindow.generate_and_set_qr()`.
### Right Panel State Page

The right panel `screen2AdDisplayStack` contains one active-sale page:
- index 0: `pagePayment` - displays payment information and the generic PayNow QR code

Note: `pageCompleted` has been removed. Payment results now display via
`paymentResultOverlay` (full-screen overlay with semi-transparent background).

Current behavior: when the sales table has rows, `pageSplit` is active and the
right panel defaults to `pagePayment` so the customer can scan the generic
PayNow QR early.

The UI `screen2AdDisplayStack` defaults to index `0` (`pagePayment`) in
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

### Payment Result Overlay (Lightbox)

Displays the payment success message with auto-hide timer.

**Structure:**
- `paymentResultOverlay`: full-screen semi-transparent dark overlay
- `paymentResultCard`: white background with colored border and centered labels

**Card Styling:**
- Success: green border (#4CAF50)
- Auto-hides after `CUSTOMER_DISPLAY_IDLE_TIMEOUT` seconds

**Method:**
- `show_payment_result(total: float | None = None, greeting: str | None = None)`
  - `total`: optional transaction total
  - `greeting`: optional custom greeting text

**Design Decision - Payment Error Handling:**
Payment database errors (e.g., connection failures, commit rollbacks) are NOT propagated to the customer display.
- The overlay is displayed immediately when PAY is clicked, before database operations complete.
- This ensures customers always see a positive acknowledgment regardless of backend processing success or failure.
- Database failures are logged to the cashier status bar (cashier-only view) for troubleshooting, but do not affect the customer experience.
- Cashier-side recovery after repeated DB failures is handled entirely on the
  main/payment panel: after three failed attempts PAY is locked as `PAY err`,
  Print can produce a `TEMP-DB-FAIL` snapshot receipt, and Clear Cart resets the
  flow. None of these recovery details are shown on the customer display.
- Rationale: Payment DB issues are system-level failures, not customer-facing errors. Showing error messages to customers damages trust and creates confusion at the point of sale.

### Fallback UI

If `ui/screen2.ui` cannot be loaded, `modules/customer_display/fallback_screen2.py`
builds a minimal customer display in code.

Fallback includes:
- Basic sale item table, item count, total, company, date, and time.
- Payment success overlay using the same `paymentResult*` widget names as the
  normal UI so `show_payment_result()` works through the standard code path.

Fallback intentionally omits:
- Fullscreen idle ad rotation.
- PayNow QR display.

### Configuration

- New config key: `CUSTOMER_DISPLAY_IDLE_AD_INTERVAL` (seconds) controls the
  rotation interval for fullscreen idle ads. See `config.py` under the
  Customer Display settings section.

## Data Flow

The customer display must not read the cashier sales table directly.
It accepts clean transaction data from the main window via:

- `CustomerDisplayWindow.update_transaction(payload)`

Payload shape:
- `state`: `idle | payment` (active sale defaults to `payment`)
- `items`: list of {quantity, description, amount, unit}
- `total`: float or numeric string

Payment result display is separate from state machine:
- `show_payment_result(total: float | None = None, greeting: str | None = None)` - displays overlay with success message
- `hide_payment_result_overlay()` - hides overlay and stops auto-hide timer

## Behavior

- **App starts**: Idle page (full screen if no rows, split if rows exist).
- **Items added**: Split mode with sales details on the left and generic PayNow QR on the right.
- **Payment initiated**: PAY shows the payment result overlay; it does not control the QR page.
- **PAY clicked**: Green success overlay appears immediately with transaction total and greeting, auto-hides after timeout.
- **Sale cleared**: Idle page (full screen or split, depending on context).
- **New items scanned during overlay**: Overlay immediately hides, items merge into cart.

**Payment Success Overlay Behavior:**
- The overlay displays on PAY click, not after payment confirmation from the database.
- The overlay is always a success message; there is no failure state shown to customers.
- If the database commit fails (transaction rollback, DB unavailable), the cashier sees an error in the status bar, but the customer sees the success overlay unchanged.
- After the timeout, the overlay auto-hides when payment commit succeeds and the cart is cleared. If the database commit fails, the overlay remains visible and the cart is preserved until staff retries or clears it manually. After three failed retries, cashier-side recovery may print a `TEMP-DB-FAIL` receipt before clearing.

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
- Add greeting message (e.g., from `config.GREETING_SELECTED`)
- Adjust colors, fonts, and styling
- Modify auto-hide timeout via `CUSTOMER_DISPLAY_IDLE_TIMEOUT`
- Adjust transparency via stylesheet

All customization occurs in `customer_display.py` -> `show_payment_result()` method.

## Work Pending

- Customization of overlay appearance (messages, icons, transparency)
- Barcode scan detection to hide overlay immediately
- Full payment flow integration testing

## MainWindow Integration

`MainLoader` creates a single `CustomerDisplayWindow` instance on startup
when `CUSTOMER_DISPLAY_ENABLED` is True. It updates the customer display
from sales and payment events.

Update hooks:
- Sales total updates -> Payment state (updated items/total).
- Hold receipt loaded -> Payment state (updated items/total).
- Payment requested -> `show_payment_result(total=...)` + overlay display (triggered immediately on PAY click).
- Item entry (vegetable/manual) -> `hide_payment_result_overlay()`.
- Cart cleared -> Idle state.

**Payment Processing Note:**
The success overlay is triggered by the PAY request signal, not by payment success/failure callbacks.
Database commit failures do not trigger any customer-facing response; they are logged to the cashier status bar only.
This decouples customer experience (always positive) from backend robustness (failures handled internally).

