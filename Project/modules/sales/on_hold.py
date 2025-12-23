from PyQt5 import uic
from PyQt5.QtWidgets import QDialog
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')


def open_on_hold_dialog(parent=None):
    ui_path = os.path.join(UI_DIR, 'on_hold.ui')
    dlg = QDialog(parent)
    uic.loadUi(ui_path, dlg)
    dlg.setModal(True)
    dlg.setWindowTitle('Put Sale On Hold')
    # Connect buttons
    dlg.btnCancel.clicked.connect(dlg.reject)
    dlg.btnConfirm.clicked.connect(dlg.accept)
    return dlg
