# Admin Menu Dialog

This document captures the current wiring and behavior for the Admin Menu dialog. Update this file as additional tabs are implemented.

## Files

- UI: [ui/admin_menu.ui](ui/admin_menu.ui)
- Controller: [modules/menu/admin_menu.py](modules/menu/admin_menu.py)
- QSS: [assets/dialog.qss](assets/dialog.qss)

## Purpose

Provide a modal, frameless Admin Menu dialog that allows:
- ADMIN password change
- STAFF password change
- Additional tabs to be wired later (document here as they are implemented)

When `must_change_password` is set for the admin account, the Admin Menu enforces a forced password change (details below).

## Current Wiring (Controller)

### Dialog Creation
- The dialog is created via `build_dialog_from_ui(...)` with `dialog.qss` applied.
- A fallback dialog is shown if the UI file fails to load.

### Required Widgets
The controller resolves and hard-fails on missing widgets, including:
- `QTabWidget#tabWidget`
- ADMIN: `adminCurPwdLineEdit`, `adminNewPwdLineEdit`, `btnAdminOk`, `btnAdminCancel`, `adminStatusLabel`, `adminToolBtn`
- STAFF: `staffCurPwdLineEdit`, `staffNewPwdLineEdit`, `btnStaffOk`, `btnStaffCancel`, `staffStatusLabel`, `staffQToolBtn`
- Title bar: `customCloseBtn`

### Title Bar
- The title bar close button calls `dlg.reject()`.
- Title alignment is left to the `.ui` layout (no runtime alignment override).

### Password Visibility
- Eye tool buttons toggle password visibility by switching `QLineEdit` echo mode.

### Shared Password Flow (ADMIN + STAFF)
Both tabs use the same shared logic via a neutral helper:
- Gate the new password field and OK button until the current password validates.
- Validate the current password using `verify_password(user_id, input)`.
- Validate the new password with `input_handler.handle_password_input(...)`.
- On OK, update with `update_password(user_id, new_pwd)`.
- Show a post-close status message on success or error.

### Forced Password Change (Admin)
When the admin account has `must_change_password = 1`:
- The dialog must open on the ADMIN tab.
- The user is blocked from switching tabs or closing the dialog until a successful admin password change.
- Cancel and title-bar close should show an error message and keep the dialog open.
- On success, the controller resets `must_change_password` to `0` in the users table.

### Fixed User Ids (Documented Invariant)
The password change targets are fixed by user id:
- ADMIN user id = 1
- STAFF user id = 2

The controller still honors an explicit `user_id` argument for ADMIN if the caller provides it; otherwise it uses the fixed id.

### Focus and Validation Behavior
- Uses `FieldCoordinator` to register validators and auto-jump on ENTER.
- Uses `FocusGate` to lock/unlock fields and hide/restore placeholders.
- Initial focus is set to `adminCurPwdLineEdit` on open.

## Known Limits / Assumptions

- ADMIN/STAFF ids are fixed in the database seed. If these change, update constants in the controller.
- Other tabs (e.g., Screen 2 Ads) are not documented here yet.

## Update Checklist (When Adding New Tab)

- Add widget names to required list (fail fast if UI changes).
- Implement a shared controller helper if the tab mirrors existing behavior.
- Add validation rules using `FieldCoordinator`.
- Update this document with UI + behavior details.

## Notes

If [Documentation/admin_settings.md](Documentation/admin_settings.md) conflicts with this file, treat this file as the current source of truth.
