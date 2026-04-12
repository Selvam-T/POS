from PyQt5.QtCore import QObject, QEvent
from PyQt5.QtGui import QValidator
from PyQt5.QtWidgets import QApplication, QLineEdit, QPushButton


class KeypadController(QObject):
    """Wire payment keypad buttons to line edits with simple numeric input."""

    def __init__(self, parent, enter_handler=None, tab_handler=None):
        super().__init__(parent)
        self.parent = parent
        self._last_target = None
        self._last_button = None
        self._enter_handler = enter_handler
        self._tab_handler = tab_handler

        # wire numeric buttons 0-9, 00, dot
        for i in range(10):
            btn = parent.findChild(QPushButton, f"keyNumBtn{i}")
            if btn is not None:
                btn.clicked.connect(lambda _, d=str(i): self._on_digit(d))

        btn00 = parent.findChild(QPushButton, "keyNumBtn00")
        if btn00 is not None:
            btn00.clicked.connect(lambda: self._on_digit("00"))

        btndot = parent.findChild(QPushButton, "keyNumBtndot")
        if btndot is not None:
            btndot.clicked.connect(self._on_dot)

        # fast dollar buttons (set amount)
        for name, amt in (("keyDolBtn10", 10), ("keyDolBtn50", 50), ("keyDolBtn100", 100)):
            b = parent.findChild(QPushButton, name)
            if b is not None:
                b.clicked.connect(lambda _, a=amt: self._on_fast_set(a))

        # control buttons
        btn_tab = parent.findChild(QPushButton, "keyFastBtntab")
        if btn_tab is not None:
            btn_tab.clicked.connect(self._on_tab)

        btn_shtab = parent.findChild(QPushButton, "keyFastBtnshftab")
        if btn_shtab is not None:
            btn_shtab.clicked.connect(lambda: self._on_tab(reverse=True))

        btn_clear = parent.findChild(QPushButton, "keyFastBtnclr")
        if btn_clear is not None:
            btn_clear.clicked.connect(self._on_clear)

        self._enter_button = parent.findChild(QPushButton, "keyFastBtnenter")
        if self._enter_button is not None:
            self._enter_button.clicked.connect(self._on_enter)

        btn_bksp = parent.findChild(QPushButton, "keyFastBtnbksp")
        if btn_bksp is not None:
            btn_bksp.clicked.connect(self._on_backspace)

        # track last focused editable widgets so keypad input stays on field
        for le in parent.findChildren(QLineEdit):
            try:
                le.installEventFilter(self)
            except Exception:
                pass
        for btn in parent.findChildren(QPushButton):
            try:
                btn.installEventFilter(self)
            except Exception:
                pass

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            if isinstance(obj, QLineEdit):
                if not obj.isReadOnly():
                    self._last_target = obj
            elif isinstance(obj, QPushButton):
                if obj is not self._enter_button:
                    name = obj.objectName() or ""
                    if not name.startswith("keyNumBtn") and not name.startswith("keyDolBtn"):
                        if name not in {
                            "keyFastBtntab",
                            "keyFastBtnshftab",
                            "keyFastBtnclr",
                            "keyFastBtnenter",
                            "keyFastBtnbksp",
                            "keyNumBtndot",
                        }:
                            self._last_button = obj
        return super().eventFilter(obj, event)

    def _get_tab_target(self):
        fw = QApplication.focusWidget()
        if isinstance(fw, QLineEdit) and not fw.isReadOnly():
            return fw
        if isinstance(fw, QPushButton):
            name = fw.objectName() or ""
            if not name.startswith("keyNumBtn") and not name.startswith("keyDolBtn"):
                if name not in {
                    "keyFastBtntab",
                    "keyFastBtnshftab",
                    "keyFastBtnclr",
                    "keyFastBtnenter",
                    "keyFastBtnbksp",
                    "keyNumBtndot",
                }:
                    return fw
        if isinstance(self._last_button, QPushButton):
            return self._last_button
        if isinstance(self._last_target, QLineEdit) and not self._last_target.isReadOnly():
            return self._last_target
        return None

    def _get_target(self):
        fw = QApplication.focusWidget()
        if isinstance(fw, QLineEdit):
            if fw.isReadOnly():
                return None
            return fw
        if isinstance(self._last_target, QLineEdit) and not self._last_target.isReadOnly():
            return self._last_target
        return None

    def _format_after_append(self, s: str):
        # enforce max 2 fractional digits and basic leading-zero handling
        if "." in s:
            left, right = s.split(".", 1)
            if len(right) > 2:
                return None
            left = left.lstrip("0") or "0"
            return left + "." + right
        s = s.lstrip("0") or "0"
        return s

    def _accepts_text(self, target: QLineEdit, text: str) -> bool:
        validator = target.validator() if target is not None else None
        if validator is None:
            return True
        state, _, _ = validator.validate(text, 0)
        return state != QValidator.Invalid

    def _on_digit(self, digit: str):
        try:
            target = self._get_target()
            if target is None:
                return
            cur = target.text() or ""
            new = cur + digit
            formatted = self._format_after_append(new)
            if formatted is None:
                return
            if not self._accepts_text(target, formatted):
                return
            if formatted == "0" and "." not in new and new.strip("0") == "":
                target.setText("0")
            else:
                target.setText(formatted)
        except Exception as exc:
            try:
                from modules.ui_utils.error_logger import log_error_message
                from modules.ui_utils.dialog_utils import report_to_statusbar
                log_error_message(f"Keypad error (_on_digit): {exc}")
                wnd = getattr(self.parent, 'window', None)
                mainw = None
                try:
                    mainw = wnd() if callable(wnd) else getattr(self.parent, 'window')()
                except Exception:
                    mainw = None
                if mainw is None:
                    try:
                        # fallback: Qt widget top-level
                        mainw = self.parent.window() if hasattr(self.parent, 'window') else None
                    except Exception:
                        mainw = None
                if mainw is not None:
                    try:
                        report_to_statusbar(mainw, "Keypad input error", is_error=True, duration=2000)
                    except Exception:
                        pass
            except Exception:
                pass

    def _on_dot(self):
        try:
            target = self._get_target()
            if target is None:
                return
            cur = target.text() or ""
            if "." in cur:
                return
            new_text = "0." if cur == "" else cur + "."
            if not self._accepts_text(target, new_text):
                return
            target.setText(new_text)
        except Exception as exc:
            try:
                from modules.ui_utils.error_logger import log_error_message
                from modules.ui_utils.dialog_utils import report_to_statusbar
                log_error_message(f"Keypad error (_on_dot): {exc}")
                try:
                    mw = self.parent.window()
                    report_to_statusbar(mw, "Keypad input error", is_error=True, duration=2000)
                except Exception:
                    pass
            except Exception:
                pass

    def _on_fast_set(self, amount: float):
        try:
            fw = QApplication.focusWidget()
            if isinstance(fw, QLineEdit) and fw.objectName() == "qtyInput":
                return
            target = self._get_target()
            if target is None:
                return
            target.setText(f"{amount:.2f}")
        except Exception as exc:
            try:
                from modules.ui_utils.error_logger import log_error_message
                from modules.ui_utils.dialog_utils import report_to_statusbar
                log_error_message(f"Keypad error (_on_fast_set): {exc}")
                try:
                    mw = self.parent.window()
                    report_to_statusbar(mw, "Keypad input error", is_error=True, duration=2000)
                except Exception:
                    pass
            except Exception:
                pass

    def _on_backspace(self):
        try:
            target = self._get_target()
            if target is None:
                return
            cur = target.text() or ""
            if cur:
                target.setText(cur[:-1])
        except Exception as exc:
            try:
                from modules.ui_utils.error_logger import log_error_message
                from modules.ui_utils.dialog_utils import report_to_statusbar
                log_error_message(f"Keypad error (_on_backspace): {exc}")
                try:
                    mw = self.parent.window()
                    report_to_statusbar(mw, "Keypad input error", is_error=True, duration=2000)
                except Exception:
                    pass
            except Exception:
                pass

    def _on_clear(self):
        try:
            target = self._get_target()
            if target is None:
                return
            target.clear()
        except Exception as exc:
            try:
                from modules.ui_utils.error_logger import log_error_message
                from modules.ui_utils.dialog_utils import report_to_statusbar
                log_error_message(f"Keypad error (_on_clear): {exc}")
                try:
                    mw = self.parent.window()
                    report_to_statusbar(mw, "Keypad input error", is_error=True, duration=2000)
                except Exception:
                    pass
            except Exception:
                pass

    def _on_tab(self, reverse: bool = False):
        try:
            fw = QApplication.focusWidget()
            if isinstance(fw, QLineEdit) and fw.objectName() == "qtyInput":
                return
            target = self._get_tab_target()
            if self._tab_handler is not None and self._tab_handler(target, reverse):
                return
            if target is not None:
                target.focusNextPrevChild(not reverse)
            else:
                try:
                    self.parent.focusNextPrevChild(not reverse)
                except Exception:
                    pass
        except Exception as exc:
            try:
                from modules.ui_utils.error_logger import log_error_message
                from modules.ui_utils.dialog_utils import report_to_statusbar
                log_error_message(f"Keypad error (_on_tab): {exc}")
                try:
                    mw = self.parent.window()
                    report_to_statusbar(mw, "Keypad navigation error", is_error=True, duration=2000)
                except Exception:
                    pass
            except Exception:
                pass

    def _on_enter(self):
        try:
            fw = QApplication.focusWidget()
            if isinstance(fw, QLineEdit) and fw.objectName() == "qtyInput":
                if fw.hasAcceptableInput():
                    fw.returnPressed.emit()
                return
            allowed_buttons = {
                "cashPaySlcBtn",
                "netsPaySlcBtn",
                "paynowPaySlcBtn",
                "voucherPaySlcBtn",
                "payPayOpsBtn",
                "resetPayOpsBtn",
                "printPayOpsBtn",
                "keyVendorBtn",
                "keyRefundBtn",
            }
            if isinstance(fw, QPushButton) and fw is not self._enter_button:
                if fw.objectName() in allowed_buttons and fw.isEnabled():
                    fw.click()
                return
            if fw is self._enter_button and isinstance(self._last_button, QPushButton):
                if self._last_button.objectName() in allowed_buttons and self._last_button.isEnabled():
                    self._last_button.click()
                    return
            target = self._get_target()
            if target is None:
                return
            if target.objectName() not in {"tenderValLineEdit", "cashPayLineEdit", "netsPayLineEdit", "paynowPayLineEdit", "voucherPayLineEdit"}:
                return
            if self._enter_handler is not None and self._enter_handler(target):
                return
            if hasattr(target, "next_focus"):
                nf = getattr(target, "next_focus")
                if callable(nf):
                    nf()
                    return
                if nf is not None:
                    nf.setFocus()
                    return
        except Exception as exc:
            try:
                from modules.ui_utils.error_logger import log_error_message
                from modules.ui_utils.dialog_utils import report_to_statusbar
                log_error_message(f"Keypad error (_on_enter): {exc}")
                try:
                    mw = self.parent.window()
                    report_to_statusbar(mw, "Keypad action error", is_error=True, duration=2000)
                except Exception:
                    pass
            except Exception:
                pass
