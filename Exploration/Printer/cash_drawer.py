"""Standalone GUI test for a network-printer cash drawer."""

from __future__ import annotations

import sys
import threading
import time

from escpos.printer import Network
from PyQt5.QtCore import QObject, QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


PRINTER_IP = "192.168.0.10"
PRINTER_PORT = 9100
CASH_DRAWER_PIN = 2
DEFAULT_TIMEOUT_SECONDS = 5.0


class DrawerTestSignals(QObject):
    completed = pyqtSignal(bool, str)


def send_cash_drawer_pulse(timeout_seconds: float) -> tuple[bool, str]:
    """Send the drawer pulse; this cannot detect its physical open state."""
    printer = None
    try:
        printer = Network(
            host=PRINTER_IP,
            port=PRINTER_PORT,
            timeout=timeout_seconds,
        )
        printer.cashdraw(CASH_DRAWER_PIN)
        return (
            True,
            f"Pulse sent to {PRINTER_IP}:{PRINTER_PORT} on pin {CASH_DRAWER_PIN}.\n"
            "Observe the cash drawer to confirm that it opened.",
        )
    except Exception as exc:
        return False, f"Cash drawer pulse failed:\n{exc}"
    finally:
        if printer is not None:
            try:
                printer.close()
            except Exception:
                pass


class CashDrawerTestDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Cash Drawer Timeout Test")
        self.setMinimumWidth(480)

        self.signals = DrawerTestSignals()
        self.signals.completed.connect(self._on_pulse_completed)
        self.test_started_at = 0.0
        self.test_duration = 0.0
        self.pulse_result = "Sending cash drawer pulse..."
        self.test_running = False

        self.timeout_input = QDoubleSpinBox()
        self.timeout_input.setRange(0.1, 3600.0)
        self.timeout_input.setDecimals(1)
        self.timeout_input.setSingleStep(1.0)
        self.timeout_input.setSuffix(" seconds")
        self.timeout_input.setValue(DEFAULT_TIMEOUT_SECONDS)

        self.test_button = QPushButton("Open Drawer and Start Timer")
        self.test_button.clicked.connect(self._start_test)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.reject)

        self.status_label = QLabel(
            "Enter a timeout, then start the test.\n"
            "Physical drawer position cannot be detected automatically."
        )
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(100)

        form = QFormLayout()
        form.addRow("Test timeout:", self.timeout_input)

        buttons = QHBoxLayout()
        buttons.addWidget(self.test_button)
        buttons.addWidget(self.close_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.status_label)
        layout.addLayout(buttons)

        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._update_countdown)

    def _start_test(self) -> None:
        if self.test_running:
            return

        self.test_duration = float(self.timeout_input.value())
        self.test_started_at = time.monotonic()
        self.pulse_result = "Sending cash drawer pulse..."
        self.test_running = True

        self.timeout_input.setEnabled(False)
        self.test_button.setEnabled(False)
        self.status_label.setText(
            f"{self.pulse_result}\n"
            f"Timer: {self.test_duration:.1f} seconds remaining"
        )
        self.timer.start()

        worker = threading.Thread(
            target=self._send_pulse_worker,
            args=(self.test_duration,),
            daemon=True,
        )
        worker.start()

    def _send_pulse_worker(self, timeout_seconds: float) -> None:
        ok, message = send_cash_drawer_pulse(timeout_seconds)
        self.signals.completed.emit(ok, message)

    def _on_pulse_completed(self, ok: bool, message: str) -> None:
        prefix = "SUCCESS" if ok else "FAILED"
        self.pulse_result = f"{prefix}: {message}"
        self._update_countdown()

    def _update_countdown(self) -> None:
        if not self.test_running:
            return

        elapsed = time.monotonic() - self.test_started_at
        remaining = max(0.0, self.test_duration - elapsed)
        if remaining > 0:
            self.status_label.setText(
                f"{self.pulse_result}\n\n"
                f"Timer: {remaining:.1f} seconds remaining"
            )
            return

        self.timer.stop()
        self.test_running = False
        self.status_label.setText(
            f"{self.pulse_result}\n\n"
            f"TIMER {self.test_duration:g} seconds up.\n"
            "Enter a new timeout and try again, or close the program."
        )
        self.timeout_input.setEnabled(True)
        self.test_button.setEnabled(True)
        self.timeout_input.setFocus()
        self.timeout_input.selectAll()


def main() -> int:
    app = QApplication(sys.argv)
    dialog = CashDrawerTestDialog()
    dialog.exec_()
    return 0


if __name__ == "__main__":
    sys.exit(main())
