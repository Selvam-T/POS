import os
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QWidget, QPushButton, QLineEdit, QToolButton, QLabel, QTabWidget
from modules.ui_utils.error_logger import log_error
from modules.ui_utils.dialog_utils import build_dialog_from_ui, require_widgets, set_dialog_error, set_dialog_info, report_exception_post_close, build_error_fallback_dialog
from modules.ui_utils.focus_utils import FieldCoordinator, FocusGate, set_initial_focus
from modules.ui_utils import input_handler
from modules.db_operation.users_repo import verify_password, update_password
from modules.ui_utils import ui_feedback

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(THIS_DIR))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
QSS_PATH = os.path.join(ASSETS_DIR, 'dialog.qss')


# Build and return the admin settings dialog.
def launch_admin_dialog(host_window, user_id: int | None = None, is_admin: bool = True):
    """Open the Admin Settings dialog.

    Args:
        host_window: Main window instance.
        user_id: Logged-in user id for password verification and update.
        is_admin: If False, dialog is read-only.

    Returns:
        QDialog instance.
    """
    # Use shared dialog builder for consistent behavior
    ui_path = os.path.join(UI_DIR, 'admin_menu.ui')
    dlg = build_dialog_from_ui(ui_path, host_window=host_window, dialog_name='admin_menu', qss_path=QSS_PATH)
    if dlg is None:
        return build_error_fallback_dialog(host_window, 'Admin Settings', QSS_PATH)

    # Resolve required widgets (hard-fail if UI changed)
    try:
        widgets = require_widgets(dlg, {
            'tabWidget': (QTabWidget, 'tabWidget'),
            'adminCur': (QLineEdit, 'adminCurPwdLineEdit'),
            'adminNew': (QLineEdit, 'adminNewPwdLineEdit'),
            'adminEye': (QToolButton, 'adminToolBtn'),
            'adminStatus': (QLabel, 'adminStatusLabel'),
            'btnAdminOk': (QPushButton, 'btnAdminOk'),
            'btnAdminCancel': (QPushButton, 'btnAdminCancel'),
            'staffCur': (QLineEdit, 'staffCurPwdLineEdit'),
            'staffNew': (QLineEdit, 'staffNewPwdLineEdit'),
            'staffEye': (QToolButton, 'staffQToolBtn'),
            'staffStatus': (QLabel, 'staffStatusLabel'),
            'btnStaffOk': (QPushButton, 'btnStaffOk'),
            'btnStaffCancel': (QPushButton, 'btnStaffCancel'),
            'customClose': (QPushButton, 'customCloseBtn'),
        }, hard_fail=True)
    except Exception as e:
        try:
            log_error(f"admin_menu: require_widgets failed: {e}")
        except Exception:
            pass
        return dlg

    tabWidget = widgets['tabWidget']
    adminCur = widgets['adminCur']
    adminNew = widgets['adminNew']
    adminEye = widgets['adminEye']
    adminStatus = widgets['adminStatus']
    btnAdminOk = widgets['btnAdminOk']
    btnAdminCancel = widgets['btnAdminCancel']
    staffCur = widgets['staffCur']
    staffNew = widgets['staffNew']
    staffEye = widgets['staffEye']
    staffStatus = widgets['staffStatus']
    btnStaffOk = widgets['btnStaffOk']
    btnStaffCancel = widgets['btnStaffCancel']
    customClose = widgets.get('customClose')

    # Titlebar close
    if customClose is not None:
        try:
            customClose.clicked.connect(dlg.reject)
        except Exception:
            pass

    # Toggle visibility buttons
    # Wire password visibility toggle.
    def _wire_eye(btn, le):
        try:
            btn.toggled.connect(lambda checked: le.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password))
        except Exception:
            pass

    _wire_eye(adminEye, adminCur)
    _wire_eye(staffEye, staffCur)

    # Coordinator & gates
    fc = FieldCoordinator(dlg)

    # Determine user id for admin (prefer explicit arg; fallback to session id)
    try:
        uid = int(user_id) if user_id is not None else None
    except Exception:
        uid = None

    if uid is None:
        try:
            if getattr(host_window, 'current_user_id', None):
                uid = int(host_window.current_user_id)
        except Exception:
            uid = None

    # Focus gate: lock new-password and OK button until current password validated
    try:
        adminNew.setReadOnly(False)
    except Exception:
        pass
    admin_gate = FocusGate([adminNew, btnAdminOk], lock_enabled=True, lock_read_only=True)
    admin_gate.remember()
    try:
        admin_gate.remember_placeholders([adminNew])
        admin_gate.hide_placeholders([adminNew])
    except Exception:
        pass
    admin_gate.lock()

    # Validation function for current admin password
    # Validate current admin password before unlocking new password.
    def _validate_admin_current():
        txt = adminCur.text() or ''
        if not txt:
            raise ValueError('Enter current password')
        try:
            ok = False
            if uid is not None:
                ok = verify_password(uid, txt)
            if not ok:
                raise ValueError('Invalid current password')
        except ValueError:
            raise
        except Exception:
            raise ValueError('Password check failed')
        # Unlock the gate on success
        try:
            admin_gate.unlock()
            admin_gate.restore_placeholders([adminNew])
        except Exception:
            pass
        return True

    # Register field in coordinator so ENTER handling and auto-clear work
    fc.register_validator(adminCur, _validate_admin_current, adminStatus)
    fc.add_link(adminCur, target_map={}, next_focus=adminNew, status_label=adminStatus, validate_fn=_validate_admin_current, auto_jump=True)

    # New password validation using shared input handler
    # Validate new admin password using shared rules.
    def _validate_new_admin():
        try:
            return input_handler.handle_password_input(adminNew)
        except ValueError as e:
            raise
        except Exception:
            raise ValueError('Invalid new password')

    fc.register_validator(adminNew, _validate_new_admin, adminStatus)
    fc.add_link(adminNew, target_map={}, next_focus=btnAdminOk, status_label=adminStatus, validate_fn=_validate_new_admin, auto_jump=True)

    # btnAdminOk click handler: validate again and update DB
    # Commit admin password update after validation.
    def _on_admin_ok():
        try:
            # Re-validate current and new
            _validate_admin_current()
            new_pwd = _validate_new_admin()
        except ValueError as e:
            fc.set_error(adminNew if 'new' in str(e).lower() else adminCur, str(e), status_label=adminStatus)
            return

        # Attempt update
        try:
            if uid is None:
                raise Exception('User id not found')
            update_password(uid, new_pwd)
        except Exception as exc:
            # Set post-close status as error and close dialog
            report_exception_post_close(dlg, 'update_password', exc, user_message='Failed to update password', level='error')
            dlg.reject()
            return

        # Success: set post-close info and close
        set_dialog_info(dlg, 'Password updated successfully')
        dlg.accept()

    try:
        btnAdminOk.clicked.connect(_on_admin_ok)
    except Exception:
        pass

    # Cancel/Close buttons
    try:
        btnAdminCancel.clicked.connect(dlg.reject)
        btnStaffCancel.clicked.connect(dlg.reject)
    except Exception:
        pass

    # Set initial focus to admin current password field and select all
    try:
        set_initial_focus(dlg, tab_widget=tabWidget, tab_name='ADMIN', first_widget=adminCur)
    except Exception:
        try:
            adminCur.setFocus()
        except Exception:
            pass

    return dlg


# Backward-compatible alias (older imports/call-sites).
open_admin_dialog = launch_admin_dialog
