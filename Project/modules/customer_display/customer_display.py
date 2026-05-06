"""Customer-facing display window for Screen 2."""

from __future__ import annotations

import os
from typing import Iterable

from PyQt5 import uic
from PyQt5.QtCore import QDateTime, QTimer, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QHeaderView,
    QLabel,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
)

from modules.ui_utils.dialog_utils import report_to_statusbar
from config import (
    COMPANY_NAME,
    CUSTOMER_DISPLAY_AUTO_DETECT,
    CUSTOMER_DISPLAY_ENABLED,
    CUSTOMER_DISPLAY_FULLSCREEN,
    CUSTOMER_DISPLAY_IDLE_TIMEOUT,
    CUSTOMER_DISPLAY_TEST_MODE,
    CUSTOMER_SCREEN_HEIGHT,
    CUSTOMER_SCREEN_INDEX,
    CUSTOMER_SCREEN_WIDTH,
    DATE_FMT,
    TIME_FMT,
)


class CustomerDisplayWindow(QDialog):
    """Secondary customer display window.

    This window is output-only and should not control cashier actions.
    """

    STATE_IDLE = "idle"
    STATE_SCANNING = "scanning"
    STATE_PAYMENT = "payment"
    STATE_COMPLETED = "completed"

    def __init__(self, host=None):
        super().__init__(host)
        self._host = host
        self._connected = False
        self._idle_timer = QTimer(self)
        self._clock_timer = QTimer(self)
        self._ui_loaded = False
        self._stack = None
        self._table = None
        self._total_label = None
        self._date_label = None
        self._company_label = None
        self._qr_label = None
        self._state = self.STATE_IDLE
        self._load_ui()
        self._apply_window_flags()
        self._cache_widgets()
        self._configure_table()
        self._configure_qr_label()
        self._start_clock()
        self.show_idle()
        if CUSTOMER_DISPLAY_AUTO_DETECT:
            self._wire_screen_events()
        self.refresh_display_visibility(initial=True)

    def _load_ui(self) -> None:
        ui_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "ui", "screen2.ui")
        )
        if not os.path.exists(ui_path):
            report_to_statusbar(self._host, "Error: screen2.ui missing.", is_error=True, duration=4000)
            return
        uic.loadUi(ui_path, self)
        self._ui_loaded = True

    def _apply_window_flags(self) -> None:
        try:
            self.setWindowFlag(Qt.WindowDoesNotAcceptFocus, True)
            self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        except Exception:
            pass

    def _cache_widgets(self) -> None:
        self._stack = self.findChild(QStackedWidget, "screen2AdDisplayStack")
        self._table = self.findChild(QTableWidget, "screen2SalesTable")
        self._total_label = self.findChild(QLabel, "screen2ValueLabel")
        self._date_label = self.findChild(QLabel, "screen2DateLabel")
        self._company_label = self.findChild(QLabel, "screen2CompanyLabel")
        self._qr_label = self.findChild(QLabel, "screen2QrLabel")

        if self._company_label is not None:
            self._company_label.setText(COMPANY_NAME)

    def _configure_table(self) -> None:
        table = self._table
        if table is None:
            return
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        header = table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

    def _configure_qr_label(self) -> None:
        if self._qr_label is None:
            return
        try:
            self._qr_label.setFixedSize(250, 250)
        except Exception:
            pass

    def _start_clock(self) -> None:
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

    def _update_clock(self) -> None:
        if self._date_label is None:
            return
        fmt = f"{DATE_FMT} {TIME_FMT}".strip()
        self._date_label.setText(QDateTime.currentDateTime().toString(fmt))

    def _wire_screen_events(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        try:
            app.screenAdded.connect(self._handle_screen_change)
            app.screenRemoved.connect(self._handle_screen_change)
        except Exception:
            pass

    def _handle_screen_change(self, *args, **kwargs) -> None:
        self.refresh_display_visibility(initial=False)

    def refresh_display_visibility(self, initial: bool = False) -> None:
        if not CUSTOMER_DISPLAY_ENABLED:
            self._connected = False
            self.hide()
            return

        if CUSTOMER_DISPLAY_TEST_MODE:
            self._connected = True
            if CUSTOMER_DISPLAY_FULLSCREEN:
                self.showFullScreen()
            else:
                self.resize(CUSTOMER_SCREEN_WIDTH, CUSTOMER_SCREEN_HEIGHT)
                self.show()
            if not initial:
                report_to_statusbar(self._host, "Customer display connected", ok=True, duration=1500)
            return

        screens = QApplication.screens()
        if len(screens) > CUSTOMER_SCREEN_INDEX:
            screen = screens[CUSTOMER_SCREEN_INDEX]
            geometry = screen.geometry()
            try:
                self.move(geometry.x(), geometry.y())
            except Exception:
                pass
            self._connected = True
            if CUSTOMER_DISPLAY_FULLSCREEN:
                self.showFullScreen()
            else:
                self.resize(CUSTOMER_SCREEN_WIDTH, CUSTOMER_SCREEN_HEIGHT)
                self.show()
            if not initial:
                report_to_statusbar(self._host, "Customer display connected", ok=True, duration=1500)
        else:
            if self._connected or initial:
                report_to_statusbar(self._host, "Customer display disconnected", ok=True, duration=1500)
            self._connected = False
            self.hide()

    def show_idle(self) -> None:
        self._set_state(self.STATE_IDLE)
        self.clear_items()
        self.set_total(0.0)

    def show_scanning(self) -> None:
        self._set_state(self.STATE_SCANNING)

    def show_payment(self) -> None:
        self._set_state(self.STATE_PAYMENT)

    def show_completed(self) -> None:
        self._set_state(self.STATE_COMPLETED)
        self._idle_timer.stop()
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self.show_idle)
        self._idle_timer.start(max(1, int(CUSTOMER_DISPLAY_IDLE_TIMEOUT * 1000)))

    def _set_state(self, state: str) -> None:
        self._state = state
        if self._stack is None:
            return
        index = {
            self.STATE_IDLE: 0,
            self.STATE_SCANNING: 1,
            self.STATE_PAYMENT: 2,
            self.STATE_COMPLETED: 3,
        }.get(state, 0)
        self._stack.setCurrentIndex(index)

    def clear_items(self) -> None:
        if self._table is None:
            return
        self._table.setRowCount(0)

    def set_items(self, items: Iterable[dict]) -> None:
        if self._table is None:
            return
        rows = list(items or [])
        self._table.setRowCount(len(rows))
        for row_idx, item in enumerate(rows):
            qty = item.get("quantity", "")
            desc = item.get("description", "")
            amount = item.get("amount", "")
            self._table.setItem(row_idx, 0, QTableWidgetItem(str(qty)))
            self._table.setItem(row_idx, 1, QTableWidgetItem(str(desc)))
            self._table.setItem(row_idx, 2, QTableWidgetItem(self._format_money(amount)))
        if rows:
            self._table.scrollToBottom()

    def set_total(self, total: float) -> None:
        if self._total_label is None:
            return
        self._total_label.setText(self._format_money(total))

    def set_qr_image(self, pixmap: QPixmap | None) -> None:
        if self._qr_label is None:
            return
        if pixmap is None or pixmap.isNull():
            self._qr_label.setText("QR CODE")
            self._qr_label.setPixmap(QPixmap())
            return
        scaled = pixmap.scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._qr_label.setPixmap(scaled)
        self._qr_label.setText("")

    def update_transaction(self, payload: dict) -> None:
        """Update customer display from clean transaction data."""
        if not payload:
            self.show_idle()
            return

        state = payload.get("state", self.STATE_SCANNING)
        items = payload.get("items", [])
        total = payload.get("total", 0.0)

        if state == self.STATE_IDLE:
            self.show_idle()
            return
        if state == self.STATE_PAYMENT:
            self.show_payment()
        elif state == self.STATE_COMPLETED:
            self.show_completed()
        else:
            self.show_scanning()

        self.set_items(items)
        self.set_total(total)

    @staticmethod
    def _format_money(amount) -> str:
        try:
            value = float(amount)
        except Exception:
            value = 0.0
        return f"${value:.2f}"
