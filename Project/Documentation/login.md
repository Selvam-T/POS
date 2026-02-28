# Login Dialog Controller Documentation

## Overview
The login dialog is the first UI shown on application startup. It blocks access to the main window until login is successful.

## Implementation
- UI file: `ui/login.ui`
- Controller: `modules/sales/login.py`
- Button naming: `btnLoginOk` (OK), `btnLoginCancel` (Cancel)
- On OK: dialog returns Accepted, main window launches
- On Cancel: dialog returns Rejected, application exits

## Entry Point Logic
- In `main.py`, the login dialog is launched before the main window.
- Only if login is successful, the main window is shown.

## Future Updates
This file will be updated as login controller implementation advances (validation, user management, etc.)
