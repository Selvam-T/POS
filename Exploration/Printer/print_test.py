"""Standalone ESC/POS font test for the network receipt printer."""

from __future__ import annotations

import sys

from escpos.printer import Network
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QDialog, QLabel, QPushButton, QVBoxLayout


PRINTER_IP = "192.168.0.10"
PRINTER_PORT = 9100
TIMEOUT_SECONDS = 5

RECEIPT_TEST_WIDTHS = (50, 49, 48, 47, 46)
RECEIPT_QTY_WIDTH = 9
RECEIPT_ITEM_AMOUNT_WIDTH = 8
RECEIPT_ITEM_PRICE_WIDTH = 6
RECEIPT_GAP = 1
RECEIPT_PRINTER_FONT = "a"
RECEIPT_TEST_LINES_PER_WIDTH = 1


def _print_line(printer: Network, *, font: str, width: int, height: int, text: str) -> None:
    printer.set(align="left", font=font, width=width, height=height)
    printer.text(text + "\n")


def _receipt_margin_test_line(receipt_width: int) -> str:
    """Build one four-column row whose length is exactly receipt_width."""
    product_width = receipt_width - (
        3 * RECEIPT_GAP
        + RECEIPT_QTY_WIDTH
        + RECEIPT_ITEM_PRICE_WIDTH
        + RECEIPT_ITEM_AMOUNT_WIDTH
    )
    if product_width < 1:
        raise ValueError(f"Receipt width {receipt_width} is too small for the configured columns.")

    product = f"Test MARGIN {receipt_width}"[:product_width].ljust(product_width)
    qty = "1 ea"[:RECEIPT_QTY_WIDTH].ljust(RECEIPT_QTY_WIDTH)
    price = "6.80"[-RECEIPT_ITEM_PRICE_WIDTH:].rjust(RECEIPT_ITEM_PRICE_WIDTH)
    total = "6.80"[-RECEIPT_ITEM_AMOUNT_WIDTH:].rjust(RECEIPT_ITEM_AMOUNT_WIDTH)
    gap = " " * RECEIPT_GAP
    line = gap.join((product, qty, price, total))

    if len(line) != receipt_width:
        raise AssertionError(
            f"Margin test line is {len(line)} characters; expected {receipt_width}."
        )
    return line


def _print_receipt_margin_tests(printer: Network) -> None:
    printer.set(
        align="left",
        font=RECEIPT_PRINTER_FONT,
        width=1,
        height=1,
    )
    printer.text("\nRECEIPT MARGIN TEST - FONT A\n")

    for receipt_width in RECEIPT_TEST_WIDTHS:
        #printer.text(f"\nWIDTH {receipt_width} ({RECEIPT_TEST_LINES_PER_WIDTH} ROWS)\n")
        test_line = _receipt_margin_test_line(receipt_width)
        for _ in range(RECEIPT_TEST_LINES_PER_WIDTH):
            printer.text(test_line + "\n")


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
            font="a",
            width=2,
            height=2,
            text="Line 2 Test PRINTING font A double $ 999.99",
        )
        _print_line(
            printer,
            font="a",
            width=1,
            height=2,
            text="Line 3 Test PRINTING font A Height $ 999.99",
        )
        _print_line(
            printer,
            font="a",
            width=2,
            height=1,
            text="Line 4 Test PRINTING font A width $ 999.99",
        )

        printer.text("\n")

        _print_line(
            printer,
            font="b",
            width=1,
            height=1,
            text="Line 5 Test PRINTING font B $ 999.99",
        )
        _print_line(
            printer,
            font="b",
            width=2,
            height=2,
            text="Line 6 Test PRINTING font B double $ 999.99",
        )
        _print_line(
            printer,
            font="b",
            width=1,
            height=2,
            text="Line 7 Test PRINTING font B Height $ 999.99",
        )
        _print_line(
            printer,
            font="b",
            width=2,
            height=1,
            text="Line 8 Test PRINTING font B width $ 999.99",
        )

        _print_line(
                    printer,
                    font="a",
                    width=1,
                    height=1,
                    text="\nAAAAA BBBBB CCCCC DDDDD EEEEE FFFFF GGGGG HHHHH IIIII JJJJJ KKKKK",
        )

        _print_line(
                    printer,
                    font="a",
                    width=1,
                    height=1,
                    text="aaaaa bbbbb ccccc ddddd eeeee fffff ggggg hhhhh iiiii jjjjj kkkkk",
        )

        _print_receipt_margin_tests(printer)

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
