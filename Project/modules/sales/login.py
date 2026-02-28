import os
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QLineEdit, QComboBox, QLabel, QPushButton

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))
UI_PATH = os.path.join(_PROJECT_DIR, "ui", "login.ui")
QSS_PATH = os.path.join(_PROJECT_DIR, "assets", "main.qss")


def launch_login_dialog(parent=None):
    dlg = uic.loadUi(UI_PATH, parent)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

    # Style (optional)
    try:
        with open(QSS_PATH, "r") as f:
            dlg.setStyleSheet(f.read())
    except Exception:
        pass

    close_btn = dlg.findChild(QPushButton, "customCloseBtn")
    username_combo = dlg.findChild(QComboBox, "loginComboBox")
    password_edit = dlg.findChild(QLineEdit, "loginPassLineEdit")
    status_label = dlg.findChild(QLabel, "loginStatusLabel")

    from modules.db_operation.users_repo import validate_user_credentials
    from modules.ui_utils import ui_feedback

    def show_error(msg="Invalid username or password."):
        if status_label:
            ui_feedback.set_status_label(status_label, msg, ok=False)
        if password_edit:
            password_edit.setFocus()
            try:
                password_edit.selectAll()
            except Exception:
                pass

    def clear_error():
        if status_label:
            ui_feedback.clear_status_label(status_label)

    def validate_now():
        username = (
            username_combo.currentText().strip().lower()
            if username_combo
            else ""
        )
        password = password_edit.text() if password_edit else ""

        if not (username and password):
            show_error()
            return False

        user = validate_user_credentials(username, password)
        if user:
            clear_error()
            return True

        show_error()
        return False

    def on_enter_pressed():
        if validate_now():
            dlg.accept()

    # Keep modal open unless validation succeeds (covers external accept triggers)
    _orig_accept = dlg.accept

    def guarded_accept():
        if validate_now():
            return _orig_accept()
        return None

    dlg.accept = guarded_accept

    # Disable QPushButton auto-default so pressing Enter won't activate a default button
    try:
        for btn in dlg.findChildren(QPushButton):
            try:
                btn.setAutoDefault(False)
                btn.setDefault(False)
            except Exception:
                pass
    except Exception:
        pass

    # Intercept Enter/Return at the dialog level to ensure our handler runs
    try:
        from PyQt5.QtCore import QObject, QEvent

        class _EnterFilter(QObject):
            def __init__(self, parent):
                super().__init__(parent)

            def eventFilter(self, obj, event):
                if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    fw = dlg.focusWidget()
                    if fw is password_edit or fw is username_combo:
                        try:
                            on_enter_pressed()
                        except Exception:
                            pass
                        return True
                return super().eventFilter(obj, event)

        dlg._enter_filter = _EnterFilter(dlg)
        dlg.installEventFilter(dlg._enter_filter)
    except Exception:
        pass

    # UX wiring
    if password_edit:
        password_edit.setFocus()
        try:
            password_edit.selectAll()
        except Exception:
            pass
        password_edit.returnPressed.connect(on_enter_pressed)
        password_edit.textChanged.connect(lambda _: clear_error())

    if username_combo:
        # if username changes, clear any previous error
        username_combo.currentIndexChanged.connect(lambda *_: clear_error())

    if close_btn:
        close_btn.clicked.connect(dlg.reject)

    return dlg.exec_() == QDialog.Accepted