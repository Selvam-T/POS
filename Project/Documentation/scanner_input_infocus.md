# Scanner input: focus-first routing and protection

This document explains how barcode scanner input is handled across the POS UI to ensure scans are accepted only where intended and ignored everywhere else without side effects.

## Goals

- Accept scans in the right place without user clicks.
- Prevent stray characters or unintended button activation during scans.
- Keep normal keyboard typing usable in forms.
- Provide useful diagnostics (focus path and cache lookup) to debug routing.

## Key ideas (current design)

- App-wide event filtering
  - Detects scan “bursts” using inter-key timing (very fast consecutive keys).
  - Swallows Enter briefly and blocks printable keys to non-allowed widgets during the burst.
- Modal scanner block
  - When a modal dialog (Manual, Vegetable, etc.) opens, a flag is set to swallow printable keys and Enter globally until the dialog closes.
  - A dim overlay sits on the main window to block mouse/touch clicks and we restore focus to the sales table on close.
- Focus-based routing with override
  - Default: scans go to the sales table handler.
  - Payment: when `refundInput` is focused, scan fills that field.
  - Product dialog: installs a temporary barcode override that accepts scans only when `productCodeLineEdit` is focused; otherwise ignores and cleans leaks.
- Leak cleanup fallback
  - If a first character leaks into a disallowed field (HID wedge limitation), we remove it best-effort from QLineEdit/QTextEdit family widgets.
- Enter/Return control
  - During scan bursts, Enter is briefly suppressed to avoid clicking default buttons.
  - In Product dialog, Enter on line edits behaves like Tab to advance focus instead of clicking a button; action buttons are non-default unless focused.
- Always-on cache diagnostics
  - Every scan logs an in-memory cache lookup result (found/key/name/price/cache size) for quick diagnosis.
  - Optional focus-path logging prints active window, focus chain, and whether a barcode override is active.

## Allowed vs blocked targets

- Allowed
  - Sales table (default destination when no special context applies).
  - `productCodeLineEdit` in Product Management (when focused).
  - `refundInput` in Payment frame (when focused).
- Blocked and cleaned
  - `qtyInput` (sales table quantity editor).
  - All fields in Manual Entry and Vegetable dialogs (via modal block + read-only text for Manual).
  - Any non-focused fields in Product dialog; leaks are cleaned.

## Challenges and limitations

- HID “keyboard wedge” scanners type like a user:
  - The very first key can arrive before detection logic kicks in, leading to a rare single-character leak.
  - Default-button behavior in GUIs can cause Enter to activate buttons if not suppressed.
- Timing-based burst detection is heuristic:
  - Extremely fast typists or atypical scanners could mimic similar timings.

## Mitigations in this build

- Modal scanner block for dialogs prevents both printable keys and Enter everywhere while the dialog is open.
- Global suppression windows for Enter and printable keys during active scan bursts.
- Local Enter-as-Tab wiring and non-default buttons in Product dialog.
- Centralized best-effort leak cleanup for QLineEdit/QTextEdit widgets.

## Options to eliminate first-char leaks (not required now)

- Scanner prefix/suffix
  - Configure a distinct prefix (e.g., F9 or control code STX) and suffix (Enter or ETX) so the app detects scans from the very first character and swallows every scan keystroke.
  - Requires scanning vendor programming barcodes; no PC driver typically needed. If unknown model, defer.
- COM/serial integration
  - Read the scan as a single message from a serial port rather than as keystrokes; perfect focus control with zero visual leaks.
  - Not chosen for this project to keep plug-and-play behavior.

## Rationale for current design

- Works with any HID scanner without hardware changes.
- Keeps normal typing usable while making scans safe.
- Centralizes complexity (event filter, modal block, override) and uses small helpers for maintainability.
- Provides robust UX: overlay blocks clicks, focus is restored to the sales table, and status bar feedback remains consistent.

## Edge cases considered

- Scans during modal dialogs: fully swallowed; no sales increments or field edits.
- Focus on `qtyInput`: scan ignored and leak cleaned.
- Focus on `refundInput`: scan is accepted and applied to the field.
- Product not found: Product dialog opens in ADD mode with code prefilled; override active only on `productCodeLineEdit`.

## Developer notes

- Key helpers in `main.py`:
  - Event filter with `_on_scanner_activity` timing window.
  - `_start_scanner_modal_block()` / `_end_scanner_modal_block()` and dim overlay helpers.
  - `_barcodeOverride` for Product dialog; `_ignore_scan()` for leak cleanup and logging.
- Debug toggles (in `config.py`): `DEBUG_SCANNER_FOCUS`, `DEBUG_FOCUS_CHANGES`, `DEBUG_CACHE_LOOKUP`.
- When adding new modal dialogs, always:
  - Show the overlay, start the scanner modal block, and restore focus to the sales table on close.
  - Avoid default buttons unless explicitly focused; consider Enter-as-Tab on multi-field forms.

## Future improvements (optional)

- Add a per-dialog child event filter to swallow printable keys for all unintended fields, even without modal block.
- If scanner model becomes known, enable a prefix/suffix for zero-leak capture.
- Tune timing thresholds if you observe false positives/negatives.
