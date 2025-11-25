from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QComboBox, QPushButton
import os

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(THIS_DIR))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
QSS_PATH = os.path.join(ASSETS_DIR, 'menu.qss')

GREETING_STRINGS = [
    "Thanks for shopping with us!",
    "Selamat Hari Raya Haji !",
    "Selamat Hari Raya !",
    "Merry Christmas !",
    "Majulah Singapura !",
    "Happy Vesak Day !",
    "Happy New Year !!!",
    "Happy Labor Day !",
    "Happy Good Friday !",
    "Happy Deepavali !",
    "Gōng xǐ fā cái !"
]

def open_greeting_dialog(parent=None):
    ui_path = os.path.join(UI_DIR, 'greeting_menu.ui')
    if not os.path.exists(ui_path):
        print('DEBUG: greeting_menu.ui not found at', ui_path)
        raise FileNotFoundError(f'greeting_menu.ui not found at {ui_path}')
    dlg = uic.loadUi(ui_path)
    from PyQt5.QtCore import Qt
    dlg.setModal(True)
    dlg.setWindowTitle('Customer Greeting Message')
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
    dlg.setFixedSize(420, 300)
    # Wire up combo box
    combo: QComboBox = dlg.findChild(QComboBox, 'greetingComboBox')
    if combo:
        combo.clear()
        combo.addItems(GREETING_STRINGS)
        combo.setCurrentIndex(0)
    # Wire up close button
    close_btn: QPushButton = dlg.findChild(QPushButton, 'customCloseBtn')
    if close_btn:
        close_btn.clicked.connect(dlg.reject)
    # Wire up Ok/Cancel
    ok_btn: QPushButton = dlg.findChild(QPushButton, 'btnGreetOk')
    cancel_btn: QPushButton = dlg.findChild(QPushButton, 'btnGreetCancel')
    if ok_btn:
        ok_btn.clicked.connect(dlg.accept)
    if cancel_btn:
        cancel_btn.clicked.connect(dlg.reject)
    dlg.exec_()
    # Return selected greeting or None if cancelled
    if dlg.result() == QDialog.Accepted and combo:
        return combo.currentText()
    return None
