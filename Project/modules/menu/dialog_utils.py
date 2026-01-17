"""Shared dialog utilities for menu dialogs.

This module keeps existing helpers stable.
New helpers added below are opt-in and do not affect existing dialogs
unless they explicitly call them.
"""
import os
import traceback
from typing import Optional

from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QVBoxLayout

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


# =========================================================
# OPT-IN HELPERS (do not change existing behavior)
# =========================================================

def build_dialog_from_ui(
    ui_path: str,
    *,
    host_window=None,
    dialog_name: str = "Dialog",
    qss_path: Optional[str] = None,
    frameless: bool = True,
    application_modal: bool = True,
) -> Optional[QDialog]:
    """Standardized dialog builder.

    - Loads UI strictly (returns None on load failure)
    - Wraps non-QDialog roots inside a QDialog container
    - Applies common modality + frameless flags
    - Applies QSS best-effort

    Opt-in: existing dialogs can keep using uic.loadUi/load_ui_strict.
    """
    content = load_ui_strict(ui_path, host_window=host_window, dialog_name=dialog_name)
    if content is None:
        return None

    if isinstance(content, QDialog):
        dlg = content
    else:
        dlg = QDialog(host_window)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(content)

    try:
        if host_window is not None:
            dlg.setParent(host_window)
    except Exception:
        pass

    try:
        dlg.setModal(True)
        if application_modal:
            from PyQt5.QtCore import Qt
            dlg.setWindowModality(Qt.ApplicationModal)
        if frameless:
            from PyQt5.QtCore import Qt
            dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
    except Exception:
        pass

    if qss_path and os.path.exists(qss_path):
        try:
            with open(qss_path, 'r', encoding='utf-8') as f:
                dlg.setStyleSheet(f.read())
        except Exception as e:
            try:
                log_error(f"{dialog_name}: failed to load qss ({qss_path}): {e}")
            except Exception:
                pass

    return dlg


def require_widgets(
    root,
    required: dict,
    *,
    hard_fail: bool = True,
) -> dict:
    """Resolve required widgets by (type, objectName).

    required format: {"key": (WidgetClass, "objectName")}
    Returns: {"key": widget}

    If hard_fail=True and any required widget is missing, raises ValueError.
    """
    found = {}
    missing = []

    for key, spec in (required or {}).items():
        try:
            cls, obj_name = spec
        except Exception:
            cls, obj_name = None, None

        w = None
        try:
            if root is not None and cls is not None and obj_name:
                w = root.findChild(cls, obj_name)
        except Exception:
            w = None

        if w is None:
            missing.append(str(obj_name or key))
        else:
            found[key] = w

    if missing and hard_fail:
        raise ValueError(f"Missing required widgets: {', '.join(missing)}")

    return found
