# Login Dialog Controller Documentation

## Overview
The login dialog is the first UI shown on application startup. It blocks access to the main window until login is successful.

## Implementation
- UI file: `ui/login.ui`
- Controller: `modules/sales/login.py`
- Controls: `loginComboBox` (username), `loginPassLineEdit` (password), `loginStatusLabel` (status/error), optional `customCloseBtn` for the frameless titlebar
- Submit flow: there is no `OK` button. Pressing Enter while focused on the password field triggers validation; on success the dialog returns Accepted and the main window launches. On failure the dialog remains open, the error is shown in `loginStatusLabel`, and the password text is selected for easy correction.
- Cancel/close: if present, `customCloseBtn` or window reject closes the dialog (Rejected).

Forced-change UX notes:
- When the Admin dialog is opened in forced-change mode, the dialog disables tab switching, disables Cancel and title-bar Close, and prevents programmatic `reject()` so the user cannot dismiss the dialog without successfully updating the password. On successful update the Admin controller clears the `must_change_password` flag in the DB.
- The `staff` user (`uid == 2`) remains excluded from forced-change; the "Forgot" flow for staff continues to instruct users to contact admin and does not set the flag.

## Entry Point Logic
- In `main.py`, the login dialog is launched before the main window.
- Only if login is successful, the main window is shown.

Forced password-change integration:
- The login "Forgot" flow for the admin (`uid == 1`) now not only generates a temporary password (via `generate_temporary_password_for_user`) but also sets a persistent `must_change_password` flag in the users table using `users_repo.set_must_change_password(uid, True)`. This ensures the admin will be required to change the temporary password on next login.
- After successful login, `main.py` checks `users_repo.get_must_change_password(current_user_id)` and — when set for an admin — opens the Admin dialog in forced-change mode. The forced dialog is opened via the app's `DialogWrapper` but its creation is deferred using `QTimer.singleShot(...)` so the main window has time to finish maximize/resize. This ensures `DialogWrapper` applies `config.DIALOG_RATIOS` against the final main-window geometry and prevents the dialog from sizing too small.

## UI/UX details
- Focus: the password field receives initial focus when the dialog opens.
- Validation: validation is performed only when Enter is pressed (or programmatically) — the dialog does not validate on every keystroke.
- Error styling: `loginStatusLabel` uses the project's QSS rules (`QLabel[status="error"]` / `QLabel[status="success"]`). The controller uses `modules.ui_utils.ui_feedback` to set/clear the label so QSS state is applied.

### Recent behavior and implementation notes

- Validation split:
	- `modules/ui_utils/input_validation.py` exposes `validate_username_password_input(username, password)` used by the dialog; for the login path this function only enforces presence (non-empty) of the password and username. Strong password rules remain available for create/change workflows.
	- `modules/db_operation/users_repo.py` exposes `authenticate_user(username, password)` which performs DB lookup and password-hash comparison and returns a normalized DB view (or `None`).
	- `modules/db_operation/users_repo.py` also exposes `build_authenticated_user(user, fallback_uid=None)` which centralizes normalization (computes `user_id`, `username`, and `is_admin`). The dialog still provides the UI-only fallback `current_user_id()` when the DB record lacks a `user_id`.

- Controller responsibilities (kept in `modules/sales/login.py`):
	- Call the input validator, call `authenticate_user(...)`, call `build_authenticated_user(...)` and keep UI-only behavior such as `clear_status()`, `set_error()`, `focus_password()`, and retrieving the `current_user_id()` from the combo widget.

- Dialog sizing:
	- Dialog ratios are configurable in `config.DIALOG_RATIOS` (e.g. `'login': (0.45, 0.9)`). The ratio should be applied immediately after `uic.loadUi(...)` so it overrides the .ui geometry.
	- When the login dialog is shown before the main window (no parent), use the primary screen's available geometry as the base for computing the ratio; when a parent exists prefer the parent window size.

	Example (call immediately after `uic.loadUi` in the launcher):

	```python
	dlg = uic.loadUi(UI_PATH, parent)
	# apply_dialog_ratio will prefer `parent` size when available,
	# otherwise it falls back to the primary screen geometry
	from modules.ui_utils.dialog_utils import apply_dialog_ratio
	apply_dialog_ratio(dlg, 'login', parent=parent)
	dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
	```

- Placeholder styling:
	- The placeholder text itself is defined in `ui/login.ui` (property `placeholderText` on `loginPassLineEdit`). Visual styling for the widget is in `assets/main.qss` under the `LOGIN DIALOG` section which styles `QLineEdit#loginPassLineEdit` (font, padding, color) and password echo.
	- Some Qt versions/stylesheets may not support the `::placeholder` pseudo-element. The dialog code includes a small palette fallback which sets the placeholder color via the widget `QPalette` so the placeholder appears in light gray even when `::placeholder` is unavailable.

## Notes
- The controller disables default/auto-default button behavior and intercepts Enter at the dialog level so the default-button acceptance cannot close the dialog before validation runs.
- The implementation intentionally avoids `FieldCoordinator` for this simple flow and handles validation directly in `modules/sales/login.py`.

- Password recovery policy: the UI no longer uses `recovery_email` for admin/staff.
	- `uid == 1` (admin): clicking the "forgot" button generates a temporary
		password (via `modules/db_operation/users_repo.generate_temporary_password_for_user`)
		and copies it to the clipboard for manual delivery.
	- `uid == 2` (staff): clicking the "forgot" button displays the message
		"Please contact admin to login." and does not generate a password.
	- The `get_recovery_email` function remains in `modules/db_operation/users_repo.py`
		for future recovery-email based flows but is not used by the current UI.

## Future Updates
This file will be updated as login controller implementation advances (validation, user management, etc.)

- Changelog (recent):
	- Extracted light-weight login input validation into `input_validation.validate_username_password_input` (presence checks only).
	- Centralized authentication and normalization in `users_repo.authenticate_user` and `users_repo.build_authenticated_user`.
	- Dialog sizing via `config.DIALOG_RATIOS` applied at dialog-creation time; fallback to screen geometry when no parent exists.
	- Placeholder color fallback implemented via `QPalette` in the dialog controller to ensure consistent placeholder appearance.
