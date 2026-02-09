"""payment_panel.py - Controller that wires the payment frame UI into the POS flow."""
import os
from PyQt5 import uic
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QPushButton, QLineEdit

from modules.ui_utils.error_logger import log_error


class PaymentPanel(QObject):
    payRequested = pyqtSignal(dict)
    paymentSuccess = pyqtSignal()

    def __init__(self, main_window, placeholder, ui_path):
        super().__init__()
        self._main_window = main_window
        self._placeholder = placeholder
        self.widget = uic.loadUi(ui_path)
        self._attach_to_placeholder()
        self._wire_buttons()

    def notify_payment_success(self) -> None:
        """Emit the payment success signal when payment processing completes."""
        self.paymentSuccess.emit()

    def _attach_to_placeholder(self) -> None:
        layout = self._placeholder.layout()
        if layout is None:
            layout = QVBoxLayout(self._placeholder)
            self._placeholder.setLayout(layout)
        try:
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(8)
        except Exception:
            pass
        layout.addWidget(self.widget)

    def _wire_buttons(self) -> None:
        pay_btn = self.widget.findChild(QPushButton, 'payPayOpsBtn')
        if pay_btn is not None:
            pay_btn.clicked.connect(self._on_pay_clicked)

    def _on_pay_clicked(self) -> None:
        payment_split = self._collect_payment_split()
        self.payRequested.emit(payment_split)

    def _collect_payment_split(self) -> dict:
        fields = {
            'cash': 'cashPayLineEdit',
            'nets': 'netsPayLineEdit',
            'voucher': 'voucherPayLineEdit',
            'paynow': 'paynowPayLineEdit',
        }
        payload = {}
        for key, field_name in fields.items():
            widget = self.widget.findChild(QLineEdit, field_name)
            payload[key] = self._parse_amount(widget.text() if widget is not None else '')
        return payload

    @staticmethod
    def _parse_amount(value: str) -> float:
        try:
            stripped = value.strip().replace('$', '')
            return float(stripped) if stripped else 0.0
        except ValueError:
            return 0.0


def setup_payment_panel(main_window, UI_DIR):
    payment_placeholder = getattr(main_window, 'paymentFrame', None)
    payment_ui = os.path.join(UI_DIR, 'payment_frame.ui')
    if payment_placeholder is None or not os.path.exists(payment_ui):
        return None
    try:
        return PaymentPanel(main_window, payment_placeholder, payment_ui)
    except Exception as e:
        log_error(f"Failed to initialize payment panel: {e}")
        return None
