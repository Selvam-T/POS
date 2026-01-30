"""Shared dialog utilities.

This module centralizes common helpers used by dialog controllers across the app
(menu dialogs and sales dialogs).

Existing helpers are kept stable.
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
        # Defer user notification to the wrapper when possible so it isn't
        # hidden under a modal overlay.
        if host_window is not None:
            try:
                host_window._pending_main_status_msg = f"Error: {msg}"
                host_window._pending_main_status_is_error = True
                host_window._pending_main_status_duration = 6000
            except Exception:
                pass
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
            try:
                host_window._pending_main_status_msg = f"Error: {dialog_name} UI load failed"
                host_window._pending_main_status_is_error = True
                host_window._pending_main_status_duration = 6000
            except Exception:
                pass
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


def _status_severity(*, level: str, is_error: Optional[bool] = None) -> int:
    """Internal: map status level to a comparable severity."""
    lvl = (level or '').strip().lower()
    if lvl == 'error':
        return 2
    if lvl == 'warning':
        return 1
    if is_error:
        return 2
    return 0


def set_dialog_main_status_max(
    dlg,
    message: str,
    *,
    level: str = 'info',
    is_error: Optional[bool] = None,
    duration: int = 4000,
) -> None:
    """Set dialog's post-close StatusBar message only if it is >= current severity.

    This is opt-in and does not change existing behavior unless a dialog calls it.
    Precedence rule:
    - error > warning > info
    """
    if dlg is None:
        return

    try:
        new_sev = _status_severity(level=level, is_error=is_error)
    except Exception:
        new_sev = 0

    cur_sev = None
    try:
        cur_sev = getattr(dlg, '_main_status_severity', None)
    except Exception:
        cur_sev = None

    if cur_sev is None:
        try:
            cur_is_error = bool(getattr(dlg, 'main_status_is_error', False))
            cur_msg = getattr(dlg, 'main_status_msg', None)
            cur_sev = 2 if (cur_is_error and cur_msg) else (0 if cur_msg else 0)
        except Exception:
            cur_sev = 0

    if int(new_sev) < int(cur_sev):
        return

    try:
        dlg._main_status_severity = int(new_sev)
    except Exception:
        pass

    if is_error is None:
        is_error = (str(level or '').strip().lower() == 'error')

    set_dialog_main_status(dlg, message, is_error=bool(is_error), duration=duration)


def log_exception_only(where: str, exc: Exception) -> None:
    """Log exception details to error.log without touching the StatusBar."""
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


def report_exception_post_close(
    dlg,
    where: str,
    exc: Exception,
    *,
    user_message: str,
    level: str = 'error',
    duration: int = 5000,
) -> None:
    """Log exception details and set a post-close StatusBar message intent on dlg.

    Use this for failures that happen during modal dialogs where we don't want
    to show StatusBar messages while the modal is still open.
    """
    log_exception_only(where, exc)
    try:
        set_dialog_main_status_max(dlg, (user_message or f"Error: {where}").strip(), level=level, duration=duration)
    except Exception:
        pass


def log_and_set_post_close(
    dlg,
    where: str,
    details: str,
    *,
    user_message: str,
    level: str = 'error',
    duration: int = 5000,
) -> None:
    """Log a handled (non-exception) failure and set post-close StatusBar intent."""
    try:
        log_error(f"{(where or 'Error').strip()}: {details}")
    except Exception:
        pass
    try:
        set_dialog_main_status_max(dlg, (user_message or f"Error: {where}").strip(), level=level, duration=duration)
    except Exception:
        pass


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

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

def build_error_fallback_dialog(host_window, dialog_name: str, qss_path: str = None) -> QDialog:
    """
    Standardized 'Emergency' dialog (250x250).
    Bold 16pt font. Propagates error to MainWindow Status Bar on close.
    """
    dlg = QDialog(host_window)
    dlg.setObjectName("FallbackErrorDialog")
    dlg.setModal(True)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
    
    # 1. Size Constraints
    dlg.setFixedSize(250, 250)
    
    # 2. Font Setup (16pt Bold)
    f = QFont()
    f.setPointSize(16)
    f.setBold(True)
    dlg.setFont(f)

    # 3. Apply QSS
    if qss_path and os.path.exists(qss_path):
        try:
            with open(qss_path, 'r', encoding='utf-8') as f_qss:
                dlg.setStyleSheet(f_qss.read())
        except Exception: pass

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(10)

    # 4. Error Message
    # Using inline style to ensure Bold 16pt is strictly followed
    msg = QLabel(f"{dialog_name}<br>failed to load.")
    msg.setWordWrap(True)
    msg.setAlignment(Qt.AlignCenter)
    msg.setStyleSheet("font-size: 16pt; font-weight: bold; color: #991b1b;")
    layout.addWidget(msg)

    sub_msg = QLabel("Check error log.")
    sub_msg.setAlignment(Qt.AlignCenter)
    sub_msg.setStyleSheet("font-size: 12pt; font-weight: bold; color: #4b5563;")
    layout.addWidget(sub_msg)

    # 5. Close Button
    btn_close = QPushButton("CLOSE")
    btn_close.setMinimumHeight(60) # Larger hit area for 250x250 window
    btn_close.setObjectName("errorOk") # Triggers QSS styling
    btn_close.setStyleSheet("font-size: 16pt; font-weight: bold;")
    btn_close.clicked.connect(dlg.reject)
    layout.addWidget(btn_close)

    # 6. Status Bar Propagation
    # This prepares the message that the Main Window will show AFTER this dialog closes.
    from modules.ui_utils.dialog_utils import set_dialog_error
    set_dialog_error(dlg, f"Error: Standard UI for {dialog_name} is missing or corrupted.")

    btn_close.setFocus()
    return dlg