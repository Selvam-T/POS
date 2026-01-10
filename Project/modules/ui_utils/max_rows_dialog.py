import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QWidget
from PyQt5.QtCore import Qt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
QSS_PATH = os.path.join(ASSETS_DIR, 'menu.qss')

def open_max_rows_dialog(parent=None, message=None):
    """Show a modal dialog informing user max sales table rows reached. Only X Close in custom titlebar."""
    dlg = QDialog(parent)
    dlg.setModal(True)
    dlg.setObjectName('MaxRowsDialog')
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
    # Apply stylesheet if available
    if os.path.exists(QSS_PATH):
        try:
            with open(QSS_PATH, 'r', encoding='utf-8') as f:
                dlg.setStyleSheet(f.read())
        except Exception:
            pass
    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(20, 20, 20, 20)
    # Custom titlebar with X button
    titlebar = QWidget()
    titlebar.setObjectName('customTitleBar')
    title_layout = QVBoxLayout(titlebar)
    title_layout.setContentsMargins(0, 0, 0, 0)
    close_btn = QPushButton('x')
    close_btn.setObjectName('customCloseBtn')
    close_btn.setFixedSize(44, 44)
    close_btn.clicked.connect(dlg.reject)
    title_layout.addWidget(close_btn, alignment=Qt.AlignRight)
    layout.addWidget(titlebar)
    # Main message
    label = QLabel(message or 'Maximum items reached. Hold or Pay to continue.')
    label.setAlignment(Qt.AlignCenter)
    label.setWordWrap(True)
    label.setStyleSheet('font-size: 18px; font-weight: bold; color: #d32f2f;')
    layout.addWidget(label)
    return dlg
