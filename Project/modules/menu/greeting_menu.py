from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QComboBox, QPushButton
import os
from modules.ui_utils.error_logger import log_error
from modules.ui_utils import ui_feedback
from modules.ui_utils.dialog_utils import set_dialog_main_status, build_dialog_from_ui, build_error_fallback_dialog

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(THIS_DIR))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
QSS_PATH = os.path.join(ASSETS_DIR, 'dialog.qss')


# Import greeting strings from config
import config

def launch_greeting_dialog(parent=None):
    """Open greeting selection dialog; result stored in `dlg.greeting_result`.
    """
    ui_path = os.path.join(UI_DIR, 'greeting_menu.ui')
    # Use the shared dialog builder so a standardized fallback is returned on failure
    dlg = build_dialog_from_ui(ui_path, host_window=parent, dialog_name='Greeting menu', qss_path=QSS_PATH)
    if not dlg:
        return build_error_fallback_dialog(parent, 'Greeting menu', QSS_PATH)
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
                log_error(f"Failed to load dialog.qss: {e}")
            except Exception:
                pass
    
    all_widgets = dlg.findChildren(QComboBox)
    combo = all_widgets[0] if all_widgets else None
    if combo is not None:
        combo.clear()
        combo.addItems(config.GREETING_STRINGS)
        default_greeting = config.GREETING_SELECTED or 'Thanks for shopping with us!'
        if default_greeting in config.GREETING_STRINGS:
            combo.setCurrentText(default_greeting)
        else:
            combo.setCurrentIndex(0)
    # Wire up close button
    close_btn: QPushButton = dlg.findChild(QPushButton, 'customCloseBtn')
    if close_btn:
        close_btn.clicked.connect(dlg.reject)
    # Wire up Ok/Cancel
    ok_btn: QPushButton = dlg.findChild(QPushButton, 'btnGreetOk')
    cancel_btn: QPushButton = dlg.findChild(QPushButton, 'btnGreetCancel')
    # Handlers to show main status and then close the dialog
    if ok_btn:
        def _on_ok():
            try:
                set_dialog_main_status(dlg, 'New greeting selected', is_error=False)
            except Exception:
                pass
            dlg.accept()
        ok_btn.clicked.connect(_on_ok)
    if cancel_btn:
        def _on_cancel():
            try:
                set_dialog_main_status(dlg, 'Greeting closed', is_error=False)
            except Exception:
                pass
            dlg.reject()
        cancel_btn.clicked.connect(_on_cancel)
    
    # Store selected greeting in dialog attribute for retrieval after execution
    dlg.greeting_result = None
    # Store selected greeting when dialog finishes
    def _store_greeting():
        if dlg.result() == QDialog.Accepted and combo:
            dlg.greeting_result = combo.currentText()
    dlg.finished.connect(_store_greeting)
    
    # After a selection, jump focus to the Ok button
    if combo is not None and ok_btn is not None:
        try:
            combo.activated.connect(lambda *a: ok_btn.setFocus())
        except Exception:
            try:
                combo.currentIndexChanged.connect(lambda *a: ok_btn.setFocus())
            except Exception:
                pass

    combo.setFocus()
    return dlg
