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

    # Fixed user ids for password change (documented invariant in DB seed)
    ADMIN_USER_ID = 1
    STAFF_USER_ID = 2

    # Determine user id for admin (prefer explicit arg; fallback to fixed id)
    try:
        admin_uid = int(user_id) if user_id is not None else ADMIN_USER_ID
    except Exception:
        admin_uid = ADMIN_USER_ID

    # Determine user id for staff (fixed id)
    staff_uid = STAFF_USER_ID

    def _setup_password_tab(*, cur_edit, new_edit, ok_btn, status_lbl, user_id: int | None):
        # Focus gate: lock new-password and OK button until current password validated
        try:
            new_edit.setReadOnly(False)
        except Exception:
            pass
        gate = FocusGate([new_edit, ok_btn], lock_enabled=True, lock_read_only=True)
        gate.remember()
        try:
            gate.remember_placeholders([new_edit])
            gate.hide_placeholders([new_edit])
        except Exception:
            pass
        gate.lock()

        # Validate current password before unlocking new password.
        def _validate_current():
            txt = cur_edit.text() or ''
            if not txt:
                raise ValueError('Enter current password')
            try:
                ok = False
                if user_id is not None:
                    ok = verify_password(user_id, txt)
                if not ok:
                    raise ValueError('Invalid current password')
            except ValueError:
                raise
            except Exception:
                raise ValueError('Password check failed')
            try:
                gate.unlock()
                gate.restore_placeholders([new_edit])
            except Exception:
                pass
            return True

        # Validate new password using shared rules.
        def _validate_new():
            try:
                return input_handler.handle_password_input(new_edit)
            except ValueError:
                raise
            except Exception:
                raise ValueError('Invalid new password')

        fc.register_validator(cur_edit, _validate_current, status_lbl)
        fc.add_link(cur_edit, target_map={}, next_focus=new_edit, status_label=status_lbl, validate_fn=_validate_current, auto_jump=True)

        fc.register_validator(new_edit, _validate_new, status_lbl)
        fc.add_link(new_edit, target_map={}, next_focus=ok_btn, status_label=status_lbl, validate_fn=_validate_new, auto_jump=True)

        def _on_ok():
            try:
                _validate_current()
                new_pwd = _validate_new()
            except ValueError as e:
                fc.set_error(new_edit if 'new' in str(e).lower() else cur_edit, str(e), status_label=status_lbl)
                return

            try:
                if user_id is None:
                    raise Exception('User id not found')
                update_password(user_id, new_pwd)
            except Exception as exc:
                report_exception_post_close(dlg, 'update_password', exc, user_message='Failed to update password', level='error')
                dlg.reject()
                return

            set_dialog_info(dlg, 'Password updated successfully')
            dlg.accept()

        try:
            ok_btn.clicked.connect(_on_ok)
        except Exception:
            pass

    _setup_password_tab(cur_edit=adminCur, new_edit=adminNew, ok_btn=btnAdminOk, status_lbl=adminStatus, user_id=admin_uid)
    _setup_password_tab(cur_edit=staffCur, new_edit=staffNew, ok_btn=btnStaffOk, status_lbl=staffStatus, user_id=staff_uid)

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
