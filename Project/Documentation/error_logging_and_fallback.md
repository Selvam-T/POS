# Error Logging and Fallback Dialogs in POS System

## Overview
This document describes the error logging mechanism and fallback dialog strategy implemented in the POS system.

The current architecture has two complementary layers:
- **Dialog Construction Layer** (per-dialog modules): loads UI, wires widgets, validation, and focus.
- **Dialog Execution Layer** (`DialogWrapper`): overlay/scanner, geometry, focus restore, and post-close messages.

This doc also defines the shared terminology used across dialogs:

- **Hard-fail**: an unexpected exception crosses a boundary (usually a bug or corrupted UI state). The wrapper catches it, cleans up overlay/scanner, logs it, and shows a short StatusBar hint.
- **Soft-fail**: an expected/handled failure (validation error, DB CRUD returns `(ok=False, msg)`, non-critical cache refresh failure). The dialog stays responsive; feedback is shown locally (status label) and optionally queued for post-close StatusBar.
- **Soft-disable**: the dialog opens but a non-essential feature is disabled (e.g., completer list not available). This is a subtype of soft-fail.

## Error Logging
- All critical dialog/UI errors (such as missing `.ui` files, failed UI load, unexpected exceptions) are logged to `log/error.log`.
- Logging is performed via `log_error(msg)` in `modules/ui_utils/error_logger.py`.
- Each log entry includes an ISO 8601 timestamp for traceability.
- Example log entry:
  ```
  2026-01-09T14:23:45.123456 - Failed to load clear_cart.ui, using fallback dialog.
  ```

## Fallback Dialogs
Fallback behavior is dialog-specific. Some dialogs show an explicit fallback dialog; others choose to abort opening and show a StatusBar message.

### Standardized UI-load fallback
For menu-style dialogs, `modules/ui_utils/dialog_utils.py` provides `load_ui_strict(...)`:
- Missing `.ui` or load failure → logs to `error.log`
- Best-effort StatusBar message (deferred and flushed by `DialogWrapper`)
- Returns `None` so the caller can **hard-fail** (return `None`) or **soft-disable** a feature.

Note: UI-load failures can still occur during an “open dialog” flow while the overlay is enabled.
To avoid StatusBar messages being hidden under the modal overlay, UI-load notifications are queued and displayed by `DialogWrapper` after cleanup.

### Post-close StatusBar messages
Dialogs can set a post-close message using:
- `set_dialog_info(dlg, message)` (non-error)
- `set_dialog_error(dlg, message)` (error)

`DialogWrapper` reads these attributes after `dlg.exec_()` and displays them in the MainWindow StatusBar.

## StatusBar policy for modal dialogs

While a modal dialog is open, the overlay is active and the StatusBar is visually “behind” the modal.
To avoid confusing UX:

- Prefer **post-close** StatusBar messages (set intent on the dialog; wrapper displays it after close).
- Avoid calling `report_to_statusbar(...)` from inside modal dialog event handlers.

### Severity precedence (important)

When a dialog sets multiple messages during a single run (e.g., DB success and later refresh warning), use:

- **failure/warning takes precedence over success in the StatusBar**

In code, this is done via `set_dialog_main_status_max(...)`.

Example rule:
- DB success → show success in dialog-local status label
- Cache/completer refresh failure after DB success → show warning in StatusBar (post-close)

## Implementation Details
Core modules:
- `modules/ui_utils/error_logger.py` — `log_error(...)`
- `modules/ui_utils/dialog_utils.py` — `load_ui_strict(...)`, `report_exception(...)` (immediate), `report_exception_post_close(...)` (post-close), `set_dialog_main_status_max(...)`
- `modules/wrappers/dialog_wrapper.py` — dialog lifecycle, overlay/scanner, focus restore, post-close StatusBar messages, and hard-fail StatusBar hint after cleanup
- `modules/ui_utils/ui_feedback.py` — StatusBar and label feedback helpers

Opt-in module:
- `modules/ui_utils/error_policy.py` — `safe_call(...)` and `should_log(...)` for incremental centralization of error routing.

## Rationale
- Ensures robust, user-friendly error handling for all dialogs.
- Centralizes error logging for easier debugging and support.
- Maintains consistent UI/UX even when assets are missing or corrupted.

## See Also
- `Documentation/cancel_all_functionality.md` for Clear Cart dialog workflow
- `README.md` for general error handling and fallback notes
- `Project_Journal.md` for development history and rationale

---
*Last updated: January 22, 2026*
