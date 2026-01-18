import os
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QPushButton, QLabel, QDialog
from modules.ui_utils.dialog_utils import center_dialog_relative_to, load_ui_strict
from modules.ui_utils.error_logger import log_error

# Compute project root and UI directory relative to this file
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))  # .../Project
_UI_DIR = os.path.join(_PROJECT_DIR, 'ui')
_ASSETS_DIR = os.path.join(_PROJECT_DIR, 'assets')
_QSS_PATH = os.path.join(_ASSETS_DIR, 'menu.qss')


def open_logout_dialog(host_window):
    """Open the Logout confirmation dialog as a modal using ui/logout_menu.ui.

    Args:
        host_window: The main window instance
    
    Returns:
        QDialog instance ready for DialogWrapper.open_dialog_scanner_blocked() to execute
    """
    logout_ui = os.path.join(_UI_DIR, 'logout_menu.ui')

    # Load UI content (strict: no programmatic fallback)
    content = load_ui_strict(logout_ui, host_window=host_window, dialog_name='Logout')
    if content is None:
        return None

    # Use QDialog as the dialog container
    dlg = QDialog(host_window)
    dlg.setModal(True)
    dlg.setObjectName('LogoutDialogContainer')
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
    
    # Apply stylesheet
    if os.path.exists(_QSS_PATH):
        try:
            with open(_QSS_PATH, 'r', encoding='utf-8') as f:
                dlg.setStyleSheet(f.read())
        except Exception as e:
            try:
                log_error(f"Failed to load menu.qss: {e}")
            except Exception:
                pass
    
    # Wire custom window titlebar X button to close dialog
    custom_close_btn = content.findChild(QPushButton, 'customCloseBtn')
    if custom_close_btn is not None:
        custom_close_btn.clicked.connect(dlg.reject)
    
    # Set dialog size and embed content
    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(0, 0, 0, 0)

    layout.addWidget(content)

    # Wire UI-based buttons to dialog result (no business logic here)
    btn_cancel = None
    try:
        container = content
        btn_cancel = container.findChild(QPushButton, 'btnLogoutCancel')
        btn_ok = container.findChild(QPushButton, 'btnLogoutOk')
        btn_x = container.findChild(QPushButton, 'customCloseBtn')
        if btn_cancel is not None:
            btn_cancel.clicked.connect(dlg.reject)
        if btn_ok is not None:
            btn_ok.clicked.connect(dlg.accept)
        if btn_x is not None:
            btn_x.clicked.connect(dlg.reject)
    except Exception:
        pass

    if btn_cancel is not None:
        btn_cancel.setFocus()
    return dlg

    