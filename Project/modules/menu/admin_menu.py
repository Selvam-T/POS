import os
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QWidget, QPushButton, QLineEdit, QToolButton, QLabel
from modules.ui_utils.error_logger import log_error

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(THIS_DIR))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
QSS_PATH = os.path.join(ASSETS_DIR, 'menu.qss')


def open_admin_dialog(host_window, current_user: str = 'Admin', is_admin: bool = True):
    """Open the Admin Settings dialog (ui/admin_menu.ui) as a modal.
    
    DialogWrapper handles: overlay, sizing, centering, scanner blocking, cleanup, and focus restoration.
    This function only creates and returns the QDialog.

    Args:
        host_window: Main window instance
        current_user: Display name for "Logged in as:" label.
        is_admin: If False, the dialog will open read-only (no password/email changes allowed).
    
    Returns:
        QDialog instance ready for DialogWrapper.open_dialog_scanner_blocked() to execute
    """
    ui_path = os.path.join(UI_DIR, 'admin_menu.ui')
    if not os.path.exists(ui_path):
        try:
            log_error(f"admin_menu.ui missing at {ui_path}")
        except Exception:
            pass
        return None

    try:
        content = uic.loadUi(ui_path)
    except Exception as e:
        try:
            log_error(f"Failed to load admin_menu.ui: {e}")
        except Exception:
            pass
        return None

    # If the .ui root is already a QDialog use it; else wrap
    if isinstance(content, QDialog):
        dlg = content
    else:
        dlg = QDialog(host_window)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(content)

    # Basic window flags (frameless like logout) + modality
    dlg.setParent(host_window)
    dlg.setModal(True)
    dlg.setWindowModality(Qt.ApplicationModal)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
    dlg.setObjectName('AdminDialogContainer')
    
    # Apply stylesheet
    if os.path.exists(QSS_PATH):
        try:
            with open(QSS_PATH, 'r', encoding='utf-8') as f:
                dlg.setStyleSheet(f.read())
        except Exception as e:
            try:
                log_error(f"Failed to load menu.qss: {e}")
            except Exception:
                pass
    
    # Wire custom window titlebar X button to close dialog
    custom_close_btn = dlg.findChild(QPushButton, 'customCloseBtn')
    if custom_close_btn is not None:
        custom_close_btn.clicked.connect(dlg.reject)

    # Populate logged-in label
    try:
        logged_lbl: QLabel = dlg.findChild(QLabel, 'loggedInLabel')
        if logged_lbl is not None:
            logged_lbl.setText(f"Logged in as: {current_user}")
    except Exception:
        pass

    # Show/hide ability hints based on is_admin
    try:
        info_lbl: QLabel = dlg.findChild(QLabel, 'infoLabel')
        if info_lbl is not None:
            if is_admin:
                info_lbl.setText('Only Admin can modify settings')
            else:
                info_lbl.setText('Read-only: Staff cannot modify settings')
    except Exception:
        pass

    # Helper to set enabled/disabled for change controls
    def _set_change_enabled(enabled: bool):
        try:
            for name in (
                'adminCurrentPassword','adminNewPassword','btnAdminOk',
                'staffCurrentPassword','staffNewPassword','btnStaffOk',
                'currentEmailLineEdit','newEmailLineEdit','btnEmailOk',
                'btnToggleAdminCurrent','btnToggleStaffCurrent'
            ):
                w = dlg.findChild(QWidget, name)
                if w is not None:
                    # Keep currentEmailLineEdit readOnly always; override enabled for style only
                    if name == 'currentEmailLineEdit':
                        try:
                            w.setEnabled(True)  # stays visible
                        except Exception:
                            pass
                        continue
                    try:
                        w.setEnabled(enabled)
                    except Exception:
                        pass
        except Exception:
            pass

    if not is_admin:
        _set_change_enabled(False)

    # Toggle password visibility for given tool button + target line edit
    def _wire_eye(btn_name: str, line_name: str):
        btn: QToolButton = dlg.findChild(QToolButton, btn_name)
        le: QLineEdit = dlg.findChild(QLineEdit, line_name)
        if btn is None or le is None:
            return
        def _on_toggled(checked: bool):
            try:
                le.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
            except Exception:
                pass
        try:
            btn.toggled.connect(_on_toggled)
        except Exception:
            pass

    _wire_eye('btnToggleAdminCurrent','adminCurrentPassword')
    _wire_eye('btnToggleStaffCurrent','staffCurrentPassword')

    # Wire Save and Cancel buttons to close window and exit
    def _close_and_exit():
        try:
            dlg.reject()
            import sys
            sys.exit(0)
        except Exception:
            pass

    for btn_name in ('btnAdminOk','btnAdminCancel','btnStaffOk','btnStaffCancel','btnEmailOk','btnEmailCancel'):
        b: QPushButton = dlg.findChild(QPushButton, btn_name)
        if b is not None:
            try:
                b.clicked.connect(_close_and_exit)
            except Exception:
                pass

    # Close button & title bar X
    try:
        close_btn: QPushButton = dlg.findChild(QPushButton, 'closeButton')
        if close_btn is not None:
            close_btn.clicked.connect(dlg.reject)
        x_btn: QPushButton = dlg.findChild(QPushButton, 'customCloseBtn')
        if x_btn is not None:
            x_btn.clicked.connect(dlg.reject)
    except Exception:
        pass

    # Basic drag move support using customTitleBar (same pattern as logout)
    try:
        title_bar = dlg.findChild(QWidget, 'customTitleBar')
        if title_bar is not None:
            dlg._drag_pos = None
            def _mousePress(ev):
                try:
                    from PyQt5.QtCore import Qt as _Qt
                    if ev.button() == _Qt.LeftButton:
                        dlg._drag_pos = ev.globalPos() - dlg.frameGeometry().topLeft()
                        ev.accept()
                except Exception:
                    pass
            def _mouseMove(ev):
                try:
                    from PyQt5.QtCore import Qt as _Qt
                    if dlg._drag_pos is not None and ev.buttons() & _Qt.LeftButton:
                        dlg.move(ev.globalPos() - dlg._drag_pos)
                        ev.accept()
                except Exception:
                    pass
            def _mouseRelease(ev):
                dlg._drag_pos = None
            title_bar.mousePressEvent = _mousePress
            title_bar.mouseMoveEvent = _mouseMove
            title_bar.mouseReleaseEvent = _mouseRelease
    except Exception:
        pass

    # Return QDialog for DialogWrapper to execute
    return dlg
