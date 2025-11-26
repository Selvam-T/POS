# modules/menu/devices_menu.py
import os
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QComboBox, QLineEdit, QLabel, QWidget
from modules.menu.dialog_utils import center_dialog_relative_to

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
QSS_PATH = os.path.join(ASSETS_DIR, 'menu.qss')


def open_devices_dialog(host_window, *args, **kwargs):
    """Open Devices dialog (ui/devices_menu.ui) as a modal frameless panel, standardized for menu dialogs."""
    ui_path = os.path.join(UI_DIR, 'devices_menu.ui')
    if not os.path.exists(ui_path):
        return None

    # Best-effort dim overlay
    try:
        host_window._show_dim_overlay()
    except Exception:
        pass

    # Load UI
    try:
        content = uic.loadUi(ui_path)
    except Exception:
        try:
            host_window._hide_dim_overlay()
        except Exception:
            pass
        return None

    # Use content if it’s already a QDialog; otherwise wrap
    if isinstance(content, QDialog):
        dlg = content
    else:
        dlg = QDialog(host_window)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(content)

    # Frameless + modal
    dlg.setParent(host_window)
    dlg.setModal(True)
    dlg.setWindowModality(Qt.ApplicationModal)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)

    # Size & center
    try:
        host_w = host_window.frameGeometry().width()
        host_h = host_window.frameGeometry().height()
        dlg.setFixedSize(max(500, int(host_w * 0.55)), max(360, int(host_h * 0.52)))
    except Exception:
        dlg.setFixedSize(640, 440)
    center_dialog_relative_to(dlg, host_window)

    # Titlebar close (optional)
    try:
        xbtn: QPushButton = dlg.findChild(QPushButton, 'customCloseBtn')
        if xbtn:
            xbtn.clicked.connect(dlg.reject)
    except Exception:
        pass

    # Device fields (names are guesses; robust if missing)
    baud_combo: QComboBox = dlg.findChild(QComboBox, 'baudRateComboBox')
    # Populate common baud rates if combo exists & empty
    try:
        if baud_combo and baud_combo.count() == 0:
            for b in ('9600','19200','38400','57600','115200'):
                baud_combo.addItem(b)
    except Exception:
        pass

    # OK/Cancel wiring (optional names, robust to missing)
    ok = dlg.findChild(QPushButton, 'btnOk') or dlg.findChild(QPushButton, 'okButton') or dlg.findChild(QPushButton, 'saveButton')
    cancel = dlg.findChild(QPushButton, 'btnCancel') or dlg.findChild(QPushButton, 'cancelButton') or dlg.findChild(QPushButton, 'closeButton')
    if ok:
        ok.clicked.connect(dlg.accept)
    if cancel:
        cancel.clicked.connect(dlg.reject)

    def _cleanup_overlay(_code):
        try:
            host_window._hide_dim_overlay()
        except Exception:
            pass
        try:
            host_window.raise_()
            host_window.activateWindow()
        except Exception:
            pass

    dlg.finished.connect(_cleanup_overlay)
    return dlg
