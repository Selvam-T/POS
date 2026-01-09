# Error Logging and Fallback Dialogs in POS System

## Overview
This document describes the error logging mechanism and fallback dialog strategy implemented in the POS system, specifically for dialogs such as Cancel Sale.

## Error Logging
- All critical dialog/UI errors (such as missing .ui files) are logged to `log/error.log` in the project root.
- Logging is performed via a shared function `log_error(msg)` in `modules/ui_utils/error_logger.py`.
- Each log entry includes an ISO 8601 timestamp for traceability.
- Example log entry:
  ```
  2026-01-09T14:23:45.123456 - Failed to load cancel_sale.ui, using fallback dialog.
  ```

## Fallback Dialogs
- If a dialog's .ui file cannot be loaded, a minimal fallback dialog is shown to the user.
- The fallback dialog always provides clear messaging and actionable buttons, ensuring a clean user experience even in error states.
- For Cancel Sale, the fallback dialog includes:
  - A confirmation message
  - Two styled buttons: Cancel (red) and Yes, Clear All (green)
- Minimal button styling is applied directly in code to ensure visibility regardless of QSS.
- Statusbar notification is shown using `show_main_status()` to inform the user that a fallback dialog was loaded.

## Implementation Details
- Shared error logger: `modules/ui_utils/error_logger.py`
- Fallback dialog logic: see `modules/sales/cancel_sale.py` (inside `open_cancel_sale_dialog`)
- Statusbar feedback: see `modules/ui_utils/ui_feedback.py` (`show_main_status`)

## Rationale
- Ensures robust, user-friendly error handling for all dialogs.
- Centralizes error logging for easier debugging and support.
- Maintains consistent UI/UX even when assets are missing or corrupted.

## See Also
- `Documentation/cancel_all_functionality.md` for Cancel Sale dialog workflow
- `README.md` for general error handling and fallback notes
- `Project_Journal.md` for development history and rationale

---
*Last updated: January 9, 2026*
