from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QComboBox, QPushButton
import os
from modules.ui_utils.error_logger import log_error

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(THIS_DIR))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
QSS_PATH = os.path.join(ASSETS_DIR, 'menu.qss')


# Import greeting strings from config
from config import GREETING_STRINGS

def open_greeting_dialog(parent=None):
    """Open the Greeting message selection dialog.
    
    Selected greeting stored in dlg.greeting_result attribute (or None if cancelled).
    
    Args:
        parent: Parent window instance
    
    Returns:
        QDialog instance ready for DialogWrapper.open_dialog_scanner_blocked() to execute
    """
    ui_path = os.path.join(UI_DIR, 'greeting_menu.ui')
    if not os.path.exists(ui_path):
        try:
            log_error(f"greeting_menu.ui not found at {ui_path}")
        except Exception:
            pass
        raise FileNotFoundError(f'greeting_menu.ui not found at {ui_path}')
    dlg = uic.loadUi(ui_path)
    from PyQt5.QtCore import Qt
    dlg.setModal(True)
    
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
    
    # Apply stylesheet
    if os.path.exists(QSS_PATH):
        try:
            with open(QSS_PATH, 'r', encoding='utf-8') as f:
                dlg.setStyleSheet(f.read())
        except Exception as e:
            try:
                log_error(f"Failed to load menu.qss: {e}")
            except Exception:
                pass
    
    all_widgets = dlg.findChildren(QComboBox)
    combo = all_widgets[0] if all_widgets else None
    if combo is not None:
        combo.clear()
        combo.addItems(GREETING_STRINGS)
        default_index = GREETING_STRINGS.index('Thanks for shopping with us!')
        combo.setCurrentIndex(default_index)
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
    
    # Store selected greeting in dialog attribute for retrieval after execution
    dlg.greeting_result = None
    def _store_greeting():
        if dlg.result() == QDialog.Accepted and combo:
            dlg.greeting_result = combo.currentText()
    dlg.finished.connect(_store_greeting)
    
    # Return QDialog for DialogWrapper to execute

    combo.setFocus()
    return dlg
