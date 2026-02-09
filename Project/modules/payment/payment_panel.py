"""payment_panel.py - Controller that wires the payment frame UI into the POS flow."""
import os
from PyQt5 import uic
from PyQt5.QtCore import QObject, pyqtSignal, Qt, QEvent
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QFrame

from modules.ui_utils import ui_feedback
from modules.ui_utils.error_logger import log_error


class PaymentPanel(QObject):
    payRequested = pyqtSignal(dict)
    paymentSuccess = pyqtSignal()

    def __init__(self, main_window, placeholder, ui_path):
        super().__init__()
        self._main_window = main_window
        self._placeholder = placeholder
        self.widget = uic.loadUi(ui_path)
        self._widgets = {}
        self._last_pay_select_method = None
        self._last_unalloc = 0.0
        self._has_balance_error = False
        self._has_unalloc_warning = False
        self._attach_to_placeholder()
        self._cache_widgets()
        self._wire_buttons()
        self._wire_inputs()
        self.clear_payment_frame()

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
            pay_btn.clicked.connect(self.handle_pay_clicked)

        reset_btn = self.widget.findChild(QPushButton, 'resetPayOpsBtn')
        if reset_btn is not None:
            reset_btn.clicked.connect(self.reset_payment_grid_to_default)

        # Note: printPayOpsBtn exists in UI; wiring is intentionally omitted until print workflow is defined.

        pay_select_buttons = {
            'cash': 'cashPaySlcBtn',
            'nets': 'netsPaySlcBtn',
            'paynow': 'paynowPaySlcBtn',
            'voucher': 'voucherPaySlcBtn',
        }
        for method, btn_name in pay_select_buttons.items():
            btn = self.widget.findChild(QPushButton, btn_name)
            if btn is not None:
                btn.clicked.connect(lambda _=None, m=method: self.handle_pay_select(m))

    def _cache_widgets(self) -> None:
        self._widgets = {
            'total_label': self.widget.findChild(QLabel, 'totalValPayLabel'),
            'unalloc_label': self.widget.findChild(QLabel, 'unallocValPayLabel'),
            'unalloc_frame': self.widget.findChild(QFrame, 'unallocPayFrame'),
            'status_label': self.widget.findChild(QLabel, 'payStatusLabel'),
            'cash': self.widget.findChild(QLineEdit, 'cashPayLineEdit'),
            'nets': self.widget.findChild(QLineEdit, 'netsPayLineEdit'),
            'paynow': self.widget.findChild(QLineEdit, 'paynowPayLineEdit'),
            'voucher': self.widget.findChild(QLineEdit, 'voucherPayLineEdit'),
            'tender_label': self.widget.findChild(QLabel, 'tenderTtlLabel'),
            'tender': self.widget.findChild(QLineEdit, 'tenderValLineEdit'),
            'balance_label': self.widget.findChild(QLabel, 'balanceTtlLabel'),
            'balance': self.widget.findChild(QLineEdit, 'balanceValLineEdit'),
            'pay_button': self.widget.findChild(QPushButton, 'payPayOpsBtn'),
            'reset_button': self.widget.findChild(QPushButton, 'resetPayOpsBtn'),
            'print_button': self.widget.findChild(QPushButton, 'printPayOpsBtn'),
        }

        balance = self._widgets.get('balance')
        if balance is not None:
            balance.setReadOnly(True)

    def _wire_inputs(self) -> None:
        pay_fields = self._pay_field_order()
        for field in pay_fields:
            if field is None:
                continue
            field.textChanged.connect(self.recalc_unalloc_and_ui)
            field.installEventFilter(self)

        tender = self._widgets.get('tender')
        if tender is not None:
            tender.textChanged.connect(self.recalc_cash_balance_and_ui)
            tender.textChanged.connect(self.update_pay_button_state)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if obj in self._pay_field_order():
                if self._last_unalloc > 0:
                    self.focus_jump_next_pay_field(obj)
                    return True
        return super().eventFilter(obj, event)

    def handle_pay_clicked(self) -> None:
        self.recalc_unalloc_and_ui()
        self.recalc_cash_balance_and_ui()
        if not self._is_payment_valid():
            self.update_pay_button_state()
            return

        payload = self._collect_payment_split()
        payload['total'] = self._get_total_amount()
        payload['tender'] = self._get_float_value(self._widgets.get('tender'))
        payload['change'] = self._get_float_value(self._widgets.get('balance'))
        self.payRequested.emit(payload)

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
            if key == 'voucher':
                payload[key] = self._parse_int(widget.text() if widget is not None else '')
            else:
                payload[key] = self._parse_amount(widget.text() if widget is not None else '')
        return payload

    @staticmethod
    def _parse_amount(value: str) -> float:
        try:
            stripped = value.strip().replace('$', '').replace(',', '')
            return float(stripped) if stripped else 0.0
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_int(value: str) -> int:
        try:
            stripped = ''.join(ch for ch in str(value or '') if ch.isdigit())
            return int(stripped) if stripped else 0
        except ValueError:
            return 0

    def _pay_field_order(self):
        return [
            self._widgets.get('nets'),
            self._widgets.get('paynow'),
            self._widgets.get('voucher'),
            self._widgets.get('cash'),
        ]

    def _get_total_amount(self) -> float:
        label = self._widgets.get('total_label')
        return self._parse_amount(label.text() if label is not None else '')

    def _get_unalloc_amount(self) -> float:
        label = self._widgets.get('unalloc_label')
        return self._parse_amount(label.text() if label is not None else '')

    def _get_float_value(self, widget: QLineEdit) -> float:
        if widget is None:
            return 0.0
        return self._parse_amount(widget.text())

    def _set_line_text(self, widget: QLineEdit, text: str) -> None:
        if widget is None:
            return
        widget.blockSignals(True)
        widget.setText(text)
        widget.blockSignals(False)

    def _set_label_text(self, widget: QLabel, text: str) -> None:
        if widget is None:
            return
        widget.setText(text)

    @staticmethod
    def _format_money(amount: float) -> str:
        return f"${amount:.2f}"

    @staticmethod
    def _format_number(amount: float) -> str:
        return f"{amount:.2f}"

    def set_payment_default(self, total: float) -> None:
        self._set_label_text(self._widgets.get('total_label'), self._format_money(total))
        self._set_line_text(self._widgets.get('cash'), self._format_number(total))
        self._set_line_text(self._widgets.get('nets'), "")
        self._set_line_text(self._widgets.get('paynow'), "")
        self._set_line_text(self._widgets.get('voucher'), "")
        self._set_line_text(self._widgets.get('tender'), "")
        self._last_pay_select_method = None
        self._clear_status()
        self.recalc_unalloc_and_ui()
        self.update_pay_button_state()
        tender = self._widgets.get('tender')
        if tender is not None and tender.isVisible():
            tender.setFocus()
            tender.selectAll()

    def clear_payment_frame(self) -> None:
        self._set_label_text(self._widgets.get('total_label'), self._format_money(0.0))
        self._set_label_text(self._widgets.get('unalloc_label'), self._format_money(0.0))
        self._set_line_text(self._widgets.get('cash'), "")
        self._set_line_text(self._widgets.get('nets'), "")
        self._set_line_text(self._widgets.get('paynow'), "")
        self._set_line_text(self._widgets.get('voucher'), "")
        self._set_line_text(self._widgets.get('tender'), "")
        self._set_line_text(self._widgets.get('balance'), "")
        self._clear_unalloc_highlight()
        self._clear_status()
        self._has_balance_error = False
        self._has_unalloc_warning = False
        self._set_tender_visibility(False)
        self.update_pay_button_state()

    def reset_payment_grid_to_default(self) -> None:
        total = self._get_total_amount()
        self.set_payment_default(total)

    def recalc_unalloc_and_ui(self) -> None:
        total = self._get_total_amount()
        cash = self._get_float_value(self._widgets.get('cash'))
        nets = self._get_float_value(self._widgets.get('nets'))
        paynow = self._get_float_value(self._widgets.get('paynow'))
        voucher = float(self._parse_int(self._widgets.get('voucher').text() if self._widgets.get('voucher') else ''))

        unalloc = total - (cash + nets + paynow + voucher)
        self._last_unalloc = unalloc
        self._set_label_text(self._widgets.get('unalloc_label'), self._format_money(unalloc))

        self._update_unalloc_ui(unalloc)
        self.update_readonly_policy()
        self.recalc_cash_balance_and_ui()
        self.update_pay_button_state()

    def _update_unalloc_ui(self, unalloc: float) -> None:
        if unalloc > 0:
            self._apply_unalloc_highlight(True)
            self._has_unalloc_warning = True
        else:
            self._apply_unalloc_highlight(False)
            self._has_unalloc_warning = False

        if self._has_balance_error:
            self._set_status("Cash tender is less than cash amount.", is_error=True)
        elif unalloc > 0:
            self._set_status("Balance remains to allocate.", is_error=True)
        elif unalloc < 0:
            self._set_status("Over-allocated payment amount.", is_error=True)
        else:
            self._clear_status()

    def update_readonly_policy(self) -> None:
        unalloc = self._last_unalloc
        for field in self._pay_field_order():
            if field is None:
                continue
            if unalloc == 0:
                val = self._parse_amount(field.text())
                field.setReadOnly(val <= 0)
            else:
                field.setReadOnly(False)

    def recalc_cash_balance_and_ui(self) -> None:
        cash = self._get_float_value(self._widgets.get('cash'))
        tender_widget = self._widgets.get('tender')

        if cash <= 0:
            self._set_tender_visibility(False)
            self._set_line_text(self._widgets.get('balance'), self._format_number(0.0))
            self._has_balance_error = False
            self._update_unalloc_ui(self._last_unalloc)
            return

        self._set_tender_visibility(True)
        tender = self._get_float_value(tender_widget)
        balance = tender - cash
        self._set_line_text(self._widgets.get('balance'), self._format_number(balance))
        if balance < 0:
            self._has_balance_error = True
        else:
            self._has_balance_error = False
        self._update_unalloc_ui(self._last_unalloc)

    def update_pay_button_state(self) -> None:
        pay_btn = self._widgets.get('pay_button')
        reset_btn = self._widgets.get('reset_button')
        print_btn = self._widgets.get('print_button')

        total = self._get_total_amount()
        unalloc = self._last_unalloc
        cash = self._get_float_value(self._widgets.get('cash'))
        tender = self._get_float_value(self._widgets.get('tender'))

        # Reset enabled only when there is a non-zero total
        if reset_btn is not None:
            reset_btn.setEnabled(total > 0)

        # Print enabled only when total is zero/empty
        if print_btn is not None:
            print_btn.setEnabled(total <= 0)

        if pay_btn is None:
            return

        ctx = getattr(self._main_window, 'receipt_context', {}) or {}
        status = ctx.get('status')
        status_ok = status in ('NONE', 'UNPAID')

        can_pay = total > 0 and unalloc == 0 and status_ok
        if cash > 0:
            can_pay = can_pay and tender >= cash

        pay_btn.setEnabled(can_pay)

    def handle_pay_select(self, method: str) -> None:
        field_map = {
            'cash': self._widgets.get('cash'),
            'nets': self._widgets.get('nets'),
            'paynow': self._widgets.get('paynow'),
            'voucher': self._widgets.get('voucher'),
        }
        field = field_map.get(method)
        if field is None:
            return

        if self._last_pay_select_method == method:
            field.setFocus()
            field.selectAll()
            return

        self._last_pay_select_method = method
        field.blockSignals(True)
        field.clear()
        field.blockSignals(False)
        self.recalc_unalloc_and_ui()

        remaining = self._last_unalloc
        if method == 'voucher':
            remaining_val = int(round(remaining))
            self._set_line_text(field, str(max(remaining_val, 0)))
        else:
            self._set_line_text(field, self._format_number(max(remaining, 0.0)))

        self.recalc_unalloc_and_ui()
        field.setFocus()
        field.selectAll()

    def focus_jump_next_pay_field(self, current=None) -> None:
        fields = [f for f in self._pay_field_order() if f is not None]
        if not fields:
            return
        try:
            idx = fields.index(current)
        except ValueError:
            idx = -1
        for offset in range(1, len(fields) + 1):
            target = fields[(idx + offset) % len(fields)]
            if target.isReadOnly() or not target.isEnabled():
                continue
            target.setFocus()
            target.selectAll()
            break

    def _set_tender_visibility(self, enabled: bool) -> None:
        for key in ('tender_label', 'tender', 'balance_label', 'balance'):
            widget = self._widgets.get(key)
            if widget is None:
                continue
            widget.setEnabled(enabled)
        if not enabled:
            self._set_line_text(self._widgets.get('tender'), "")

    def _apply_unalloc_highlight(self, active: bool) -> None:
        label = self._widgets.get('unalloc_label')
        frame = self._widgets.get('unalloc_frame')
        if active:
            if label is not None:
                label.setStyleSheet("background-color: #fff2cc; border: 3px solid #ff9800;")
            if frame is not None:
                frame.setStyleSheet("border: 3px solid #ff9800; background-color: #fff7e6;")
        else:
            if label is not None:
                label.setStyleSheet("")
            if frame is not None:
                frame.setStyleSheet("")

    def _clear_unalloc_highlight(self) -> None:
        self._apply_unalloc_highlight(False)

    def _set_status(self, message: str, is_error: bool = False) -> None:
        label = self._widgets.get('status_label')
        if label is None:
            return
        ui_feedback.set_status_label(label, message, ok=not is_error)

    def _clear_status(self) -> None:
        label = self._widgets.get('status_label')
        if label is None:
            return
        ui_feedback.clear_status_label(label)

    def _is_payment_valid(self) -> bool:
        total = self._get_total_amount()
        if total <= 0:
            return False
        if self._last_unalloc != 0:
            return False
        cash = self._get_float_value(self._widgets.get('cash'))
        tender = self._get_float_value(self._widgets.get('tender'))
        if cash > 0 and tender < cash:
            return False
        return True


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
