import os
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QPushButton, QLabel, QDialog

# Compute project root and UI directory relative to this file
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))  # .../Project
_UI_DIR = os.path.join(_PROJECT_DIR, 'ui')


def _center_dialog_relative_to(dlg: QDialog, host) -> None:
    try:
        mw = host.frameGeometry().width()
        mh = host.frameGeometry().height()
        mx = host.frameGeometry().x()
        my = host.frameGeometry().y()
        dw = dlg.width()
        dh = dlg.height()
        dlg.move(mx + (mw - dw) // 2, my + (mh - dh) // 2)
    except Exception:
        pass


def open_logout_dialog(host_window) -> None:
    """Open the Logout confirmation dialog as a modal using ui/logout_menu.ui.

    Args:
        host_window: The main window (expects helper methods like _show_dim_overlay and _hide_dim_overlay).
    """
    logout_ui = os.path.join(_UI_DIR, 'logout_menu.ui')

    # Dim background (best-effort)
    try:
        host_window._show_dim_overlay()
    except Exception:
        pass

    # Load UI content
    content = None
    if os.path.exists(logout_ui):
        try:
            content = uic.loadUi(logout_ui)
        except Exception:
            content = None

    # Use QDialog as the dialog container
    dlg = QDialog(host_window)
    dlg.setModal(True)
    dlg.setObjectName('LogoutDialogContainer')
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
    # Set dialog size and embed content
    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(0, 0, 0, 0)
    if content is not None:
        layout.addWidget(content)
        try:
            content.adjustSize()
            sh = content.sizeHint()
            dw = max(360, sh.width() + 24)
            dh = max(140, sh.height() + 24)
            dlg.setFixedSize(dw, dh)
        except Exception:
            dlg.setFixedSize(420, 180)
    else:
        # Simple fallback content
        info = QLabel('Are you sure you want to logout?')
        info.setWordWrap(True)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(info)
        row = QWidget()
        from PyQt5.QtWidgets import QHBoxLayout
        hl = QHBoxLayout(row)
        hl.addStretch(1)
        btn_cancel = QPushButton('Cancel')
        btn_ok = QPushButton('Yes, Logout !')
        hl.addWidget(btn_cancel)
        hl.addWidget(btn_ok)
        layout.addWidget(row)
        dlg.setFixedSize(420, 180)
        try:
            btn_cancel.clicked.connect(dlg.reject)
            btn_ok.clicked.connect(lambda: (dlg.accept(), host_window._perform_logout()))
        except Exception:
            pass

    # Center relative to host
    _center_dialog_relative_to(dlg, host_window)
    # Wire buttons and behavior when using full UI content
    if content is not None:
        try:
            container = content
            btn_cancel: QPushButton = container.findChild(QPushButton, 'pushButton_cancel')
            btn_ok: QPushButton = container.findChild(QPushButton, 'pushButton_logout')
            btn_x: QPushButton = container.findChild(QPushButton, 'customCloseBtn')
            if btn_cancel is not None:
                btn_cancel.clicked.connect(dlg.reject)
            if btn_ok is not None:
                btn_ok.clicked.connect(lambda: (dlg.accept(), host_window._perform_logout()))
            if btn_x is not None:
                btn_x.clicked.connect(dlg.reject)
        except Exception:
            pass

    # Cleanup dim overlay and focus when closed
    def _cleanup(_result):
        try:
            host_window._hide_dim_overlay()
        except Exception:
            pass
        try:
            host_window.raise_()
            host_window.activateWindow()
        except Exception:
            pass

    dlg.finished.connect(_cleanup)
    try:
        dlg.raise_()
    except Exception:
        pass
    dlg.exec_()
