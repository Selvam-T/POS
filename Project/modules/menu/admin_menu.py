import os
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QWidget, QPushButton, QLineEdit, QToolButton, QLabel

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))  # .../Project
_UI_DIR = os.path.join(_PROJECT_DIR, 'ui')


def open_admin_dialog(host_window, current_user: str = 'Admin', is_admin: bool = True) -> None:
    """Open the Admin Settings dialog (ui/admin_menu.ui) as a modal.

    Args:
        host_window: Main window (needs _show_dim_overlay/_hide_dim_overlay helpers like logout dialog).
        current_user: Display name for "Logged in as:" label.
        is_admin: If False, the dialog will open read-only (no password/email changes allowed).
    """
    ui_path = os.path.join(_UI_DIR, 'admin_menu.ui')
    if not os.path.exists(ui_path):
        print('admin_menu.ui missing at', ui_path)
        return

    # Dim background (best effort)
    try:
        host_window._show_dim_overlay()
    except Exception:
        pass

    try:
        content = uic.loadUi(ui_path)
    except Exception as e:
        print('Failed to load admin_menu.ui:', e)
        try:
            host_window._hide_dim_overlay()
        except Exception:
            pass
        return

    # If the .ui root is already a QDialog use it; else wrap
    if isinstance(content, QDialog):
        dlg = content
    else:
        dlg = QDialog(host_window)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(content)

    # Basic window flags (frameless like logout) + modality
    try:
        dlg.setParent(host_window)
        dlg.setModal(True)
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
        dlg.setObjectName('AdminDialogContainer')
        dlg.setWindowTitle('Admin Settings')
    except Exception:
        pass

    # Center relative to main window & size to hint
    try:
        dlg.adjustSize()
        sh = dlg.sizeHint()
        mw = host_window.frameGeometry().width()
        mh = host_window.frameGeometry().height()
        dw = max(520, sh.width() + 24)
        dh = max(380, sh.height() + 24)
        dlg.setFixedSize(dw, dh)
        mx = host_window.frameGeometry().x()
        my = host_window.frameGeometry().y()
        dlg.move(mx + (mw - dw)//2, my + (mh - dh)//2)
    except Exception:
        pass

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
                'adminCurrentPassword','adminNewPassword','btnAdminSave',
                'staffCurrentPassword','staffNewPassword','btnStaffSave',
                'currentEmailLineEdit','newEmailLineEdit','btnEmailSave',
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

    # Simple stub save actions (placeholder: print values)
    def _stub_save(which: str):
        try:
            if which == 'admin':
                cur = dlg.findChild(QLineEdit,'adminCurrentPassword')
                new = dlg.findChild(QLineEdit,'adminNewPassword')
            elif which == 'staff':
                cur = dlg.findChild(QLineEdit,'staffCurrentPassword')
                new = dlg.findChild(QLineEdit,'staffNewPassword')
            else:
                cur = dlg.findChild(QLineEdit,'currentEmailLineEdit')
                new = dlg.findChild(QLineEdit,'newEmailLineEdit')
            print(f"[AdminSettings][{which}] current={cur.text() if cur else ''} new={new.text() if new else ''}")
        except Exception:
            pass

    for btn_name, which in (('btnAdminSave','admin'), ('btnStaffSave','staff'), ('btnEmailSave','email')):
        b: QPushButton = dlg.findChild(QPushButton, btn_name)
        if b is not None:
            try:
                b.clicked.connect(lambda _, w=which: _stub_save(w))
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

    # Cleanup overlay when closed
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
