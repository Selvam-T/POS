# modules/menu/reports_menu.py
import os
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QWidget, QPushButton, QDateEdit, QComboBox, QLabel

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

def open_reports_dialog(host_window):
    """Open Reports dialog (ui/reports_menu.ui) as a modal frameless panel."""
    ui_path = os.path.join(_UI_DIR, 'reports_menu.ui')
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

    # Wrap in QDialog if needed
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
        dlg.setFixedSize(max(480, int(host_w * 0.55)), max(340, int(host_h * 0.50)))
    except Exception:
        dlg.setFixedSize(600, 420)
    _center_dialog_relative_to(dlg, host_window)

    # Titlebar close (optional)
    try:
        xbtn: QPushButton = dlg.findChild(QPushButton, 'customCloseBtn')
        if xbtn: xbtn.clicked.connect(dlg.reject)
    except Exception:
        pass

    # OK/Cancel wiring (optional names, robust to missing widgets)
    ok = dlg.findChild(QPushButton, 'btnOk') or dlg.findChild(QPushButton, 'okButton')
    cancel = dlg.findChild(QPushButton, 'btnCancel') or dlg.findChild(QPushButton, 'cancelButton')
    if ok: ok.clicked.connect(dlg.accept)
    if cancel: cancel.clicked.connect(dlg.reject)

    # Optional widgets for selection/filters (names are guesses; safe if absent)
    kind_combo: QComboBox = dlg.findChild(QComboBox, 'reportTypeCombo')  # e.g. Daily/Monthly/Range/Charts
    start_date: QDateEdit = dlg.findChild(QDateEdit, 'startDateEdit')
    end_date: QDateEdit   = dlg.findChild(QDateEdit, 'endDateEdit')
    info_lbl: QLabel      = dlg.findChild(QLabel, 'statusLabel')

    result = None
    if dlg.exec_() == QDialog.Accepted:
        try:
            result = {
                'type': (kind_combo.currentText().strip() if kind_combo else None),
                'start': (start_date.date().toString('yyyy-MM-dd') if start_date else None),
                'end':   (end_date.date().toString('yyyy-MM-dd') if end_date else None),
            }
        except Exception:
            result = {}

    # Cleanup overlay
    try: host_window._hide_dim_overlay()
    except Exception: pass
    try:
        host_window.raise_(); host_window.activateWindow()
    except Exception: pass

    return result
