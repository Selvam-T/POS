# Admin Settings Dialog (Admin, Staff, Email)

This document describes the Admin Settings dialog, its UI structure, access rules, and how it integrates with the right-side menu.

## Overview

- Purpose: Provide a central place to manage passwords for Admin and Staff, and to configure the recovery email address.
- Access: Only the Admin user can open the Admin Settings dialog (Staff has no access via the menu button in production).
- UX pattern: Frameless dialog with a custom title bar (consistent with other menu dialogs), dimmed background while open, and centered on the main window.

## Files

- UI: `ui/admin_menu.ui`
  - Root: `QDialog#AdminDialog`
  - Custom title bar: `QFrame#customTitleBar` with `QLabel#customTitle` and `QPushButton#customCloseBtn`
  - Logged-in indicator: `QLabel#loggedInLabel` (e.g., "Logged in as: Admin")
  - Tabs: `QTabWidget#tabWidget` with three pages
    - Admin tab: `QWidget#tabAdmin`
    - Staff tab: `QWidget#tabStaff`
    - Email tab: `QWidget#tabEmail`
  - Footer info: `QLabel#infoLabel` (e.g., "Only Admin can modify settings")
  - Footer action: `QPushButton#closeButton` (closes dialog)
- Controller: `modules/menu/admin_menu.py`
  - Entry point: `open_admin_dialog(host_window, current_user='Admin', is_admin=True)`
  - Loads the .ui, applies frameless flags, centers the dialog, wires buttons, and toggles password field visibility.
- Wiring: `main.py`
  - The right-side menu button `adminBtn` calls `open_admin_dialog(self, current_user='Admin', is_admin=True)`.

## UI Details

### Admin Tab
- Group: `QGroupBox#groupAdminPassword` (title: "Change Admin Password")
- Fields:
  - `QLineEdit#adminCurrentPassword` (masked; placeholder `********`)
  - `QToolButton#btnToggleAdminCurrent` (checkable eye icon to show/hide)
  - `QLineEdit#adminNewPassword` (masked; placeholder "Enter new password")
- Action:
  - `QPushButton#btnAdminSave` (Save Changes)

### Staff Tab
- Group: `QGroupBox#groupStaffPassword` (title: "Change Staff Password")
- Fields:
  - `QLineEdit#staffCurrentPassword` (masked; placeholder `********`)
  - `QToolButton#btnToggleStaffCurrent` (checkable eye icon)
  - `QLineEdit#staffNewPassword` (masked; placeholder "Enter new password")
- Action:
  - `QPushButton#btnStaffSave` (Save Changes)

### Email Tab
- Group: `QGroupBox#groupEmail` (title: "Email Settings")
- Fields:
  - `QLineEdit#currentEmailLineEdit` (read-only; shows current recovery email)
  - `QLineEdit#newEmailLineEdit` (editable; enter new recovery email)
- Action:
  - `QPushButton#btnEmailSave` (Save Changes)

### Close Controls
- Title bar close: `QPushButton#customCloseBtn` (×)
- Bottom close: `QPushButton#closeButton` (CLOSE)

## Behavior (Controller)

- The dialog is opened modally and frameless; background is dimmed using the main window helper.
- `loggedInLabel` shows the current user (e.g., Admin/Staff) passed in from the caller.
- `is_admin` flag controls editability:
  - `True`: All change controls enabled (default).
  - `False`: Read-only presentation (Staff cannot modify settings); Save buttons disabled.
- Eye buttons (`btnToggleAdminCurrent`, `btnToggleStaffCurrent`) toggle the echo mode between Password and Normal for their paired fields.
- Save buttons are stubs for now (print to console). Real persistence can be implemented later (e.g., secure hash in AppData).

## QSS Hooks

Define shared dialog styles in `assets/menu.qss` to keep a consistent look with other menu dialogs. Common selectors:

```css
/* Title bar */
QFrame#customTitleBar { /* background-color, padding, border, etc. */ }
QPushButton#customCloseBtn { /* color, size, hover/pressed */ }

/* Primary action */
QPushButton#btnAdminSave,
QPushButton#btnStaffSave,
QPushButton#btnEmailSave { /* shared size, color, radius */ }

/* Inputs and groups */
QGroupBox { /* title color, margins */ }
QLineEdit { /* base input style */ }
```

You can also scope rules using the container object name:

```css
QDialog#AdminDialog { /* dialog background, padding */ }
```

## Access Control Notes

- The right-side menu should only enable the Admin button for the Admin user. In development, we pass `is_admin=True` by default.
- In production, determine the logged-in role and call:
  - Admin: `open_admin_dialog(self, current_user='Admin', is_admin=True)`
  - Staff: Either hide/disable the Admin button, or call `open_admin_dialog(self, current_user='Staff', is_admin=False)` to show a read-only view.

## Integration Checklist

- [x] UI file `ui/admin_menu.ui`
- [x] Controller `modules/menu/admin_menu.py`
- [x] Menu button wiring in `main.py` (`adminBtn` → opens dialog)
- [ ] QSS polish for Admin/Staff/Email tabs and primary save button (pending)
- [ ] Persistence layer for passwords and recovery email (pending)

## Future Work

- Implement secure password storage (hash + salt) in AppData.
- Add email format validation and persistence for `currentEmailLineEdit`.
- Add feedback labels (success/error) near each Save button.
- Optional: migrate to `BaseMenuDialog` shell to reuse the shared title bar and spacing from `ui/base_menu_dialog.ui`.
