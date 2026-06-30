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

This protects forms and default buttons from a scanner's trailing Enter. Printable letters and numbers are not blocked solely because they arrived quickly, which avoids the old fast-manual-typing pause in fields such as receipt notes.

### Dialog Overrides

Scanner-aware dialogs expose `dlg.barcode_override_handler`.

- Scans are accepted when focus is in a field whose `objectName` ends with `ProductCodeLineEdit`.
- If focus moves during a scan, the override can still accept it when the scan started in a `*ProductCodeLineEdit`.
- Scans in other fields are rejected and restored/cleaned.

### Modal Block

Dialogs opened through `DialogWrapper.open_dialog_scanner_blocked(...)` enable modal scanner block.

- Confirmed scans do not route to the main sales table while a modal is open.
- Normal typing inside the active modal remains usable.
- Input outside the active modal is blocked as a fail-safe.

## Allowed vs Blocked Targets

Allowed:

- Sales table, when no modal/special context blocks scanner routing.
- Focused dialog fields ending in `ProductCodeLineEdit`, when the dialog has an override.

Blocked and cleaned:

- `qtyInput` in the sales table.
- Non-product-code fields in scanner-aware dialogs.
- Main-window scan routing while `receipt_context.source == 'HOLD_LOADED'`.
- Main-window scan routing while a scanner-blocked modal is open.

## Leak Cleanup

HID scanners type like keyboards, so scanner characters can briefly appear in the focused widget.

When a scan is confirmed and then rejected/ignored, `BarcodeManager`:

1. Restores the editable widget text captured at scan-burst start.
2. Falls back to single-character cleanup if no snapshot is available.

If a scanner does not send Enter, no confirmed scan is emitted, so rejected-scan cleanup does not run.

## Edge Cases

- Fast manual typing may still briefly suppress Enter if it looks scanner-fast, but printable characters should continue flowing into the widget.
- A scan into a forbidden editable field may briefly show characters until Enter confirms the scan; then the field should restore to its pre-scan text.
- A scanner configured with a prefix/suffix or serial/COM mode would allow cleaner zero-leak capture, but the current design keeps HID plug-and-play behavior.

## Developer Notes

- Timing constants live in `config.py`:
  - `SCANNER_KEY_INTERVAL_SECONDS`
  - `SCANNER_UI_SUPPRESS_SECONDS`
- Main event filtering and routing live in `modules/devices/barcode_manager.py`.
- Raw HID key buffering lives in `modules/devices/scanner.py`.
- Debug toggles:
  - `DEBUG_SCANNER_FOCUS`
  - `DEBUG_FOCUS_CHANGES`
  - `DEBUG_CACHE_LOOKUP`
