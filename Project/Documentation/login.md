# Login Dialog Controller Documentation

## Overview
The login dialog is the first UI shown on application startup. It blocks access to the main window until login is successful.

## Implementation
- UI file: `ui/login.ui`
- Controller: `modules/sales/login.py`
- Controls: `loginComboBox` (username), `loginPassLineEdit` (password), `loginStatusLabel` (status/error), optional `customCloseBtn` for the frameless titlebar
- Submit flow: there is no `OK` button. Pressing Enter while focused on the password field triggers validation; on success the dialog returns Accepted and the main window launches. On failure the dialog remains open, the error is shown in `loginStatusLabel`, and the password text is selected for easy correction.
- Cancel/close: if present, `customCloseBtn` or window reject closes the dialog (Rejected).

## Entry Point Logic
- In `main.py`, the login dialog is launched before the main window.
- Only if login is successful, the main window is shown.

## UI/UX details
- Focus: the password field receives initial focus when the dialog opens.
- Validation: validation is performed only when Enter is pressed (or programmatically) — the dialog does not validate on every keystroke.
- Error styling: `loginStatusLabel` uses the project's QSS rules (`QLabel[status="error"]` / `QLabel[status="success"]`). The controller uses `modules.ui_utils.ui_feedback` to set/clear the label so QSS state is applied.

## Notes
- The controller disables default/auto-default button behavior and intercepts Enter at the dialog level so the default-button acceptance cannot close the dialog before validation runs.
- The implementation intentionally avoids `FieldCoordinator` for this simple flow and handles validation directly in `modules/sales/login.py`.

## Future Updates
This file will be updated as login controller implementation advances (validation, user management, etc.)
