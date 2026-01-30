import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui, 
    require_widgets, 
    set_dialog_main_status_max,
    set_dialog_error
)
from modules.ui_utils.error_logger import log_error

# Paths
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))
UI_PATH = os.path.join(_PROJECT_DIR, 'ui', 'cancel_sale.ui')
QSS_PATH = os.path.join(_PROJECT_DIR, 'assets', 'dialog.qss')

def launch_cancelsale_dialog(host_window):
    """
    Standardized Cancel Sale dialog.
    Returns a QDialog. If accepted, the caller clears the sales table.
    """
    # 1. Attempt standard pipeline load
    dlg = build_dialog_from_ui(
        UI_PATH, 
        host_window=host_window, 
        dialog_name='Cancel Sale', 
        qss_path=QSS_PATH
    )

    # --- BRANCH A: UI LOADED SUCCESSFULLY ---
    if dlg is not None:
        try:
            widgets = require_widgets(dlg, {
                'ok_btn': (QPushButton, 'btnCancelAllOk'),
                'cancel_btn': (QPushButton, 'btnCancelAllCancel'),
                'close_btn': (QPushButton, 'customCloseBtn')
            })

            def _handle_abort():
                set_dialog_main_status_max(dlg, "Sale cancellation aborted.", level='info')
                dlg.reject()

            def _handle_confirm():
                set_dialog_main_status_max(dlg, "Current sale cleared.", level='info')
                dlg.accept()

            widgets['ok_btn'].clicked.connect(_handle_confirm)
            widgets['cancel_btn'].clicked.connect(_handle_abort)
            widgets['close_btn'].clicked.connect(_handle_abort)
            
            # Safety: Focus CANCEL by default
            widgets['cancel_btn'].setFocus()
            return dlg
            
        except Exception as e:
            log_error(f"Cancel Sale UI mapping failed, falling back: {e}")
            # Fall through to programmatic fallback if widgets are missing/renamed

    # --- BRANCH B: PROGRAMMATIC FALLBACK (250x250) ---
    dlg = QDialog(host_window)
    dlg.setFixedSize(350, 250)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
    dlg.setModal(True)

    # Standard 16pt Bold Font
    f = QFont()
    f.setPointSize(16)
    f.setBold(True)
    dlg.setFont(f)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(10)

    # 1. Labels
    info = QLabel('CLEAR SALES TABLE?')
    info.setAlignment(Qt.AlignCenter)
    info.setStyleSheet("font-size: 16pt; color: #991b1b;; font-weight: bold;")
    layout.addWidget(info)

    info2 = QLabel("UI failure. Check Error log.")
    info2.setAlignment(Qt.AlignCenter)
    info2.setStyleSheet("font-size: 12pt; color: #4b5563; font-weight: bold;")
    layout.addWidget(info2)

    # 2. Buttons Row
    btn_row = QWidget()
    hl = QHBoxLayout(btn_row)
    hl.setContentsMargins(0, 0, 0, 0)
    
    btn_cancel = QPushButton('CANCEL')
    btn_ok = QPushButton('CLEAR ALL')

    # Standard fallback button styles
    btn_style = "font-size: 16pt; font-weight: bold; min-height: 60px; color: white; border-radius: 4px;"
    btn_cancel.setStyleSheet(f"background-color: #d32f2f; {btn_style}") # Red
    btn_ok.setStyleSheet(f"background-color: #388e3c; {btn_style}")     # Green

    hl.addWidget(btn_ok)
    hl.addWidget(btn_cancel)
    layout.addWidget(btn_row)

    # 3. Actions & Status Bar
    def _fallback_abort():
        set_dialog_main_status_max(dlg, "Sale cancellation aborted.", level='info')
        dlg.reject()

    def _fallback_confirm():
        set_dialog_main_status_max(dlg, "Current sale cleared.", level='info')
        dlg.accept()

    btn_cancel.clicked.connect(_fallback_abort)
    btn_ok.clicked.connect(_fallback_confirm)

    # Notify user that UI was missing via Main Window Status Bar
    set_dialog_error(dlg, "Error: Cancel Sale UI missing. Used emergency fallback.")
    
    btn_cancel.setFocus()
    return dlg