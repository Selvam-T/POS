# Customer Display (Screen 2)

## Overview

The customer-facing display is a secondary output-only window that mirrors
transaction status for customers. It must never control sales, payments,
refunds, database writes, or cashier actions.

Status: base window and UI state management implemented; MainWindow
integration complete in `main.py`.

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
- Right panel: `screen2AdDisplayStack` with pages:
  - index 0: `pageIdle`
  - index 1: `pageScanning`
  - index 2: `pagePayment`
  - index 3: `pageCompleted`

## Data Flow

The customer display must not read the cashier sales table directly.
It accepts clean transaction data from the main window via:

- `CustomerDisplayWindow.update_transaction(payload)`

Payload shape:
- `state`: `idle | scanning | payment | completed`
- `items`: list of {quantity, description, amount}
- `total`: float or numeric string

## Behavior

- App starts: Idle page.
- First item added: Scanning page.
- Items updated: remain on Scanning page.
- Payment started: Payment page.
- Payment completed: Completed page, then return to Idle after timeout.
- Sale cleared: Idle page.

## Item Count Rule

Screen 2 shows a "Number of Items" summary. The count is calculated as:
- Each/unit items: sum of quantities (rounded to whole items).
- Kg items: counted as 1 item per line.

Reason: weighted produce can be fractional and should not inflate the item count
based on grams. Customers and cashiers expect one weighed product to read as one
item even if the weight is 0.25 kg or 1.75 kg.

## Work Pending

MainWindow integration and event hooks are done. Pending:

- Add a small demo/test runner if needed.

## MainWindow Integration

`MainLoader` creates a single `CustomerDisplayWindow` instance on startup
when `CUSTOMER_DISPLAY_ENABLED` is True. It updates the customer display
from sales and payment events.

Update hooks:
- Sales total updates -> Scanning state with refreshed items/total.
- Hold receipt loaded -> Scanning state with refreshed items/total.
- Payment requested -> Payment state.
- Payment success -> Completed state (auto returns to Idle).
- Cart cleared -> Idle state.
