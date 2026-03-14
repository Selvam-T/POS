import pytest
from PyQt5.QtWidgets import QApplication, QLineEdit, QPushButton, QWidget

from modules.payment.keypad_controller import KeypadController


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class PanelHarness(QWidget):
    def __init__(self):
        super().__init__()
        self.last_tab_next = None

    def focusNextPrevChild(self, next):
        self.last_tab_next = next
        return True


def _make_panel(app):
    panel = PanelHarness()

    le = QLineEdit(panel)
    le.setObjectName("tenderValLineEdit")

    btns = [
        "keyNumBtn0",
        "keyNumBtn1",
        "keyNumBtn2",
        "keyNumBtn3",
        "keyNumBtn4",
        "keyNumBtn5",
        "keyNumBtn6",
        "keyNumBtn7",
        "keyNumBtn8",
        "keyNumBtn9",
        "keyNumBtn00",
        "keyNumBtndot",
        "keyDolBtn10",
        "keyDolBtn50",
        "keyDolBtn100",
        "keyFastBtntab",
        "keyFastBtnshftab",
        "keyFastBtnclr",
        "keyFastBtnenter",
        "keyFastBtnbksp",
    ]
    for name in btns:
        b = QPushButton(panel)
        b.setObjectName(name)

    panel.show()
    app.processEvents()

    return panel, le


def _focus(app, widget):
    widget.setFocus()
    app.processEvents()


def test_digit_and_decimal_limit(app):
    panel, le = _make_panel(app)
    controller = KeypadController(panel)

    _focus(app, le)
    controller._on_digit("1")
    controller._on_dot()
    controller._on_digit("2")
    controller._on_digit("3")
    controller._on_digit("4")

    assert le.text() == "1.23"


def test_double_zero_leading(app):
    panel, le = _make_panel(app)
    controller = KeypadController(panel)

    _focus(app, le)
    controller._on_digit("00")
    assert le.text() == "0"

    controller._on_digit("0")
    assert le.text() == "0"


def test_fast_set_replaces(app):
    panel, le = _make_panel(app)
    controller = KeypadController(panel)

    _focus(app, le)
    le.setText("12")
    controller._on_fast_set(10)
    assert le.text() == "10.00"


def test_backspace_and_clear(app):
    panel, le = _make_panel(app)
    controller = KeypadController(panel)

    _focus(app, le)
    le.setText("123")
    controller._on_backspace()
    assert le.text() == "12"

    controller._on_clear()
    assert le.text() == ""


def test_readonly_skips(app):
    panel, le = _make_panel(app)
    controller = KeypadController(panel)

    le.setReadOnly(True)
    le.setText("5")
    _focus(app, le)
    controller._on_digit("1")
    assert le.text() == "5"


def test_tab_calls_parent(app):
    panel, le = _make_panel(app)
    controller = KeypadController(panel)

    _focus(app, le)
    controller._on_tab()
    assert panel.last_tab_next is True

    controller._on_tab(reverse=True)
    assert panel.last_tab_next is False


def test_enter_next_focus_callable(app):
    panel, le = _make_panel(app)
    controller = KeypadController(panel)

    called = {"ok": False}

    def _mark():
        called["ok"] = True

    le.next_focus = _mark
    _focus(app, le)
    controller._on_enter()

    assert called["ok"] is True
