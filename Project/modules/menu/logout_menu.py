import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QWidget, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui, 
    require_widgets, 
    set_dialog_main_status_max,
    set_dialog_error
)

# Paths
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))
UI_PATH = os.path.join(_PROJECT_DIR, 'ui', 'logout_menu.ui')
QSS_PATH = os.path.join(_PROJECT_DIR, 'assets', 'dialog.qss')

def launch_logout_dialog(host_window):
    """
    Logout dialog with standardized 250x250 high-visibility fallback.
    """
    # 1. Attempt standard load
    dlg = build_dialog_from_ui(UI_PATH, host_window=host_window, dialog_name='Logout', qss_path=QSS_PATH)

    # --- BRANCH A: UI LOADED SUCCESSFULLY ---
    if dlg is not None:
        try:
            widgets = require_widgets(dlg, {
                'ok_btn': (QPushButton, 'btnLogoutOk'),
                'cancel_btn': (QPushButton, 'btnLogoutCancel'),
                'close_btn': (QPushButton, 'customCloseBtn')
            })
            def _handle_cancel():
                set_dialog_main_status_max(dlg, "Logout cancelled.", level='info')
                dlg.reject()

            widgets['ok_btn'].clicked.connect(dlg.accept)
            widgets['cancel_btn'].clicked.connect(_handle_cancel)
            widgets['close_btn'].clicked.connect(_handle_cancel)
            widgets['cancel_btn'].setFocus()
            return dlg
        except Exception:
            pass # Fall through to Branch B if mapping fails

    # --- BRANCH B: STANDARDIZED FALLBACK (250x250) ---
    dlg = QDialog(host_window)
    dlg.setFixedSize(350, 350)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
    dlg.setModal(True)

    # Apply 16pt Bold font to entire dialog
    f = QFont()
    f.setPointSize(16)
    f.setBold(True)
    dlg.setFont(f)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(10)

    # 1. Labels (Centered & Bold)
    info = QLabel('Logout Failed to load.')
    info.setAlignment(Qt.AlignCenter)
    info.setStyleSheet("font-size: 16pt; color: #991b1b;; font-weight: bold;")
    layout.addWidget(info)

    info2 = QLabel("Check Error log.")
    info2.setAlignment(Qt.AlignCenter)
    info2.setStyleSheet("font-size: 12pt; color: #4b5563; font-weight: bold;")
    layout.addWidget(info2)

    # 2. Buttons Row
    btn_row = QWidget()
    hl = QHBoxLayout(btn_row)
    hl.setContentsMargins(0, 0, 0, 0)
    
    btn_ok = QPushButton('LOGOUT ?')
    btn_cancel = QPushButton('CANCEL')

    # Apply standard fallback button styles
    btn_style = "font-size: 16pt; font-weight: bold; min-height: 60px; color: white; border-radius: 4px;"
    btn_cancel.setStyleSheet(f"background-color: #d32f2f; {btn_style}")
    btn_ok.setStyleSheet(f"background-color: #388e3c; {btn_style}")

    hl.addWidget(btn_ok)
    hl.addWidget(btn_cancel)
    layout.addWidget(btn_row)

    # 3. Actions & Status Bar Propagation
    def _fallback_cancel():
        set_dialog_main_status_max(dlg, "Logout cancelled (Fallback mode).", level='info')
        dlg.reject()

    btn_cancel.clicked.connect(_fallback_cancel)
    btn_ok.clicked.connect(dlg.accept)

    # Propagate the missing UI error for post-close visibility
    set_dialog_error(dlg, "Error: Logout UI missing. Used emergency fallback.")

    btn_cancel.setFocus()
    return dlg

# Alias
open_logout_dialog = launch_logout_dialog