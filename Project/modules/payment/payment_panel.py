"""Payment UI controller.

Emits `payRequested` (payload) when payment is confirmed. Database
finalization (atomic commit across receipts/items/payments) is handled by
the application layer (`main.py`).
"""
import os
from config import ENABLE_PRINTER_PRINT
from PyQt5 import uic
from PyQt5.QtCore import QObject, pyqtSignal, Qt, QEvent
from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QLineEdit, QLabel, QFrame

from modules.ui_utils import ui_feedback
from modules.ui_utils.dialog_utils import report_to_statusbar
from modules.ui_utils.error_logger import log_error
from modules.payment import receipt_generator


class PaymentPanel(QObject):
    payRequested = pyqtSignal(dict)
    paymentSuccess = pyqtSignal()

    # Initialization and wiring
    def __init__(self, main_window, placeholder, ui_path):
        # Initialize payment panel state, load UI, and wire controls/events.
        super().__init__()
        self._main_window = main_window
        self._placeholder = placeholder
        self.widget = uic.loadUi(ui_path)
        self._widgets = {}
        self._placeholders = {}
        self._unalloc_title_default = "Balance to Allocate"
        self._last_pay_select_method = None
        self._last_unalloc = 0.0
        self._has_validation_error = False
        self._validation_message = ""
        self._pay_select_buttons = {}
        self._last_invalid_widget = None
        self._attach_to_placeholder()
        self._cache_widgets()
        self._wire_buttons()
        self._wire_inputs()
        self.clear_payment_frame()

    # Public API
    def notify_payment_success(self) -> None:
        # Emit payment success signal for downstream workflow updates.
        self.paymentSuccess.emit()

    # Layout and wiring helpers
    def _attach_to_placeholder(self) -> None:
        # Attach the loaded payment widget into the host placeholder layout.
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

    def _cache_widgets(self) -> None:
        # Cache UI child widgets and defaults for fast repeated access.
        self._widgets = {
            'total_label': self.widget.findChild(QLabel, 'totalValPayLabel'),
            'unalloc_label': self.widget.findChild(QLabel, 'unallocValPayLabel'),
            'unalloc_title': self.widget.findChild(QLabel, 'unallocTtlPayLabel'),
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
            balance.setFocusPolicy(Qt.NoFocus)

        for key in ('cash', 'nets', 'paynow', 'voucher', 'tender'):
            widget = self._widgets.get(key)
            if widget is not None:
                self._placeholders[key] = widget.placeholderText()

        title = self._widgets.get('unalloc_title')
        if title is not None and title.text().strip():
            self._unalloc_title_default = title.text().strip()

    def _wire_buttons(self) -> None:
        # Connect operation/select button signals and key event handling.
        # Enter key activation for ops buttons
        for btn_name, handler in [
            ('payPayOpsBtn', self.handle_pay_clicked),
            ('resetPayOpsBtn', self.reset_payment_grid_to_default),
            ('printPayOpsBtn', self.handle_print_clicked),
        ]:
            btn = self.widget.findChild(QPushButton, btn_name)
            if btn is not None:
                if handler:
                    btn.clicked.connect(handler)
                try:
                    btn.installEventFilter(self)
                except Exception:
                    pass

        # Wire payment selection buttons
        self._pay_select_buttons = {}
        for method, btn_name in {
            'cash': 'cashPaySlcBtn',
            'nets': 'netsPaySlcBtn',
            'paynow': 'paynowPaySlcBtn',
            'voucher': 'voucherPaySlcBtn',
        }.items():
            btn = self.widget.findChild(QPushButton, btn_name)
            if btn is not None:
                self._pay_select_buttons[method] = btn
                btn.clicked.connect(lambda _=None, m=method: self.handle_pay_select(m))

    def _wire_inputs(self) -> None:
        # Connect field change/validation handlers and install line-edit event filters.
        pay_fields = self._pay_field_order()
        for field in pay_fields:
            if field is None:
                    continue
            field.textChanged.connect(self.recalc_unalloc_and_ui)
            field.textChanged.connect(lambda _=None, f=field: self._clear_validation_error(f))
            field.editingFinished.connect(self._validate_currency_field)

        tender = self._widgets.get('tender')
        if tender is not None:
            tender.textChanged.connect(self.recalc_cash_balance_and_ui)
            tender.textChanged.connect(self.update_pay_button_state)
            tender.textChanged.connect(lambda _=None, f=tender: self._clear_validation_error(f))
            tender.editingFinished.connect(self._validate_currency_field)

        for field in self._lineedit_state_widgets():
            try:
                field.installEventFilter(self)
            except Exception:
                pass

    # Parsing and formatting helpers
    @staticmethod
    def _parse_amount(value: str) -> float:
        # Parse currency-like text into float, returning 0.0 on invalid input.
        try:
            stripped = value.strip().replace('$', '').replace(',', '')
            return float(stripped) if stripped else 0.0
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_int(value: str) -> int:
        # Parse digits from text into int, returning 0 on invalid/empty input.
        try:
            stripped = ''.join(ch for ch in str(value or '') if ch.isdigit())
            return int(stripped) if stripped else 0
        except ValueError:
            return 0

    @staticmethod
    def _format_money(amount: float) -> str:
        # Format amount as a display currency string with a dollar sign.
        return f"${amount:.2f}"

    @staticmethod
    def _format_number(amount: float) -> str:
        # Format amount as a plain two-decimal numeric string.
        return f"{amount:.2f}"

    @staticmethod
    def _round_currency(amount: float) -> float:
        # Round to currency precision and normalize near-zero values to 0.0.
        amt = round(amount, 2)
        return 0.0 if abs(amt) < 0.005 else amt

    def _set_line_text(self, widget: QLineEdit, text: str) -> None:
        # Set line-edit text without emitting connected text-change signals.
        if widget is None:
            return
        widget.blockSignals(True)
        widget.setText(text)
        widget.blockSignals(False)

    def _set_label_text(self, widget: QLabel, text: str) -> None:
        # Set label text safely when widget exists.
        if widget is None:
            return
        widget.setText(text)

    # Field accessors
    def _pay_field_order(self):
        # Return the ordered payment entry fields used for navigation.
        return [
            self._widgets.get('nets'),
            self._widgets.get('paynow'),
            self._widgets.get('voucher'),
            self._widgets.get('cash'),
        ]

    def _get_total_amount(self) -> float:
        # Read and parse the payable total from the total label.
        label = self._widgets.get('total_label')
        return self._parse_amount(label.text() if label is not None else '')

    def _get_float_value(self, widget: QLineEdit) -> float:
        # Parse and return a float value from a line edit.
        if widget is None:
            return 0.0
        return self._parse_amount(widget.text())

    def _get_validated_amount(self, widget: QLineEdit) -> float:
        # Validate and parse a currency field using shared input handlers.
        if widget is None:
            return 0.0
        try:
            from modules.ui_utils import input_handler
            return input_handler.handle_currency_input(widget)
        except Exception:
            return self._parse_amount(widget.text())

    def _get_validated_voucher(self, widget: QLineEdit) -> int:
        # Validate and parse voucher input as integer units.
        if widget is None:
            return 0
        try:
            from modules.ui_utils import input_handler
            return input_handler.handle_voucher_input(widget)
        except Exception:
            return 0

    # Public API
    def set_payment_default(self, total: float) -> None:
        # Reset payment split to default values for the provided total.
        if total <= 0:
            self.clear_payment_frame()
            return
        self._reset_validation_feedback()
        self._set_label_text(self._widgets.get('total_label'), self._format_money(total))
        self._set_line_text(self._widgets.get('cash'), self._format_number(total))
        self._set_line_text(self._widgets.get('nets'), "")
        self._set_line_text(self._widgets.get('paynow'), "")
        self._set_line_text(self._widgets.get('voucher'), "")
        self._set_line_text(self._widgets.get('tender'), "")
        self._last_pay_select_method = None
        self.recalc_unalloc_and_ui()
        self.update_pay_button_state()
        tender = self._widgets.get('tender')
        if tender is not None and tender.isVisible():
            tender.setFocus()
            tender.selectAll()

    def clear_payment_frame(self) -> None:
        # Clear all payment fields/state and return the panel to idle defaults.
        self._reset_validation_feedback()
        self._set_label_text(self._widgets.get('total_label'), self._format_money(0.0))
        self._set_label_text(self._widgets.get('unalloc_label'), self._format_money(0.0))
        self._set_line_text(self._widgets.get('cash'), "")
        self._set_line_text(self._widgets.get('nets'), "")
        self._set_line_text(self._widgets.get('paynow'), "")
        self._set_line_text(self._widgets.get('voucher'), "")
        self._set_line_text(self._widgets.get('tender'), "")
        self._set_line_text(self._widgets.get('balance'), "")
        self._last_unalloc = 0.0
        self._clear_unalloc_highlight()
        self._set_tender_visibility(False)
        self.update_readonly_policy()
        self.update_pay_button_state()

    def reset_payment_grid_to_default(self) -> None:
        # Reapply default split behavior using the current total amount.
        self._reset_validation_feedback()
        total = self._get_total_amount()
        self.set_payment_default(total)

    # Calculations and state updates
    def recalc_unalloc_and_ui(self) -> None:
        # Recompute unallocated amount and refresh dependent UI/interactivity.
        total = self._get_total_amount()
        cash = self._get_validated_amount(self._widgets.get('cash'))
        nets = self._get_validated_amount(self._widgets.get('nets'))
        paynow = self._get_validated_amount(self._widgets.get('paynow'))
        voucher = float(self._get_validated_voucher(self._widgets.get('voucher')))

        unalloc = self._round_currency(total - (cash + nets + paynow + voucher))
        self._last_unalloc = unalloc
        self._set_label_text(self._widgets.get('unalloc_label'), self._format_money(unalloc))

        self._update_unalloc_ui(unalloc)
        self.update_readonly_policy()
        self.recalc_cash_balance_and_ui()
        self._update_placeholders(unalloc, cash)
        self._refresh_status(cash, self._get_validated_amount(self._widgets.get('tender')), unalloc)
        self.update_pay_button_state()

    def recalc_cash_balance_and_ui(self) -> None:
        # Recompute tender-change balance and refresh related cash UI state.
        cash = self._get_validated_amount(self._widgets.get('cash'))
        tender_widget = self._widgets.get('tender')

        if cash <= 0:
            self._set_tender_visibility(False)
            self._set_line_text(self._widgets.get('balance'), "")
            self._update_unalloc_ui(self._last_unalloc)
            self._update_placeholders(self._last_unalloc, cash)
            return

        self._set_tender_visibility(True)
        tender = self._get_validated_amount(tender_widget)
        balance = self._round_currency(tender - cash)
        self._set_line_text(self._widgets.get('balance'), self._format_number(balance))
        self._update_unalloc_ui(self._last_unalloc)
        self._update_placeholders(self._last_unalloc, cash)
        self._refresh_status(cash, tender, self._last_unalloc)

    def update_readonly_policy(self) -> None:
        # Lock/unlock entry fields based on allocation and cash/tender rules.
        unalloc = self._last_unalloc
        cash_field = self._widgets.get('cash')
        cash_val = self._get_validated_amount(cash_field)

        for key, field in zip(('nets', 'paynow', 'voucher', 'cash'), self._pay_field_order()):
            if field is None:
                continue
            has_raw_text = bool(field.text().strip())
            locked = unalloc <= 0 and not has_raw_text
            field.setReadOnly(locked)
            field.setFocusPolicy(Qt.NoFocus if locked else Qt.StrongFocus)
            field.setEnabled(not locked)
            if locked and field.hasFocus():
                self.focus_jump_next_pay_field(field)

        tender = self._widgets.get('tender')
        if tender is not None:
            tender_locked = cash_val <= 0
            tender.setReadOnly(tender_locked)
            tender.setFocusPolicy(Qt.NoFocus if tender_locked else Qt.StrongFocus)

        self._refresh_lineedit_visuals()

    def update_pay_button_state(self) -> None:
        # Enable or disable payment actions according to business constraints.
        pay_btn = self._widgets.get('pay_button')
        reset_btn = self._widgets.get('reset_button')
        print_btn = self._widgets.get('print_button')

        total = self._get_total_amount()
        unalloc = self._last_unalloc
        cash = self._get_validated_amount(self._widgets.get('cash'))
        tender = self._get_validated_amount(self._widgets.get('tender'))

        # Respect global payment-in-progress flag from main window to avoid
        # allowing Reset/Pay while a commit is underway.
        busy = getattr(self._main_window, '_payment_in_progress', False)

        if reset_btn is not None:
            reset_btn.setEnabled(total > 0 and not busy)

        if print_btn is not None:
            print_btn.setEnabled(total <= 0)

        if pay_btn is None:
            return

        ctx = getattr(self._main_window, 'receipt_context', {}) or {}
        status = ctx.get('status')
        status_ok = status in ('NONE', 'UNPAID')

        can_pay = total > 0 and unalloc <= 0 and status_ok and not self._has_validation_error
        if cash > 0:
            can_pay = can_pay and tender >= cash

        # Disable Pay while busy in addition to normal gating rules.
        pay_btn.setEnabled(can_pay and not busy)
        for btn in self._pay_select_buttons.values():
            btn.setEnabled(total > 0 and not busy)

    def _update_placeholders(self, unalloc: float, cash: float) -> None:
        # Show contextual placeholders only where user guidance is needed.
        for key in ('cash', 'nets', 'paynow', 'voucher'):
            field = self._widgets.get(key)
            if field is None:
                continue
            has_value = bool(field.text().strip()) and self._parse_amount(field.text()) > 0
            show = unalloc > 0 and not has_value
            placeholder = self._placeholders.get(key, "") if show else ""
            field.setPlaceholderText(placeholder)

        tender = self._widgets.get('tender')
        if tender is not None:
            tender_has_val = bool(tender.text().strip()) and self._parse_amount(tender.text()) > 0
            show_tender_ph = cash > 0 and not tender_has_val
            tender.setPlaceholderText(self._placeholders.get('tender', "") if show_tender_ph else "")

    def _refresh_status(self, cash: float, tender: float, unalloc: float) -> None:
        # Update status label with highest-priority validation/payment message.
        if self._has_validation_error:
            self._set_status(self._validation_message or "Invalid amount.", is_error=True)
            return
        if cash > 0 and tender < cash:
            self._set_status("Cash tender < CASH payable.", is_error=True)
            return
        '''if unalloc > 0:
            self._set_status("Payable not fully allocated.", is_error=True)
            return'''
        if unalloc < 0:
            self._set_status("Warning: Payment Over-allocation.", is_error=True)
            return
        self._clear_status()

    def _run_validation_pass(self) -> None:
        # Validate all populated payment fields and record first validation failure.
        try:
            from modules.ui_utils import input_handler
            for field in (self._widgets.get('cash'), self._widgets.get('nets'), self._widgets.get('paynow'), self._widgets.get('tender')):
                if field is None:
                    continue
                if not (field.text() or '').strip():
                    continue
                try:
                    input_handler.handle_currency_input(field)
                except Exception:
                    self._mark_widget_invalid(field)
                    raise
            voucher_field = self._widgets.get('voucher')
            if voucher_field is not None and (voucher_field.text() or '').strip():
                try:
                    input_handler.handle_voucher_input(voucher_field)
                except Exception:
                    self._mark_widget_invalid(voucher_field)
                    raise
            self._has_validation_error = False
            self._validation_message = ""
            self._clear_all_validation_marks()
        except Exception as exc:
            self._has_validation_error = True
            self._validation_message = str(exc) if str(exc) else "Invalid amount."

    def _validate_currency_field(self) -> None:
        # Run validation pipeline after editing and refresh status/button state.
        self._run_validation_pass()
        self._refresh_status(
            self._get_validated_amount(self._widgets.get('cash')),
            self._get_validated_amount(self._widgets.get('tender')),
            self._last_unalloc,
        )
        self.update_pay_button_state()

    # Navigation
    def eventFilter(self, obj, event):
        # Intercept focus/enter-key events for validation-aware navigation behavior.
        if isinstance(obj, QLineEdit) and self._is_state_managed_lineedit(obj):
            if event.type() == QEvent.FocusIn:
                if obj in self._pay_field_order() or obj == self._widgets.get('tender'):
                    self._clear_validation_error(obj)
                self._refresh_lineedit_visuals()
            elif event.type() == QEvent.FocusOut:
                self._refresh_lineedit_visuals()

        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if isinstance(obj, QPushButton) and obj.isEnabled():
                obj.click()
                return True

            if obj in self._pay_field_order() or obj == self._widgets.get('tender'):
                try:
                    from modules.ui_utils import input_handler
                    # only validate when there's content
                    text = obj.text() if hasattr(obj, 'text') else ''
                    if text and text.strip():
                        if obj == self._widgets.get('voucher'):
                            input_handler.handle_voucher_input(obj)
                        else:
                            input_handler.handle_currency_input(obj)
                except Exception as exc:
                    self._has_validation_error = True
                    self._validation_message = str(exc) or "Invalid amount."
                    self._mark_widget_invalid(obj)
                    self._set_status(self._validation_message, is_error=True)
                    try:
                        obj.setFocus()
                        if hasattr(obj, 'selectAll'):
                            obj.selectAll()
                    except Exception:
                        pass
                    return True

                # valid — continue navigation
                self._handle_enter_navigation(
                    obj,
                    self._get_validated_amount(self._widgets.get('cash')),
                    self._get_validated_amount(self._widgets.get('tender')),
                    self._last_unalloc,
                )
                return True

        return super().eventFilter(obj, event)

    def _handle_enter_navigation(self, current, cash: float, tender: float, unalloc: float) -> None:
        # Route focus on Enter based on current field and payment completion state.
        cash_field = self._widgets.get('cash')
        tender_field = self._widgets.get('tender')
        pay_btn = self._widgets.get('pay_button')

        if current == cash_field:
            if cash > 0 and unalloc <= 0:
                tender = self._get_validated_amount(tender_field)
                if tender_field is not None and tender < cash:
                    tender_field.setFocus()
                    tender_field.selectAll()
                    return
                if pay_btn is not None:
                    pay_btn.setFocus()
                return
            if unalloc > 0:
                self.focus_jump_next_pay_field(current)
                return
        elif current in self._pay_field_order():
            if unalloc <= 0:
                if pay_btn is not None:
                    pay_btn.setFocus()
                return
            self.focus_jump_next_pay_field(current)
            return
        elif current == tender_field:
            if tender < cash:
                current.selectAll()
                return
            if tender > cash and unalloc > 0:
                self.focus_jump_next_pay_field()
                return
            if tender >= cash and unalloc <= 0:
                if pay_btn is not None:
                    pay_btn.setFocus()
                return

    

    def focus_jump_next_pay_field(self, current=None) -> None:
            # Move focus to the next editable payment field in navigation order.
        fields = [f for f in self._pay_field_order() if f is not None and f.isEnabled() and not f.isReadOnly()]
        if not fields:
            return
        try:
            idx = fields.index(current)
        except ValueError:
            idx = -1
        for offset in range(1, len(fields) + 1):
            target = fields[(idx + offset) % len(fields)]
            target.setFocus()
            target.selectAll()
            break

    # Actions
    def handle_pay_select(self, method: str) -> None:
        # Apply one-tap full allocation to a selected payment method.
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
        total = self._get_total_amount()
        for key, le in field_map.items():
            if le is None:
                continue
            le.blockSignals(True)
            if key == method:
                if key == 'voucher':
                    self._set_line_text(le, str(int(round(total))))
                else:
                    self._set_line_text(le, self._format_number(total))
            else:
                le.clear()
            le.blockSignals(False)

        self.recalc_unalloc_and_ui()

        if method == 'cash':
            tender = self._widgets.get('tender')
            if tender is not None:
                tender.setFocus()
                tender.selectAll()
            else:
                pay_btn = self._widgets.get('pay_button')
                if pay_btn is not None:
                    pay_btn.setFocus()
        else:
            pay_btn = self._widgets.get('pay_button')
            if pay_btn is not None:
                pay_btn.setFocus()

    def handle_pay_clicked(self) -> None:
        # Validate payment state and emit finalized payment payload when valid.
        self.recalc_unalloc_and_ui()
        self.recalc_cash_balance_and_ui()
        if not self._is_payment_valid():
            self.update_pay_button_state()
            return

        payload = self._collect_payment_split()
        payload['total'] = self._get_total_amount()
        payload['tender'] = self._get_validated_amount(self._widgets.get('tender'))
        payload['change'] = self._get_float_value(self._widgets.get('balance'))
        self.payRequested.emit(payload)

    def handle_print_clicked(self) -> None:
        # Print the last completed receipt to console (v1 behavior).
        ctx = getattr(self._main_window, 'receipt_context', {}) or {}
        receipt_no = ctx.get('last_receipt_no')
        if not receipt_no:
            report_to_statusbar(self._main_window, "No Receipt to be printed.", is_error=True, duration=3000)
            return

        try:
            receipt_text = receipt_generator.generate_receipt_text(str(receipt_no))
            printer_success = None

            if not ENABLE_PRINTER_PRINT:
                print(receipt_text)
            else:
                try:
                    from modules.devices import printer as device_printer
                    printed_ok = device_printer.print_receipt(receipt_text, blocking=True)
                    printer_success = bool(printed_ok)
                    if not printer_success:
                        log_error(f"Printer send failed (device rejected / protocol error) for receipt {receipt_no}.")
                        report_to_statusbar(
                            self._main_window,
                            f"Receipt {receipt_no} printer send failed.",
                            is_error=True,
                            duration=3000,
                        )
                except Exception as exc:
                    printer_success = False
                    log_error(f"Printer helper call failed: {exc}. Failure before even talking to printer")
                    report_to_statusbar(
                        self._main_window,
                        f"Receipt {receipt_no} printer error.",
                        is_error=True,
                        duration=3000,
                    )

            if printer_success is not False:
                report_to_statusbar(
                    self._main_window,
                    f"Receipt {receipt_no} printed.",
                    is_error=False,
                    duration=3000,
                )
            if "Receipt Status is UNKNOWN" in receipt_text:
                log_error(f"Receipt status is UNKNOWN for receipt {receipt_no}.")
                
        except ValueError:
            log_error(f"Receipt not found for receipt {receipt_no}.")
            report_to_statusbar(self._main_window, "Receipt not found.", is_error=True, duration=3000)
        except RuntimeError:
            log_error(f"Receipt data not found for receipt {receipt_no}.")
            report_to_statusbar(
                self._main_window,
                "Receipt data not found.",
                is_error=True,
                duration=3000,
            )
        except Exception as exc:
            log_error(f"Receipt print failed: {exc}")
            report_to_statusbar(
                self._main_window,
                "Receipt print failed.",
                is_error=True,
                duration=3000,
            )

    def _collect_payment_split(self) -> dict:
        # Build normalized payment split values from UI fields.
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
                payload[key] = self._get_validated_voucher(widget) if widget is not None else 0
            else:
                payload[key] = self._parse_amount(widget.text() if widget is not None else '')
        return payload

    def _is_payment_valid(self) -> bool:
        # Check whether current payment values satisfy all completion rules.
        total = self._get_total_amount()
        if total <= 0:
            return False
        if self._last_unalloc > 0:
            return False
        if self._has_validation_error:
            return False
        cash = self._get_validated_amount(self._widgets.get('cash'))
        tender = self._get_validated_amount(self._widgets.get('tender'))
        if cash > 0 and tender < cash:
            return False
        return True

    # UI helpers
    def _set_tender_visibility(self, enabled: bool) -> None:
        # Toggle tender/change widgets together and clear tender input when hidden.
        for key in ('tender_label', 'tender', 'balance_label', 'balance'):
            widget = self._widgets.get(key)
            if widget is None:
                continue
            widget.setEnabled(enabled)
        if not enabled:
            self._set_line_text(self._widgets.get('tender'), "")

    def _apply_unalloc_highlight(self, active: bool, unalloc: float = 0.0) -> None:
        # Paint unallocated section highlight colors based on current allocation state.
        title = self._widgets.get('unalloc_title')
        label = self._widgets.get('unalloc_label')
        frame = self._widgets.get('unalloc_frame')

        if active:
            if title is not None:
                color = "red" if unalloc > 0 else "blue" if unalloc < 0 else ""
                title.setStyleSheet(f"color: {color}; border: transparent;" if color else "border: transparent;")
            if label is not None:
                label.setStyleSheet("background-color: yellow; border: transparent;")
            if frame is not None:
                frame.setStyleSheet("""
                    background-color: orange;
                    border: 3px solid orange;
                    border-radius: 10px;
                """)
        else:
            if title is not None:
                title.setStyleSheet("border: transparent;")
            if label is not None:
                label.setStyleSheet("border: transparent;")
            if frame is not None:
                frame.setStyleSheet("")  # or restore original if stored

    def _clear_unalloc_highlight(self) -> None:
        # Reset unallocated section highlight to its normal style.
        self._apply_unalloc_highlight(False, 0.0)

    def _update_unalloc_ui(self, unalloc: float) -> None:
        # Highlight whenever unalloc is non-zero; update title to show over-allocation
        self._apply_unalloc_highlight(unalloc != 0, unalloc)
        title = self._widgets.get('unalloc_title')
        if title is not None:
            if unalloc < 0:
                title.setText("Over Allocated")
            elif unalloc > 0:
                title.setText("Allocate Remaining")
            else:
                title.setText(self._unalloc_title_default)

    def _set_status(self, message: str, is_error: bool = False) -> None:
        # Display a status message in success or error style.
        label = self._widgets.get('status_label')
        if label is None:
            return
        ui_feedback.set_status_label(label, message, ok=not is_error)

    def _clear_status(self) -> None:
        # Clear status label text and state styling.
        label = self._widgets.get('status_label')
        if label is None:
            return
        ui_feedback.clear_status_label(label)

    def _mark_widget_invalid(self, widget) -> None:
        # Mark a line edit with validation error styling metadata.
        try:
            if isinstance(widget, QLineEdit):
                self._last_invalid_widget = widget
                widget.setProperty('validation', 'error')
                self._refresh_lineedit_visuals()
        except Exception:
            pass

    def _clear_validation_error(self, widget=None) -> None:
        # Clear current validation error state for the active invalid widget.
        if widget is not None and widget is not self._last_invalid_widget:
            return
        if self._has_validation_error:
            self._has_validation_error = False
            self._validation_message = ""
            self._clear_status()
        if isinstance(widget, QLineEdit):
            try:
                widget.setProperty('validation', '')
                self._refresh_lineedit_visuals()
            except Exception:
                pass
        if widget is self._last_invalid_widget:
            self._last_invalid_widget = None

    def _is_state_managed_lineedit(self, widget: QLineEdit) -> bool:
        # Return True when a line edit participates in shared visual-state styling.
        name = widget.objectName() if widget is not None else ""
        return bool(name) and ('PayLineEdit' in name or 'ValLineEdit' in name)

    def _lineedit_state_widgets(self):
        # Collect all line edits that should receive shared visual-state updates.
        return [
            widget
            for widget in self.widget.findChildren(QLineEdit)
            if self._is_state_managed_lineedit(widget)
        ]

    def _resolve_lineedit_state(self, widget: QLineEdit) -> str:
        # Compute widget visual state with priority: invalid, focused, disabled, enabled.
        if widget is None:
            return 'enabled'
        if widget.property('validation') == 'error':
            return 'invalid'
        if widget.hasFocus():
            return 'focused'
        if (not widget.isEnabled()) or widget.isReadOnly() or widget.focusPolicy() == Qt.NoFocus:
            return 'disabled'
        return 'enabled'

    def _apply_lineedit_state(self, widget: QLineEdit, state: str) -> None:
        # Apply computed visual state property and refresh QSS rendering.
        if widget is None:
            return
        widget.setProperty('visualState', state)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _refresh_lineedit_visuals(self) -> None:
        # Recompute and apply visual state for all managed line edits.
        for widget in self._lineedit_state_widgets():
            self._apply_lineedit_state(widget, self._resolve_lineedit_state(widget))

    def _clear_all_validation_marks(self) -> None:
        # Clear validation flags on all managed line edits and refresh visuals.
        self._last_invalid_widget = None
        for widget in self._lineedit_state_widgets():
            widget.setProperty('validation', '')
        self._refresh_lineedit_visuals()

    def _reset_validation_feedback(self) -> None:
        # Reset validation flags, message label, and invalid styling in one shared path.
        self._has_validation_error = False
        self._validation_message = ""
        self._clear_status()
        self._clear_all_validation_marks()

def setup_payment_panel(main_window, UI_DIR):
    # Create and return the payment panel controller when UI resources are available.
    payment_placeholder = getattr(main_window, 'paymentFrame', None)
    payment_ui = os.path.join(UI_DIR, 'payment_frame.ui')
    if payment_placeholder is None or not os.path.exists(payment_ui):
        return None
    try:
        return PaymentPanel(main_window, payment_placeholder, payment_ui)
    except Exception as e:
        log_error(f"Failed to initialize payment panel: {e}")
        return None
