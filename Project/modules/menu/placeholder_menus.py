"""Placeholder menu dialog loaders for Reports, Devices, Greeting.

Each function loads the corresponding .ui (reports_menu.ui, devices_menu.ui, greeting_menu.ui)
and displays a frameless modal dialog centered over the host main window.

The .ui files contain an `underConstructionLabel` so no dynamic text insertion
is required here. These are stand-ins until full feature implementations replace them.

Usage (from main window wiring):
    from modules.menu.placeholder_menus import open_reports_dialog
    reportsBtn.clicked.connect(lambda: open_reports_dialog(self))

All dialogs reuse the main window's dim overlay helpers if available.
"""

import os
from typing import Optional
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QWidget

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))  # .../Project/modules/menu -> .../Project
_UI_DIR = os.path.join(_PROJECT_DIR, 'ui')


def _open_placeholder(host_window: QWidget, ui_name: str, title: str, min_w: int = 420, min_h: int = 300) -> None:
    ui_path = os.path.join(_UI_DIR, ui_name)
    if not os.path.exists(ui_path):
        print(f"[PlaceholderMenus] Missing UI: {ui_path}")
        return

    # Attempt to show dim overlay for modal effect
    try:
        host_window._show_dim_overlay()
    except Exception:
        pass

    try:
        content = uic.loadUi(ui_path)
    except Exception as e:
        print(f"[PlaceholderMenus] Failed to load {ui_name}: {e}")
        try:
            host_window._hide_dim_overlay()
        except Exception:
            pass
        return

    # Root may already be a QDialog (since .ui defines QDialog); wrap only if needed
    if isinstance(content, QDialog):
        dlg = content
    else:
        dlg = QDialog(host_window)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(content)

    try:
        dlg.setParent(host_window)
        dlg.setModal(True)
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
        dlg.setObjectName(f"{title.replace(' ', '')}DialogContainer")
    except Exception:
        pass

    # Size & center
    try:
        dlg.adjustSize()
        sh = dlg.sizeHint()
        mw = host_window.frameGeometry().width()
        mh = host_window.frameGeometry().height()
        dw = max(min_w, sh.width() + 24)
        dh = max(min_h, sh.height() + 24)
        dlg.setFixedSize(dw, dh)
        mx = host_window.frameGeometry().x()
        my = host_window.frameGeometry().y()
        dlg.move(mx + (mw - dw)//2, my + (mh - dh)//2)
    except Exception:
        pass

    # Wire close buttons (custom title X + footer Close) if present
    try:
        from PyQt5.QtWidgets import QPushButton
        x_btn = dlg.findChild(QPushButton, 'customCloseBtn')
        if x_btn is not None:
            x_btn.clicked.connect(dlg.reject)
        close_btn = dlg.findChild(QPushButton, 'closeButton')
        if close_btn is not None:
            close_btn.clicked.connect(dlg.reject)
    except Exception:
        pass

    # Basic drag move using customTitleBar like other dialogs
    try:
        title_bar = dlg.findChild(QWidget, 'customTitleBar')
        if title_bar is not None:
            dlg._drag_pos = None
            def _mousePress(ev):
                from PyQt5.QtCore import Qt as _Qt
                if ev.button() == _Qt.LeftButton:
                    dlg._drag_pos = ev.globalPos() - dlg.frameGeometry().topLeft()
                    ev.accept()
            def _mouseMove(ev):
                from PyQt5.QtCore import Qt as _Qt
                if dlg._drag_pos is not None and ev.buttons() & _Qt.LeftButton:
                    dlg.move(ev.globalPos() - dlg._drag_pos)
                    ev.accept()
            def _mouseRelease(ev):
                dlg._drag_pos = None
            title_bar.mousePressEvent = _mousePress
            title_bar.mouseMoveEvent = _mouseMove
            title_bar.mouseReleaseEvent = _mouseRelease
    except Exception:
        pass

    def _cleanup(_code):
        try:
            host_window._hide_dim_overlay()
        except Exception:
            pass
        try:
            host_window.raise_(); host_window.activateWindow()
        except Exception:
            pass

    dlg.finished.connect(_cleanup)
    try:
        dlg.raise_()
    except Exception:
        pass
    dlg.exec_()


def open_reports_dialog(host_window: QWidget) -> None:
    _open_placeholder(host_window, 'reports_menu.ui', 'Reports')


def open_devices_dialog(host_window: QWidget) -> None:
    _open_placeholder(host_window, 'devices_menu.ui', 'Devices')


def open_greeting_dialog(host_window: QWidget) -> None:
    _open_placeholder(host_window, 'greeting_menu.ui', 'Greeting')
