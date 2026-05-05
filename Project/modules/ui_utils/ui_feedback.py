from PyQt5.QtWidgets import QLabel, QStatusBar
from PyQt5.QtCore import QTimer
import weakref


def _set_status_label_state(label: QLabel, message: str, state: str, duration: int = 3000) -> bool:
    if label is None:
        return False

    try:
        label.setText(message or "")
    except RuntimeError:
        return False

    try:
        label.setProperty("status", state)
    except RuntimeError:
        return False

    try:
        label.style().unpolish(label)
        label.style().polish(label)
    except RuntimeError:
        return False

    if duration > 0 and state in {"success", "warning", "error"}:
        ref = weakref.ref(label)

        def _clear_later():
            lbl = ref()
            if lbl is None:
                return
            clear_status_label(lbl)

        QTimer.singleShot(duration, _clear_later)

    return state == "success"

def set_status_label(label: QLabel, message: str, ok: bool, duration: int = 3000) -> bool:
    """Sets status message and triggers QSS property change."""
    status_val = "success" if ok else "error"
    return _set_status_label_state(label, message, status_val, duration)


def set_warning_status_label(label: QLabel, message: str, duration: int = 3000) -> bool:
    """Sets a warning message with warning styling."""
    return _set_status_label_state(label, message, "warning", duration)

def clear_status_label(label: QLabel) -> bool:
    """Clears text and resets the QSS property."""
    if label is None:
        return False
    try:
        label.setText("")
        label.setProperty("status", "none")
        label.style().unpolish(label)
        label.style().polish(label)
        return True
    except RuntimeError:
        # Safe no-op if the Qt object has been deleted.
        return False

# helper function to target the Main Window’s status bar

def show_main_status(parent, message: str, is_error: bool = False, duration: int = 3000):
    """Finds the Main Window status bar and shows a message."""
    from PyQt5.QtWidgets import QMainWindow
    
    # Walk up the parent tree to find the QMainWindow
    win = parent
    while win and not isinstance(win, QMainWindow):
        win = win.parent()
        
    if win and win.statusBar():
        color = "red" if is_error else "green"
        win.statusBar().setStyleSheet(f"color: {color};")
        win.statusBar().showMessage(message, duration)


def show_temp_status(status_bar: QStatusBar, message: str, duration_ms: int = 3000) -> None:
    """Small helper for transient messages on a QStatusBar."""
    if status_bar is None:
        return
    try:
        status_bar.showMessage(message or "", int(duration_ms))
    except Exception:
        pass