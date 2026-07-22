# Scanner Input: Focus-First Routing And Protection

This document explains how HID barcode scanner input is routed while keeping normal keyboard typing usable.

## Goals

- Accept scans only in intended destinations.
- Prevent scanner Enter from submitting forms or clicking default buttons.
- Restore/clean leaked scanner text when scans are rejected.
- Keep fast manual typing usable in ordinary fields.

## Current Design

### Scanner Timing

Workflow diagram: [Barcode_Manager_High-Speed_Manual_Input.png](Barcode_Manager_High-Speed_Manual_Input.png)

`modules/devices/scanner.py` owns scanner/manual timing.

- `SCANNER_KEY_INTERVAL_SECONDS` identifies scanner-fast consecutive keys.
- `scanner_activity(timestamp, is_fast)` is emitted for each key press.
- A barcode is confirmed only when the scanner buffer has at least 3 characters and Enter completes the scan.

`BarcodeManager` consumes `is_fast`; it does not run a second, different timing threshold.

### Enter Suppression

`BarcodeManager` suppresses Enter/Return for `SCANNER_UI_SUPPRESS_SECONDS` after scanner-fast activity.

This protects forms and default buttons from a scanner's trailing Enter.

Printable letters and numbers are blocked only during the confirmed scanner-burst window and only when the focused widget is not barcode-allowed. This keeps normal fast manual typing usable while preventing scanner text from leaking into protected fields.

### Main Window Protection

The main window is the normal scan-to-cart surface, so it is not globally scanner-blocked.

Instead, `BarcodeManager` rejects scans selectively for protected manual fields:

- `qtyInput`
- `tenderValLineEdit`
- `cashPayLineEdit`
- `netsPayLineEdit`
- `paynowPayLineEdit`
- `voucherPayLineEdit`

If a scanner burst targets one of these fields:

- Printable scanner characters are swallowed.
- The widget restores to its last stable manual value.
- The completed scan is ignored so it does not add to the cart or open Product Menu.
- Manual typing and manual Enter remain unaffected outside scanner-burst timing.

Successful main-window product scans return focus to `salesTable` after the
add/increment completes.

### Dialog Overrides

Scanner-aware dialogs expose `dlg.barcode_override_handler`.

- Scans are accepted when focus is in a field whose `objectName` ends with `ProductCodeLineEdit`.
- If focus moves during a scan, the override can still accept it when the scan started in a `*ProductCodeLineEdit`.
- Scans in other fields are rejected and restored/cleaned.
- Known limitation: dialog name-search fields may still retain one leaked scanner character after rejection. They remain manual fields and do not own scanner input.

### Modal Block

Dialogs opened through `DialogWrapper.open_dialog_scanner_blocked(...)` enable modal scanner block.

- Confirmed scans do not route to the main sales table while a modal is open.
- Normal typing inside the active modal remains usable.
- Input outside the active modal is blocked as a fail-safe.
- Dialogs that need scanner input opt in with `dlg.barcode_override_handler`, and only `*ProductCodeLineEdit` fields may consume scans.

## Allowed vs Blocked Targets

Allowed:

- Sales table, when no modal/special context blocks scanner routing.
- Focused or scan-start dialog fields ending in `ProductCodeLineEdit`, when the dialog has an override.

Blocked and cleaned:

- `qtyInput` in the sales table.
- Main-window payment entry fields: `tenderValLineEdit`, `cashPayLineEdit`, `netsPayLineEdit`, `paynowPayLineEdit`, `voucherPayLineEdit`.
- Non-product-code fields in scanner-aware dialogs.
- Main-window scan routing while `receipt_context.source == 'HOLD_LOADED'`.
- Main-window scan routing while a scanner-blocked modal is open.

## Leak Cleanup

HID scanners type like keyboards, so scanner characters can briefly appear in the focused widget.

When a scan is confirmed and then rejected/ignored, `BarcodeManager`:

1. Restores protected main-window manual fields from stable text memory.
2. Restores other editable widgets from text captured at scan-burst start.
3. Falls back to single-character cleanup if no snapshot is available.

Date fields are covered by the same path: `QDateEdit` restores/cleans through its internal `lineEdit()`.

Name-search fields in scanner-aware dialogs can still retain a single leaked character after rejection. The scan is still blocked from barcode routing; this is a limitation of HID keyboard-style scanner cleanup in those manual fields.

If a scanner does not send Enter, no confirmed scan is emitted, so rejected-scan cleanup does not run.

## Edge Cases

- Fast manual typing may still briefly suppress Enter if it looks scanner-fast, but printable characters should continue flowing into the widget.
- A scan into a protected main-window field should swallow scanner characters during the confirmed burst and ignore the completed scan.
- A scan into other forbidden editable fields may briefly show characters until Enter confirms the scan; then the field should restore to its pre-scan text.
- A scanner configured with a prefix/suffix or serial/COM mode would allow cleaner zero-leak capture, but the current design keeps HID plug-and-play behavior.

## Developer Notes

- Timing constants live in `config.py`:
  - `SCANNER_KEY_INTERVAL_SECONDS`
  - `SCANNER_UI_SUPPRESS_SECONDS`
- Main event filtering and routing live in `modules/devices/barcode_manager.py`.
- Raw HID key buffering lives in `modules/devices/scanner.py`.
