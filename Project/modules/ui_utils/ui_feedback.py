from PyQt5.QtWidgets import QLabel, QStatusBar
from PyQt5.QtCore import QTimer
import weakref

BARCODE_WARNING_TEXT = "Scan only in Product Code field"

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


class AutoClearingWarningLabel:
    def __init__(self, label: QLabel, message: str, duration: int = 3000, poll_interval: int = 150):
        self._label_ref = weakref.ref(label) if label is not None else lambda: None
        self._message = str(message or "")
        self._duration = max(0, int(duration))
        self._active = False
        self._poll_timer = QTimer(label)
        self._poll_timer.setInterval(max(50, int(poll_interval)))
        self._poll_timer.timeout.connect(self._sync)
        self._clear_timer = QTimer(label)
        self._clear_timer.setSingleShot(True)
        self._clear_timer.timeout.connect(self.clear)
        self._poll_timer.start()

    def _label(self):
        try:
            return self._label_ref()
        except Exception:
            return None

    def _sync(self) -> None:
        label = self._label()
        if label is None:
            self.stop()
            return
        try:
            current = str(label.text() or "")
        except RuntimeError:
            self.stop()
            return
        if current == self._message:
            try:
                label.setProperty("status", "warning")
                label.style().unpolish(label)
                label.style().polish(label)
            except Exception:
                pass
            if not self._active and self._duration > 0:
                self._active = True
                self._clear_timer.start(self._duration)
        elif self._active:
            self._active = False
            self._clear_timer.stop()

    def clear(self) -> bool:
        label = self._label()
        if label is None:
            self.stop()
            return False
        try:
            self._clear_timer.stop()
        except Exception:
            pass
        self._active = False
        try:
            if str(label.text() or "") == self._message:
                clear_status_label(label)
                return True
        except RuntimeError:
            self.stop()
            return False
        return False

    def stop(self) -> None:
        try:
            self._poll_timer.stop()
        except Exception:
            pass
        try:
            self._clear_timer.stop()
        except Exception:
            pass
        self._active = False


def create_auto_clearing_warning_label(label: QLabel, message: str, duration: int = 3000, poll_interval: int = 150) -> AutoClearingWarningLabel:
    return AutoClearingWarningLabel(label, message, duration=duration, poll_interval=poll_interval)

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