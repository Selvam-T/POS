# modules/menu/devices_menu.py
import os
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QComboBox, QLineEdit, QLabel, QWidget

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(_THIS_DIR)))  # .../Project
_UI_DIR = os.path.join(_BASE_DIR, 'ui')

def _center_dialog_relative_to(dlg: QDialog, host) -> None:
    try:
        mw = host.frameGeometry().width(); mh = host.frameGeometry().height()
        mx = host.frameGeometry().x();     my = host.frameGeometry().y()
        dw = dlg.width();                  dh = dlg.height()
        dlg.move(mx + (mw - dw)//2, my + (mh - dh)//2)
    except Exception:
        pass

def open_devices_dialog(host_window):
    """Open Devices dialog (ui/devices_menu.ui) as a modal frameless panel."""
    ui_path = os.path.join(_UI_DIR, 'devices_menu.ui')
    if not os.path.exists(ui_path):
        return None

    # Best-effort dim overlay
    try: host_window._show_dim_overlay()
    except Exception: pass

    # Load UI
    try:
        content = uic.loadUi(ui_path)
    except Exception:
        try: host_window._hide_dim_overlay()
        except Exception: pass
        return None

    # Use content if it’s already a QDialog; otherwise wrap
    if isinstance(content, QDialog):
        dlg = content
    else:
        dlg = QDialog(host_window)
        lay = QVBoxLayout(dlg); lay.setContentsMargins(0, 0, 0, 0); lay.addWidget(content)

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
    _center_dialog_relative_to(dlg, host_window)

    # Titlebar close (optional)
    try:
        xbtn: QPushButton = dlg.findChild(QPushButton, 'customCloseBtn')
        if xbtn: xbtn.clicked.connect(dlg.reject)
    except Exception:
        pass

    # Device fields (names are guesses; robust if missing)
    baud_combo: QComboBox = dlg.findChild(QComboBox, 'baudRateComboBox')
    scale_combo: QComboBox = dlg.findChild(QComboBox, 'scalePortComboBox')
    scanner_combo: QComboBox = dlg.findChild(QComboBox, 'scannerModeComboBox')  # e.g., HID / Serial
    msg_lbl: QLabel = dlg.findChild(QLabel, 'statusLabel')

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
    if ok: ok.clicked.connect(dlg.accept)
    if cancel: cancel.clicked.connect(dlg.reject)

    result = None
    if dlg.exec_() == QDialog.Accepted:
        try:
            result = {
                'baud_rate': (baud_combo.currentText().strip() if baud_combo else None),
                'scale_port': (scale_combo.currentText().strip() if scale_combo else None),
                'scanner_mode': (scanner_combo.currentText().strip() if scanner_combo else None),
            }
        except Exception:
            result = {}

    # Cleanup overlay & focus
    try: host_window._hide_dim_overlay()
    except Exception: pass
    try:
        host_window.raise_(); host_window.activateWindow()
    except Exception: pass

    return result
