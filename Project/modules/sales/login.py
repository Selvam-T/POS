import os
from PyQt5 import uic
from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtWidgets import QDialog, QLineEdit, QComboBox, QLabel, QPushButton, QApplication

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))
UI_PATH = os.path.join(_PROJECT_DIR, "ui", "login.ui")
QSS_PATH = os.path.join(_PROJECT_DIR, "assets", "main.qss")


def launch_login_dialog(parent=None):
    dlg = uic.loadUi(UI_PATH, parent)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

    try:
        with open(QSS_PATH, "r") as f:
            dlg.setStyleSheet(f.read())
    except Exception:
        pass

    close_btn = dlg.findChild(QPushButton, "customCloseBtn")
    forget_btn = dlg.findChild(QPushButton, "loginForgetBtn")
    username_combo = dlg.findChild(QComboBox, "loginComboBox")
    password_edit = dlg.findChild(QLineEdit, "loginPassLineEdit")
    status_label = dlg.findChild(QLabel, "loginStatusLabel")

    from modules.db_operation.users_repo import (
        validate_user_credentials,
        get_recovery_email,
        generate_temporary_password_for_user,
        # recommended to have this; otherwise use itemData approach (below)
        get_user_id_by_username,
    )
    from modules.ui_utils import ui_feedback

    def clear_status():
        if status_label:
            ui_feedback.clear_status_label(status_label)

    def set_error(msg):
        if status_label:
            ui_feedback.set_status_label(status_label, msg, ok=False)

    def set_ok(msg):
        if status_label:
            ui_feedback.set_status_label(status_label, msg, ok=True)

    def focus_password(select_all=True):
        if not password_edit:
            return
        password_edit.setFocus()
        if select_all:
            try:
                password_edit.selectAll()
            except Exception:
                pass

    def current_user_id():
        if not username_combo:
            return None

        # BEST: store user_id as itemData when populating combo
        idx = username_combo.currentIndex()
        uid = username_combo.itemData(idx)
        if isinstance(uid, int):
            return uid

        # fallback: map by username text using helper that returns integer id
        username = username_combo.currentText().strip().lower()
        try:
            return get_user_id_by_username(username)
        except Exception:
            return None

    def validate_now():
        username = username_combo.currentText().strip().lower() if username_combo else ""
        password = password_edit.text() if password_edit else ""

        if not username or not password:
            set_error("Invalid username or password.")
            focus_password()
            return False

        if validate_user_credentials(username, password):
            clear_status()
            return True

        set_error("Invalid username or password.")
        focus_password()
        return False

    def try_accept():
        if validate_now():
            dlg.accept()

    # guard accept
    _orig_accept = dlg.accept

    def guarded_accept():
        if validate_now():
            return _orig_accept()
        return None

    dlg.accept = guarded_accept

    # prevent default button Enter behavior
    for btn in dlg.findChildren(QPushButton):
        btn.setAutoDefault(False)
        btn.setDefault(False)

    class _EnterFilter(QObject):
        def eventFilter(self, obj, event):
            if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
                fw = dlg.focusWidget()
                if fw in (password_edit, username_combo):
                    try_accept()
                    return True
            return False

    dlg._enter_filter = _EnterFilter(dlg)
    dlg.installEventFilter(dlg._enter_filter)

    def on_forget_clicked():
        uid = current_user_id()
        if uid is None:
            set_error("Select a user first.")
            return

        email = get_recovery_email(int(uid))
        if not email:
            set_error("No recovery email set for this user.")
            return

        temp_pwd = generate_temporary_password_for_user(int(uid), length=12)

        # No email configured: copy to clipboard for manual delivery
        try:
            QApplication.clipboard().setText(temp_pwd)
        except Exception:
            pass

        set_ok("Temporary password generated and copied to clipboard.")
        focus_password()

    if password_edit:
        focus_password(select_all=True)
        password_edit.textChanged.connect(lambda *_: clear_status())

    if username_combo:
        username_combo.currentIndexChanged.connect(lambda *_: clear_status())

    if forget_btn:
        forget_btn.clicked.connect(on_forget_clicked)

    if close_btn:
        close_btn.clicked.connect(dlg.reject)

    return dlg.exec_() == QDialog.Accepted