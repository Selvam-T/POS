import os
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QPushButton, QLabel, QDialog
from modules.ui_utils.dialog_utils import center_dialog_relative_to

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')
_ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
_QSS_PATH = os.path.join(_ASSETS_DIR, 'dialog.qss')


def launch_cancelsale_dialog(host_window):
    cancel_sale_ui = os.path.join(UI_DIR, 'cancel_sale.ui')

    # Load UI content
    content = None
    if os.path.exists(cancel_sale_ui):
        try:
            content = uic.loadUi(cancel_sale_ui)
        except Exception:
            content = None

    # Use QDialog as the dialog container
    dlg = QDialog(host_window)
    dlg.setModal(True)
    dlg.setObjectName('CancelAllDialogContainer')
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
    
    # Apply stylesheet
    if os.path.exists(_QSS_PATH):
        try:
            with open(_QSS_PATH, 'r', encoding='utf-8') as f:
                dlg.setStyleSheet(f.read())
        except Exception as e:
            try:
                from modules.ui_utils.error_logger import log_error
                log_error(f"Failed to load dialog.qss: {e}")
            except Exception:
                pass
    
    from modules.ui_utils.ui_feedback import show_main_status

    # Wire custom window titlebar X button to close dialog
    if content is not None:
        custom_close_btn = content.findChild(QPushButton, 'customCloseBtn')
        if custom_close_btn is not None:
            custom_close_btn.clicked.connect(dlg.reject)

        # Set dialog size and embed content
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(content)
        # Wire UI-based buttons to dialog result (no business logic here)
        try:
            container = content
            btn_cancel = container.findChild(QPushButton, 'btnCancelAllCancel')
            btn_ok = container.findChild(QPushButton, 'btnCancelAllOk')
            btn_x = container.findChild(QPushButton, 'customCloseBtn')
            if btn_cancel is not None:
                btn_cancel.clicked.connect(dlg.reject)
            if btn_ok is not None:
                btn_ok.clicked.connect(dlg.accept)
            if btn_x is not None:
                btn_x.clicked.connect(dlg.reject)
        except Exception:
            pass
        btn_cancel.setFocus()
        return dlg

    # --- Fallback: UI failed to load ---
    # Log error (shared logger)
    try:
        from modules.ui_utils.error_logger import log_error
        log_error('Failed to load cancel_sale.ui, using fallback dialog.')
    except Exception:
        pass
    # Show statusbar message
    try:
        show_main_status(host_window, 'Cancel Sale dialog fallback loaded.', True, 5000)
    except Exception:
        pass

    # Build fallback dialog content
    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(16, 16, 16, 16)
    info = QLabel('clear all transactions?')
    info.setStyleSheet('QLabel { color: blue; font-size: 16px; font-weight: bold; }')
    info.setWordWrap(True)
    layout.addWidget(info)
    info2 = QLabel('( ui failed to load)')
    layout.addWidget(info2)
    row = QWidget()
    from PyQt5.QtWidgets import QHBoxLayout
    hl = QHBoxLayout(row)
    hl.addStretch(1)
    btn_cancel = QPushButton('Cancel')
    btn_ok = QPushButton('Yes, Clear All')
    # Minimal style for buttons
    btn_cancel.setStyleSheet('QPushButton { background-color: #d32f2f; color: #fff; font-size: 16px; min-width: 100px; min-height: 40px; }')
    btn_ok.setStyleSheet('QPushButton { background-color: #388e3c; color: #fff; font-size: 16px; min-width: 100px; min-height: 40px; }')
    hl.addWidget(btn_cancel)
    hl.addWidget(btn_ok)
    layout.addWidget(row)
    try:
        btn_cancel.clicked.connect(dlg.reject)
        btn_ok.clicked.connect(dlg.accept)
    except Exception:
        pass
    btn_cancel.setFocus()
    return dlg
