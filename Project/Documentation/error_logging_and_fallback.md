# Error Logging and Fallback Dialogs in POS System

## Overview
This document describes the error logging mechanism and fallback dialog strategy implemented in the POS system.

The current architecture has two complementary layers:
- **Dialog Construction Layer** (per-dialog modules): loads UI, wires widgets, validation, and focus.
- **Dialog Execution Layer** (`DialogWrapper`): overlay/scanner, geometry, focus restore, and post-close messages.

## Error Logging
- All critical dialog/UI errors (such as missing `.ui` files, failed UI load, unexpected exceptions) are logged to `log/error.log`.
- Logging is performed via `log_error(msg)` in `modules/ui_utils/error_logger.py`.
- Each log entry includes an ISO 8601 timestamp for traceability.
- Example log entry:
  ```
  2026-01-09T14:23:45.123456 - Failed to load cancel_sale.ui, using fallback dialog.
  ```

## Fallback Dialogs
Fallback behavior is dialog-specific. Some dialogs show an explicit fallback dialog; others choose to abort opening and show a StatusBar message.

### Standardized UI-load fallback
For menu-style dialogs, `modules/ui_utils/dialog_utils.py` provides `load_ui_strict(...)`:
- Missing `.ui` or load failure → logs to `error.log`
- Best-effort StatusBar message via `report_to_statusbar(...)`
- Returns `None` so the caller can **hard-fail** (return `None`) or **soft-disable** a feature.

### Post-close StatusBar messages
Dialogs can set a post-close message using:
- `set_dialog_info(dlg, message)` (non-error)
- `set_dialog_error(dlg, message)` (error)

`DialogWrapper` reads these attributes after `dlg.exec_()` and displays them in the MainWindow StatusBar.

## Implementation Details
Core modules:
- `modules/ui_utils/error_logger.py` — `log_error(...)`
- `modules/ui_utils/dialog_utils.py` — `load_ui_strict(...)`, `report_exception(...)`, `set_dialog_info(...)`
- `modules/wrappers/dialog_wrapper.py` — dialog lifecycle, overlay/scanner, focus restore, post-close StatusBar messages
- `modules/ui_utils/ui_feedback.py` — StatusBar and label feedback helpers

Opt-in module:
- `modules/ui_utils/error_policy.py` — `safe_call(...)` and `should_log(...)` for incremental centralization of error routing.

## Rationale
- Ensures robust, user-friendly error handling for all dialogs.
- Centralizes error logging for easier debugging and support.
- Maintains consistent UI/UX even when assets are missing or corrupted.

## See Also
- `Documentation/cancel_all_functionality.md` for Cancel Sale dialog workflow
- `README.md` for general error handling and fallback notes
- `Project_Journal.md` for development history and rationale

---
*Last updated: January 17, 2026*
