"""
Shared dialog utilities for menu dialogs.
"""
import os
import traceback
from typing import Optional

from PyQt5 import uic
from PyQt5.QtWidgets import QDialog

from modules.ui_utils.error_logger import log_error
from modules.ui_utils import ui_feedback


def set_dialog_main_status(dlg, message: str, *, is_error: bool = False, duration: int = 4000) -> None:
    """Standard way for dialogs to request a post-close StatusBar message.

    DialogWrapper will read these attributes after exec_() and display them.
    This allows CANCEL/Reject paths to still show *non-error* messages.
    """
    try:
        dlg.main_status_msg = str(message or '')
        dlg.main_status_is_error = bool(is_error)
        dlg.main_status_duration = int(duration)
    except Exception:
        pass


def set_dialog_info(dlg, message: str, *, duration: int = 4000) -> None:
    set_dialog_main_status(dlg, message, is_error=False, duration=duration)


def set_dialog_error(dlg, message: str, *, duration: int = 5000) -> None:
    set_dialog_main_status(dlg, message, is_error=True, duration=duration)

def center_dialog_relative_to(dlg: QDialog, host) -> None:
    """Center dlg relative to host window."""
    try:
        mw = host.frameGeometry().width(); mh = host.frameGeometry().height()
        mx = host.frameGeometry().x();     my = host.frameGeometry().y()
        dw = dlg.width();                  dh = dlg.height()
        dlg.move(mx + (mw - dw)//2, my + (mh - dh)//2)
    except Exception:
        pass


def report_to_statusbar(host_window, message: str, *, is_error: bool = True, duration: int = 4000) -> None:
    """Best-effort: show a transient message on the MainWindow status bar."""
    try:
        ui_feedback.show_main_status(host_window, message, is_error=is_error, duration=duration)
    except Exception:
        pass


def load_ui_strict(ui_path: str, *, host_window=None, dialog_name: str = "Dialog") -> Optional[object]:
    """Load a .ui file.

    Behavior:
    - If the .ui file is missing or fails to load, logs an error and (optionally)
      sends a message to the main window StatusBar.
    - Returns the loaded widget on success, otherwise None.
    """
    if not ui_path or not os.path.exists(ui_path):
        msg = f"{dialog_name}: UI not found ({ui_path})"
        try:
            log_error(msg)
        except Exception:
            pass
        if host_window is not None:
            report_to_statusbar(host_window, f"Error: {msg}", is_error=True)
        return None

    try:
        return uic.loadUi(ui_path)
    except Exception as e:
        msg = f"{dialog_name}: failed to load UI ({ui_path}): {e}"
        try:
            log_error(msg)
        except Exception:
            pass
        if host_window is not None:
            report_to_statusbar(host_window, f"Error: {dialog_name} UI load failed", is_error=True)
        return None


def report_exception(host_window, where: str, exc: Exception, *, user_message: Optional[str] = None, duration: int = 5000) -> None:
    """Standardized exception routing.

    - Writes details to error.log (including traceback when available)
    - Shows a short message on the MainWindow StatusBar (best-effort)

    This is intended for DB/Cache/UI failures where the user needs a quick hint
    but full details should go to logs.
    """
    where_txt = (where or 'Error').strip()
    try:
        tb = traceback.format_exc()
    except Exception:
        tb = ''

    try:
        msg = f"{where_txt}: {exc!r}"
        if tb and 'Traceback' in tb:
            msg = msg + "\n" + tb
        log_error(msg)
    except Exception:
        pass

    if host_window is not None:
        short = (user_message or f"Error: {where_txt}").strip()
        report_to_statusbar(host_window, short, is_error=True, duration=duration)

    return None
