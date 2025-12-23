from PyQt5 import uic
from PyQt5.QtWidgets import QDialog
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')


def open_view_hold_dialog(parent=None):
    ui_path = os.path.join(UI_DIR, 'view_hold.ui')
    dlg = QDialog(parent)
    uic.loadUi(ui_path, dlg)
    dlg.setModal(True)
    dlg.setWindowTitle('View Held Sales')
    # Connect buttons
    dlg.btnResume.clicked.connect(lambda: dlg.done(1))  # 1 = Resume
    dlg.btnDelete.clicked.connect(lambda: dlg.done(2))  # 2 = Delete
    dlg.btnClose.clicked.connect(dlg.reject)
    return dlg
