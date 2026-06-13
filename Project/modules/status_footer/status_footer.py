from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer, QFileSystemWatcher
from PyQt5.QtWidgets import QLabel, QMainWindow, QPushButton, QStatusBar, QWidget

from modules.ui_utils.error_logger import LOG_PATH


class MainStatusFooterController(QWidget):
    def __init__(self):
        super().__init__()
        self.root = None
        self.statusbar = None
        self.statusMessageLabel = None
        self.loggedInUserLabel = None
        self.errorLogFrame = None
        self.errorLogStatusLabel = None
        self.exportErrorLogBtn = None
        self.clearErrorLogBtn = None
        self._statusbar_current_message = ""
        self._statusbar_clear_timer = None
        self._error_log_watcher = None
        self._error_log_refresh_timer = None
        self._error_log_poll_timer = None
        self._last_error_log_signature = None
        self._last_has_error = None

    def bind(self, root: QMainWindow):
        self.root = root
        self.setParent(root)
        self.statusbar = root.findChild(QStatusBar, 'statusbar')
        self.loggedInUserLabel = root.findChild(QLabel, 'loggedInUserLabel')
        self.errorLogFrame = root.findChild(QWidget, 'errorLogFrame')
        self.errorLogStatusLabel = root.findChild(QLabel, 'errorLogStatusLabel')
        self.exportErrorLogBtn = root.findChild(QPushButton, 'exportErrorLogBtn')
        self.clearErrorLogBtn = root.findChild(QPushButton, 'clearErrorLogBtn')

        self._setup_statusbar_message_area()
        self._setup_error_log_controls()
        self.set_username(getattr(root, 'current_username', ''))
        return self

    def set_username(self, username: str) -> None:
        try:
            if self.loggedInUserLabel is None:
                return
            value = str(username or '').strip()
            self.loggedInUserLabel.setText(f"Logged in: {value}" if value else "Logged in: -")
        except Exception:
            pass

    def _setup_statusbar_message_area(self) -> None:
        try:
            status_bar = self.statusbar
            if status_bar is None:
                return

            status_bar.setSizeGripEnabled(False)
            self._statusbar_current_message = ""
            self._statusbar_clear_timer = QTimer(self)
            self._statusbar_clear_timer.setSingleShot(True)
            self._statusbar_clear_timer.timeout.connect(lambda: status_bar.clearMessage())

            message_label = QLabel("", status_bar)
            message_label.setObjectName("statusMessageLabel")
            message_label.setAlignment(Qt.AlignCenter)
            message_label.setMinimumWidth(0)
            status_bar.addPermanentWidget(message_label, 1)
            self.statusMessageLabel = message_label
            if self.root is not None:
                self.root.statusMessageLabel = message_label

            def show_message(message="", timeout=0):
                text = str(message or "")
                self._statusbar_current_message = text
                message_label.setText(text)
                try:
                    status_bar.messageChanged.emit(text)
                except Exception:
                    pass
                try:
                    self._statusbar_clear_timer.stop()
                    if int(timeout or 0) > 0:
                        self._statusbar_clear_timer.start(int(timeout))
                except Exception:
                    pass

            def clear_message():
                if not self._statusbar_current_message:
                    return
                try:
                    self._statusbar_clear_timer.stop()
                except Exception:
                    pass
                self._statusbar_current_message = ""
                message_label.clear()
                try:
                    status_bar.messageChanged.emit("")
                except Exception:
                    pass

            def current_message():
                return self._statusbar_current_message

            status_bar.showMessage = show_message
            status_bar.clearMessage = clear_message
            status_bar.currentMessage = current_message
        except Exception:
            pass

    def _setup_error_log_controls(self) -> None:
        try:
            self._ensure_error_log_file()
            self._error_log_watcher = QFileSystemWatcher(self)
            self._watch_error_log_path()
            self._error_log_watcher.fileChanged.connect(self._on_error_log_file_changed)
            self._error_log_watcher.directoryChanged.connect(self._on_error_log_file_changed)
            self._error_log_refresh_timer = QTimer(self)
            self._error_log_refresh_timer.setSingleShot(True)
            self._error_log_refresh_timer.timeout.connect(self.refresh_error_log_state)
            self._error_log_poll_timer = QTimer(self)
            self._error_log_poll_timer.timeout.connect(self._poll_error_log_state)
            self._error_log_poll_timer.start(1000)

            if self.exportErrorLogBtn is not None:
                self.exportErrorLogBtn.clicked.connect(self._export_error_log_text)
            if self.clearErrorLogBtn is not None:
                self.clearErrorLogBtn.clicked.connect(self._clear_error_log)

            self.refresh_error_log_state()
        except Exception:
            pass

    def _ensure_error_log_file(self) -> None:
        try:
            log_path = Path(LOG_PATH)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.touch(exist_ok=True)
        except Exception:
            pass

    def _watch_error_log_path(self) -> None:
        try:
            watcher = self._error_log_watcher
            if watcher is None:
                return
            self._ensure_error_log_file()
            log_path = str(Path(LOG_PATH))
            log_dir = str(Path(LOG_PATH).parent)
            if log_path not in watcher.files():
                watcher.addPath(log_path)
            if log_dir not in watcher.directories():
                watcher.addPath(log_dir)
        except Exception:
            pass

    def _error_log_text(self) -> str:
        try:
            with open(LOG_PATH, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception:
            return ""

    def _error_log_has_content(self) -> bool:
        try:
            return Path(LOG_PATH).stat().st_size > 0
        except Exception:
            return False

    def _error_log_signature(self):
        try:
            stat = Path(LOG_PATH).stat()
            return stat.st_size, stat.st_mtime_ns
        except Exception:
            return None

    def _poll_error_log_state(self) -> None:
        signature = self._error_log_signature()
        if signature == self._last_error_log_signature:
            return
        self.refresh_error_log_state()

    def refresh_error_log_state(self) -> None:
        try:
            has_error = self._error_log_has_content()
            self._last_error_log_signature = self._error_log_signature()

            if self.errorLogStatusLabel is not None:
                self.errorLogStatusLabel.setText("Error Log!" if has_error else "No Error")

            if self._last_has_error != has_error:
                for widget in (
                    self.errorLogFrame,
                    self.errorLogStatusLabel,
                    self.exportErrorLogBtn,
                    self.clearErrorLogBtn,
                ):
                    if widget is not None:
                        widget.setProperty("hasError", has_error)
                        try:
                            widget.style().unpolish(widget)
                            widget.style().polish(widget)
                        except Exception:
                            pass
                self._last_has_error = has_error

            for button in (self.exportErrorLogBtn, self.clearErrorLogBtn):
                if button is not None:
                    button.setEnabled(has_error)
                    button.setFocusPolicy(Qt.StrongFocus if has_error else Qt.NoFocus)
                    button.setToolTip("" if has_error else "No error log entries")
        except Exception:
            pass

    def _on_error_log_file_changed(self, *_args) -> None:
        self._watch_error_log_path()
        self._schedule_error_log_refresh()

    def _schedule_error_log_refresh(self, delay_ms: int = 50) -> None:
        try:
            if self._error_log_refresh_timer is not None:
                self._error_log_refresh_timer.start(int(delay_ms))
            else:
                QTimer.singleShot(int(delay_ms), self.refresh_error_log_state)
        except Exception:
            pass

    def _export_error_log_text(self) -> None:
        try:
            text = self._error_log_text()
            if not text.strip():
                self.refresh_error_log_state()
                self._show_status("No error log entries to export.", 3000)
                return

            export_dir = Path(
                getattr(self, '_error_log_export_root', Path.home() / "POS_Exports" / "Error_Log")
            )
            export_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%d%b%Y_%H-%M-%S").lower()
            out_path = export_dir / f"error_log_{stamp}.txt"
            out_path.write_text(
                "Selvam POS Error Log\n"
                f"Exported: {datetime.now().strftime('%d %b %Y, %I:%M:%S %p')}\n"
                f"Source: {LOG_PATH}\n\n"
                f"{text}",
                encoding='utf-8',
            )

            self.refresh_error_log_state()
            self._show_status(f"Error log saved to {export_dir}", 4000)
        except Exception as exc:
            try:
                from modules.ui_utils.error_logger import log_error_message
                log_error_message(f"Error log export failed: {exc}")
            except Exception:
                pass
            self._show_status("Error: Unable to export error log.", 5000)
        finally:
            self._watch_error_log_path()
            self._schedule_error_log_refresh()

    def _clear_error_log(self) -> None:
        try:
            with open(LOG_PATH, 'w', encoding='utf-8') as f:
                f.truncate(0)
            self.refresh_error_log_state()
            self._show_status("Error log cleared.", 4000)
            self._watch_error_log_path()
            self._schedule_error_log_refresh()
        except Exception as exc:
            try:
                from modules.ui_utils.error_logger import log_error_message
                log_error_message(f"Error log clear failed: {exc}")
            except Exception:
                pass
            self._watch_error_log_path()
            self._schedule_error_log_refresh()
            self._show_status("Error: Unable to clear error log.", 5000)

    def _show_status(self, message: str, timeout: int) -> None:
        try:
            if self.root is not None:
                self.root.statusBar().showMessage(message, timeout)
            elif self.statusbar is not None:
                self.statusbar.showMessage(message, timeout)
        except Exception:
            pass
