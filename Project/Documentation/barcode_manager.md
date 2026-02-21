# BarcodeManager — Current Behavior (Jan 2026)

This document describes the **current** behavior of `BarcodeManager` in `modules/devices/barcode_manager.py`, and clarifies how it differs from the legacy implementation described in `Documentation/barcode_managerOLD.md` / `POS temp/barcode_managerOLD.py`.

## Purpose

`BarcodeManager` centralizes scanner behavior:

- Routes scanned barcodes to the right destination (sales table, refund input, product code fields)
- Prevents scan “leaks” (first-character wedge leakage) via best-effort cleanup
- Provides **fail-safe gating** when modal dialogs are open
- Suppresses Enter/Return during scan bursts to avoid triggering default buttons

## Core Concepts

### 1) Modal block (fail-safe gating)

`_modalBlockScanner` is a *global safety guard* used while modal dialogs are open.

- When enabled, barcode scans are prevented from reaching the main-window routing (e.g., sales table add).
- The event filter is designed to stop keystrokes from leaking into the main window while still allowing normal typing inside the active modal dialog.

This is typically toggled by `DialogWrapper`:

- `_start_scanner_modal_block()` when opening most dialogs
- `_end_scanner_modal_block()` on dialog close

### 2) Barcode override (dialog-owned routing)

Dialogs that want to “own” scans temporarily (notably Product Menu) install an override:

- `set_barcode_override(callable)`
- `clear_barcode_override()`

**Override is checked first** in `on_barcode_scanned()`.

Current gating rule:

- Override is allowed to consume a scan when the focused widget’s `objectName` ends with `ProductCodeLineEdit`.
- Additionally, if focus shifts mid-scan (e.g., auto-lookup moves focus to a button), the override is still allowed if the scan burst **started** in a `*ProductCodeLineEdit`.
- Otherwise the scan is rejected and any leaked character is cleaned up (best-effort), and the dialog may show an error in a status label.

This makes Product Menu scanner behavior both:

- **usable** (scan into the code field)
- **safe** (scan cannot accidentally add to the sale while a modal is up)

### 2b) ReceiptContext HOLD_LOADED block (cart-protection)

When the main window `ReceiptContext.source == 'HOLD_LOADED'` (i.e., the cart was populated by loading a held receipt), scanner-driven routing is blocked at the manager level.

Current rule:

- `BarcodeManager.on_barcode_scanned()` checks the parent window’s `receipt_context`.
- If `source == 'HOLD_LOADED'`, the scan is ignored via `_ignore_scan(...)`.

Important nuance:

- This check happens **after** the dialog override logic, so dialogs that explicitly own scans (via `set_barcode_override(...)` and `*ProductCodeLineEdit`) can still accept scans when appropriate.

Goal:

- Prevent accidental scan-to-cart behavior while a held receipt is being paid.
- Still allow normal keyboard typing (scanner bursts are blocked; manual typing remains unaffected).

### 3) Focus-based routing (no override)

If no override consumes the scan, `BarcodeManager` applies routing rules:

- If `_modalBlockScanner` is enabled: ignore scan + cleanup leak
- If `ReceiptContext.source == 'HOLD_LOADED'`: ignore scan + cleanup leak
- If focus is `qtyInput`: ignore scan + cleanup leak
- If focus is `refundInput`: write barcode into `refundInput`
- Otherwise: treat as a sales-table barcode
  - If product not found: open Product Menu in ADD mode with `initial_code`
  - If product found: add to sales table via `handle_barcode_scanned(...)`

### 4) Scan-burst key suppression

Barcode scanners often send fast key bursts (HID wedge). `BarcodeManager`:

- Suppresses Enter/Return briefly during scanner activity
- During an active burst window, swallows printable keys unless the focused widget is allowed

Allowed during burst:

- `refundInput`
- any widget whose `objectName` ends with `ProductCodeLineEdit`

## Leak Cleanup

`_cleanup_scanner_leak(...)` attempts to remove a leaked first character from common editable widgets (e.g., `QLineEdit`, `QTextEdit`, `QPlainTextEdit`) when a scan is rejected.

Current rule (Jan 2026):

- If the focused widget’s text ends with the first character of the scanned barcode, it is removed (best-effort).
- This applies regardless of the existing value length (no `len<=3` restriction) and does not depend on a timing window.

Rationale: some widgets (e.g., price fields) often contain longer values; leak cleanup must remain effective even when the field already has content.

## Integration Points

- Main window creates `BarcodeManager` and installs its event filter on the app.
- `DialogWrapper.open_dialog_scanner_blocked(...)` uses modal block to protect the main window.
- Main window sets `ReceiptContext.source = 'HOLD_LOADED'` when a hold receipt is loaded; BarcodeManager uses this to block scan-to-cart routing.
- Product Menu installs a temporary override and is expected to clear it on close (the wrapper also clears it as a safety net).

## Notes on Legacy (barcode_managerOLD)

The legacy code path (see `Documentation/barcode_managerOLD.md` / `POS temp/barcode_managerOLD.py`) is **not safe to restore** as-is.

Key issues:

- **Brittle modal typing allow-list:** it relied on a hardcoded list of widget names to permit typing during modal block. New dialogs could break unexpectedly unless manually added.
- **Incorrect/unfinished “found” logic:** the legacy `on_barcode_scanned()` referenced `found` without ensuring it was computed, making “product not found → open product menu” unreliable.
- **Weaker convention support:** it did not consistently support the newer `*ProductCodeLineEdit` naming convention in the scan-burst allow-list.

The current implementation replaces the brittle allow-list approach with “allow typing inside the active modal dialog; block leaks to the main window” and uses naming conventions for product-code fields.

## Recommended Conventions

- Any dialog that should accept barcode scans in a product code field should name that field with `objectName` ending in `ProductCodeLineEdit`.
- Keep scanner usage inside modals either:
  - override-based (Product Menu), or
  - blocked entirely (most dialogs)

If you want a third mode (“blocked modal, but allow scans directly into focused `*ProductCodeLineEdit` without overrides”), implement it explicitly in `on_barcode_scanned()` rather than reverting to the legacy manager.
