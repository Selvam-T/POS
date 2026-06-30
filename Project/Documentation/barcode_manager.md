# BarcodeManager - Current Behavior

This document describes the current behavior of `BarcodeManager` in `modules/devices/barcode_manager.py`.

## Purpose

`BarcodeManager` centralizes scanner behavior:

- Routes scanned barcodes to the sales table or dialog-owned product-code fields.
- Cleans scan leaks via snapshot restore, with single-character cleanup as fallback.
- Blocks scanner-driven main-window actions while modal dialogs are open.
- Suppresses Enter/Return during scanner bursts to avoid unintended button clicks.

## Core Concepts

### 1) Modal Block

`_modalBlockScanner` is enabled by `DialogWrapper.open_dialog_scanner_blocked(...)` while most dialogs are open.

- Confirmed scans are prevented from reaching main-window routing.
- Keystrokes inside the active modal are allowed so normal typing still works.
- Keystrokes outside the active modal are blocked as a fail-safe.

### 2) Barcode Override

Dialogs that own scans temporarily expose `dlg.barcode_override_handler`; `DialogWrapper` installs it through `set_barcode_override(...)` and clears it on cleanup.

Override routing is checked first in `on_barcode_scanned()`.

Current rule:

- The override may consume a scan when focus is in a widget whose `objectName` ends with `ProductCodeLineEdit`.
- If focus shifts mid-scan, the override may still consume it if the scan started in a `*ProductCodeLineEdit`.
- Otherwise the scan is rejected, leaked text is restored/cleaned, and the dialog may show "Scan only in Product Code field".

### 3) HOLD_LOADED Cart Protection

When `receipt_context.source == 'HOLD_LOADED'`, scanner-driven sales-table routing is blocked.

This check happens after dialog override routing, so product-code dialogs can still accept scans when focused correctly.

### 4) Default Routing

If no override consumes the scan:

- `_modalBlockScanner`: ignore scan + restore/cleanup leak.
- `receipt_context.source == 'HOLD_LOADED'`: ignore scan + restore/cleanup leak.
- Focus on `qtyInput`: ignore scan + restore/cleanup leak.
- Otherwise: treat as a sales-table barcode.
  - Product found: add to sales table.
  - Product not found: open Product Menu in ADD mode with `initial_code`.

## Scan-Burst Timing

![Barcode scanner high-speed input workflow](Barcode_Manager_High-Speed_Manual_Input.png)

The diagram's `confirmation.py` box is conceptual; the confirmed `barcode_scanned` signal is emitted by `modules/devices/scanner.py`.

`scanner.py` owns scanner/manual timing. It uses `SCANNER_KEY_INTERVAL_SECONDS` and emits:

```python
scanner_activity(timestamp, is_fast)
```

`BarcodeManager` consumes `is_fast`; it no longer re-checks a separate interval.

During scanner-fast activity, `BarcodeManager`:

- Snapshots the focused editable widget at the start of a possible burst.
- Suppresses Enter/Return for `SCANNER_UI_SUPPRESS_SECONDS`.
- Does not block printable characters solely because typing is fast.

This keeps the scanner's trailing Enter from submitting forms while avoiding the old fast-manual-typing freeze in normal text fields.

## Leak Cleanup

When a confirmed scan is rejected or ignored, `BarcodeManager` first restores the editable widget text captured at scan-burst start.

If no snapshot is available, `_cleanup_scanner_leak(...)` removes the trailing first character of the scanned barcode when present. This fallback is length-independent and still works when a field already contains text.

## Integration Points

- `main.py` creates `BarcodeManager` and installs it as an app event filter.
- `DialogWrapper.open_dialog_scanner_blocked(...)` toggles modal block and clears overrides on close.
- Dialogs that accept scans should name product-code fields with an `objectName` ending in `ProductCodeLineEdit`.

## Notes On Legacy

Do not restore the old manager from `Documentation/barcode_managerOLD.md` / `POS temp/barcode_managerOLD.py`.

Known legacy issues:

- Brittle modal typing allow-list.
- Incomplete product-found routing.
- Weaker support for the `*ProductCodeLineEdit` convention.
