import os
from PyQt5.QtWidgets import QDialog, QPushButton
from PyQt5 import uic

# Paths
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))
UI_PATH = os.path.join(_PROJECT_DIR, 'ui', 'login.ui')
QSS_PATH = os.path.join(_PROJECT_DIR, 'assets', 'dialog.qss')

def launch_login_dialog(parent=None):
    """Launch Login dialog, return True if accepted, False otherwise."""
    dlg = uic.loadUi(UI_PATH, parent)
    dlg.setWindowTitle('Login')
    # Optionally apply QSS
    try:
        with open(QSS_PATH, 'r') as f:
            dlg.setStyleSheet(f.read())
    except Exception:
        pass
    # Connect OK and Cancel buttons
    ok_btn = dlg.findChild(QPushButton, 'btnLoginOk')
    if ok_btn:
        ok_btn.clicked.connect(dlg.accept)
    cancel_btn = dlg.findChild(QPushButton, 'btnLoginCancel')
    if cancel_btn:
        cancel_btn.clicked.connect(dlg.reject)
    result = dlg.exec_()
    return result == QDialog.Accepted
