import os
from PyQt5 import uic
from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QDialog, QLineEdit, QComboBox, QLabel, QPushButton, QApplication
from config import COMPANY_NAME, DIALOG_RATIOS, LOGIN_BACKGROUND, QSS_DIR, UI_DIR
from modules.runtime_paths import load_stylesheet

UI_PATH = os.path.join(UI_DIR, "login.ui")
QSS_PATH = os.path.join(QSS_DIR, "main.qss")


def _apply_login_dialog_geometry(dlg, parent=None):
    ratio = DIALOG_RATIOS.get("login")
    if not ratio:
        return

    width_ratio, height_ratio = ratio
    base_rect = None

    if parent is not None:
        try:
            base_rect = parent.frameGeometry()
        except Exception:
            base_rect = None

    if base_rect is None or base_rect.isEmpty():
        screen = None
        if parent is not None:
            try:
                screen = parent.screen()
            except Exception:
                screen = None
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return
        base_rect = screen.availableGeometry()

    target_width = int(base_rect.width() * width_ratio)
    target_height = int(base_rect.height() * height_ratio)
    final_width = max(dlg.minimumWidth(), target_width)
    final_height = max(dlg.minimumHeight(), target_height)

    dlg.resize(final_width, final_height)
    dlg.move(
        base_rect.x() + (base_rect.width() - dlg.width()) // 2,
        base_rect.y() + (base_rect.height() - dlg.height()) // 2,
    )


def _install_login_background(dlg):
    if not LOGIN_BACKGROUND or not os.path.exists(LOGIN_BACKGROUND):
        return

    source_pixmap = QPixmap(LOGIN_BACKGROUND)
    if source_pixmap.isNull():
        return

    background_label = QLabel(dlg)
    background_label.setObjectName("loginBackgroundLabel")
    background_label.setAttribute(Qt.WA_TransparentForMouseEvents)
    background_label.setAlignment(Qt.AlignCenter)

    def update_background():
        size = dlg.size()
        if size.isEmpty():
            return
        scaled = source_pixmap.scaled(
            size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        background_label.setGeometry(dlg.rect())
        background_label.setPixmap(scaled)
        background_label.lower()

    class _BackgroundResizeFilter(QObject):
        def eventFilter(self, obj, event):
            if event.type() in (QEvent.Resize, QEvent.Show):
                update_background()
            return False

    dlg._login_background_label = background_label
    dlg._login_background_filter = _BackgroundResizeFilter(dlg)
    dlg.installEventFilter(dlg._login_background_filter)
    update_background()

def launch_login_dialog(parent=None, *, return_user: bool = False):
    dlg = uic.loadUi(UI_PATH, parent)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
    dlg.customTitle.setText(COMPANY_NAME)
    try:
        dlg.setStyleSheet(load_stylesheet(QSS_PATH))
    except Exception:
        pass
    _apply_login_dialog_geometry(dlg, parent)
    _install_login_background(dlg)

    close_btn = dlg.findChild(QPushButton, "customCloseBtn")
    forget_btn = dlg.findChild(QPushButton, "loginForgetBtn")
    username_combo = dlg.findChild(QComboBox, "loginComboBox")
    password_edit = dlg.findChild(QLineEdit, "loginPassLineEdit")
    status_label = dlg.findChild(QLabel, "loginStatusLabel")

    from modules.db_operation.users_repo import (
        authenticate_user,
        build_authenticated_user,
        generate_temporary_password_for_user,
        set_must_change_password,
        # recommended to have this; otherwise use itemData approach (below)
        get_user_id_by_username,
    )
    from modules.ui_utils import ui_feedback, input_validation

    authenticated_user = None

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

        # store user_id as itemData when populating combo
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
        nonlocal authenticated_user
        username = username_combo.currentText().strip().lower() if username_combo else ""
        password = password_edit.text() if password_edit else ""

        # Format/sanity validation
        ok, err = input_validation.validate_username_password_input(username, password)
        if not ok:
            authenticated_user = None
            set_error(err or "Invalid username or password.")
            focus_password()
            return False

        # Authenticate against users repository
        user = authenticate_user(username, password)
        if user:
            # Use helper to normalize and compute is_admin; pass combo fallback
            authenticated_user = build_authenticated_user(user, fallback_uid=current_user_id())
            clear_status()
            return True

        authenticated_user = None
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
        # - uid == 1: generate a temporary password and copy it to clipboard
        # - uid == 2: instruct the user to contact admin
        if int(uid) == 1:
            temp_pwd = generate_temporary_password_for_user(int(uid), length=12)
            try:
                # mark the admin account to require a password change on next login
                set_must_change_password(int(uid), True)
            except Exception:
                # non-fatal; proceed even if flag update fails
                pass
            try:
                QApplication.clipboard().setText(temp_pwd)
            except Exception:
                pass
            set_ok("Login with temp password pasted to clipboard.")
            focus_password()
            return

        if int(uid) == 2:
            set_error("Please contact admin to login.")
            return

        # Fallback for other users
        set_error("Password recovery not supported for this user.")

    if password_edit:
        focus_password(select_all=True)
        password_edit.textChanged.connect(lambda *_: clear_status())

    if username_combo:
        username_combo.currentIndexChanged.connect(lambda *_: clear_status())

    if forget_btn:
        forget_btn.clicked.connect(on_forget_clicked)

    if close_btn:
        close_btn.clicked.connect(dlg.reject)

    accepted = dlg.exec_() == QDialog.Accepted
    if return_user:
        return authenticated_user if accepted else None
    return accepted
