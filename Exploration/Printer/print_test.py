"""Standalone ESC/POS font test for the network receipt printer."""

from __future__ import annotations

import sys

from escpos.printer import Network
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QDialog, QLabel, QPushButton, QVBoxLayout


PRINTER_IP = "192.168.0.10"
PRINTER_PORT = 9100
TIMEOUT_SECONDS = 5


def _print_line(printer: Network, *, font: str, width: int, height: int, text: str) -> None:
    printer.set(align="left", font=font, width=width, height=height)
    printer.text(text + "\n")


def send_print_test() -> tuple[bool, str]:
    printer = None
    try:
        printer = Network(host=PRINTER_IP, port=PRINTER_PORT, timeout=TIMEOUT_SECONDS)

        _print_line(
            printer,
            font="a",
            width=1,
            height=1,
            text="Line 1 Test PRINTING font A $ 999.99",
        )
        _print_line(
            printer,
            font="b",
            width=1,
            height=1,
            text="Line 2 Test PRINTING font B $ 999.99",
        )
        _print_line(
            printer,
            font="a",
            width=2,
            height=2,
            text="Line 3 Test PRINTING font A double $ 999.99",
        )
        _print_line(
            printer,
            font="b",
            width=2,
            height=2,
            text="Line 4 Test PRINTING font B double $ 999.99",
        )
        _print_line(
            printer,
            font="a",
            width=1,
            height=2,
            text="Line 5 Test PRINTING font A Height $ 999.99",
        )
        _print_line(
            printer,
            font="b",
            width=1,
            height=2,
            text="Line 6 Test PRINTING font B Height $ 999.99",
        )
        _print_line(
            printer,
            font="a",
            width=2,
            height=1,
            text="Line 7 Test PRINTING font A width $ 999.99",
        )
        _print_line(
            printer,
            font="b",
            width=2,
            height=1,
            text="Line 8 Test PRINTING font B width $ 999.99",
        )

        printer.set(align="left", font="a", width=1, height=1)
        printer.text("\n")
        printer.cut()
        return True, f"Print test sent to {PRINTER_IP}:{PRINTER_PORT}."
    except Exception as exc:
        return False, f"Print test failed:\n{exc}"
    finally:
        if printer is not None:
            try:
                printer.close()
            except Exception:
                pass


class PrintTestDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Printer Font Test")
        self.setMinimumWidth(420)

        self.status_label = QLabel("Sending print test...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)

        self.close_button = QPushButton("Close")
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.close_button)

        QTimer.singleShot(100, self._run_print_test)

    def _run_print_test(self) -> None:
        ok, message = send_print_test()
        self.status_label.setText(message)
        self.close_button.setEnabled(True)
        self.close_button.setFocus()
        if not ok:
            self.setWindowTitle("Printer Font Test Failed")


def main() -> int:
    app = QApplication(sys.argv)
    dialog = PrintTestDialog()
    dialog.exec_()
    return 0


if __name__ == "__main__":
    sys.exit(main())
