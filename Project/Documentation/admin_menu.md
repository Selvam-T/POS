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
- ADMIN: `adminCurPwdLineEdit`, `adminNewPwdLineEdit`, `btnAdminOk`, `btnAdminCancel`, `adminStatusLabel`, `adminToolBtn`, `adminToolBtn2`
- STAFF: `staffCurPwdLineEdit`, `staffNewPwdLineEdit`, `btnStaffOk`, `btnStaffCancel`, `staffStatusLabel`, `staffToolBtn`, `staffToolBtn2`
- Screen 2 Ads: `screen2ListWidget`, `screen2PreviewLabel`, `screen2CountLabel`, `screen2StatusLabel`, `addScreen2Btn`, `removeScreen2Btn`, `upScreen2Btn`, `downScreen2Btn`
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

Implementation note:
- The shared helper is implemented in `modules/menu/admin_menu.py` as a neutral `_setup_password_tab(...)` function which is invoked for both ADMIN and STAFF tabs. This consolidates validation, FocusGate behavior and the call to `update_password()` so maintenance and UX rules remain consistent.

### Forced Password Change (Admin)
When the admin account has `must_change_password = 1`:
- The dialog must open on the ADMIN tab.
- The user is blocked from switching tabs or closing the dialog until a successful admin password change.
- Cancel and title-bar close should show an error message and keep the dialog open.
- On success, the controller resets `must_change_password` to `0` in the users table.

Behavioral details / implementation notes:
- The persistent flag is stored in the `users.must_change_password` INTEGER column and manipulated via helpers in `modules/db_operation/users_repo.py` (`set_must_change_password`, `get_must_change_password`, `clear_must_change_password`).
- When the app launches and detects the flag for the logged-in admin, `main.py` opens the Admin dialog in forced-change mode using the normal `DialogWrapper` flow. To ensure dialog sizing is computed against the final main-window geometry, the forced dialog open is deferred with `QTimer.singleShot(...)` so the main window can finish maximize/resize operations before the dialog applies `config.DIALOG_RATIOS`.
- While `force_change=True`, the controller disables other tabs, disables Cancel and the custom Close button, and prevents `dlg.reject()` from closing the dialog. The DB flag is cleared only after a successful password update.

### Fixed User Ids (Documented Invariant)
The password change targets are fixed by user id:
- ADMIN user id = 1
- STAFF user id = 2

The controller still honors an explicit `user_id` argument for ADMIN if the caller provides it; otherwise it uses the fixed id.

### Focus and Validation Behavior
- Uses `FieldCoordinator` to register validators and auto-jump on ENTER.
- Uses `FocusGate` to lock/unlock fields and hide/restore placeholders.
- Initial focus is set to `adminCurPwdLineEdit` on open.

## Screen 2 Ads Tab

Screen 2 Ads is wired via a dedicated helper so it remains independent from Admin/Staff password logic.

Helper module:
- [modules/menu/screen2_ads_helper.py](modules/menu/screen2_ads_helper.py)

Storage model:
- Folder: `assets/ads`
- Files are named with numeric prefixes (e.g., `1_image.jpg`, `2_image.jpg`)
- Order is determined by numeric prefix and persisted by renaming files

Behavior summary:
- Add images via file picker; accepted formats: JPG, JPEG, PNG
- Validation: resolution must be exactly 1280x800 (16:10)
- Limit: max 6 images
- Thumbnails are generated in memory and shown in the list
- Preview is displayed in `screen2PreviewLabel`
- Reorder uses Up/Down and persists by renumbering files
- Remove deletes the selected image and renumbers remaining files

Gating rules:
- Add is disabled when the limit is reached
- Remove is disabled unless an item is selected
- Up is disabled on the first item or if nothing is selected
- Down is disabled on the last item or if nothing is selected

Status messaging:
- Errors and success messages are routed through `screen2StatusLabel` via `ui_feedback.set_status_label(...)`
- Clearing status uses `ui_feedback.clear_status_label(...)`

## EXPORT Tab

The EXPORT tab allows exporting the application's `Product_list` table in three formats:

- CSV (`.csv`) — simple comma-separated values file.
- XLSX (`.xlsx`) — Excel workbook (requires the `openpyxl` package).
- SQL (`.sql`) — SQL file containing the `CREATE TABLE` statement and `INSERT` statements for every row.

Behaviour and wiring:
- Buttons wired in controller: `csvExportBtn`, `xlsxExportBtn`, `sqlExportBtn` (see `modules/menu/admin_menu.py`).
- Exports are written to the user Documents folder under `Documents/POS_Exports`.
- Filenames follow the pattern: `product_list_{kind}_ddmmmyyyy_hh-mm.ext` (timestamp uses `ddMmmYYYY_HH-MM` with `:` replaced by `-` for Windows-safe filenames).
- After a successful export the UI shows a concise status message in `exportStatusLabel` of the form: `"<FILETYPE> file exported to <full-path>"` (e.g. `CSV file exported to C:/Users/.../Documents/POS_Exports/product_list_csv_03apr2026_21-30.csv`).

Notes:
- The XLSX export uses `openpyxl`. If `openpyxl` is not installed the controller will report an error and the XLSX export will fail; install via `pip install openpyxl` or include it in your environment requirements. The project `requirements.txt` already lists `openpyxl>=3.1`.
- Exports are generated from a `SELECT * FROM Product_list ORDER BY name COLLATE NOCASE` query; ensure the `Product_list` table exists and the DB path is correct.

## Known Limits / Assumptions

- ADMIN/STAFF ids are fixed in the database seed. If these change, update constants in the controller.
- Screen 2 Ads uses file-system persistence in `assets/ads`. Ensure this folder is accessible to the app user.

Security note:
- The forced-change flow is only applied for the ADMIN account (user id 1). The `staff` account intentionally does not participate in forced password changes and the application will ignore `must_change_password` for staff (remains 0).

## Update Checklist (When Adding New Tab)

- Add widget names to required list (fail fast if UI changes).
- Implement a shared controller helper if the tab mirrors existing behavior.
- Add validation rules using `FieldCoordinator`.
- Update this document with UI + behavior details.

## Notes

If [Documentation/admin_settings.md](Documentation/admin_settings.md) conflicts with this file, treat this file as the current source of truth.
