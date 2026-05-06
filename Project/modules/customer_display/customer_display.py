"""Customer-facing display window for Screen 2."""

from __future__ import annotations

import os
from typing import Iterable

from PyQt5 import uic
from PyQt5.QtCore import QDateTime, QTimer, Qt
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QHeaderView,
    QLabel,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QFrame,
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

# Resolve project paths and assets (used to apply main QSS to this dialog)
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(THIS_DIR))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
QSS_PATH = os.path.join(ASSETS_DIR, 'main.qss')
from modules.table.unit_helpers import canonicalize_unit, UNIT_KG, UNIT_EACH


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
        self._time_label = None
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
        ui_path = os.path.abspath(os.path.join(UI_DIR, 'screen2.ui'))
        if not os.path.exists(ui_path):
            report_to_statusbar(self._host, "Error: screen2.ui missing.", is_error=True, duration=4000)
            return
        uic.loadUi(ui_path, self)
        self._ui_loaded = True
        # Apply main QSS (if present) to this dialog so Screen 2 matches app styling.
        try:
            if os.path.exists(QSS_PATH):
                with open(QSS_PATH, 'r', encoding='utf-8') as _f:
                    q = _f.read()
                    if q:
                        try:
                            self.setStyleSheet(q)
                        except Exception:
                            pass
        except Exception:
            pass

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
        self._time_label = self.findChild(QLabel, "screen2TimeLabel")
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

        # Hide vertical header (row numbers)
        try:
            vh = table.verticalHeader()
            vh.setVisible(False)
        except Exception:
            pass

        # Ensure gridlines and a visible frame so styles aren't visually missing
        try:
            table.setShowGrid(True)
        except Exception:
            pass
        try:
            table.setGridStyle(Qt.SolidLine)
        except Exception:
            pass
        try:
            table.setFrameShape(QFrame.Box)
            table.setLineWidth(1)
        except Exception:
            pass

        # Apply a readable default font for rows in case stylesheet cascade misses it
        try:
            table.setFont(QFont("Segoe UI", 16))
        except Exception:
            pass

        header = table.horizontalHeader()
        if header is not None:
            # Ensure header is visible and has a reasonable minimum height so
            # stylesheet changes don't collapse it to zero height.
            try:
                header.setVisible(True)
            except Exception:
                pass
            try:
                header.setMinimumHeight(36)
            except Exception:
                pass
            try:
                header.setDefaultAlignment(Qt.AlignCenter)
            except Exception:
                pass
            # Prefer fixed widths for Qty and Amount to control layout on screen2
            try:
                header.setSectionResizeMode(0, QHeaderView.Fixed)
                header.setSectionResizeMode(1, QHeaderView.Stretch)
                header.setSectionResizeMode(2, QHeaderView.Fixed)
                header.setStretchLastSection(False)
                # Desired fixed widths (px)
                col0_w = 160
                col2_w = 180
                header.resizeSection(0, col0_w)
                header.resizeSection(2, col2_w)

                # Defer enforcing exact column widths until after the widget is laid out
                def _apply_column_widths():
                    try:
                        try:
                            vpw = table.viewport().width()
                        except Exception:
                            vpw = table.width()
                        # Ensure the middle (product) column gets the remaining space
                        col1_w = max(40, vpw - col0_w - col2_w)
                        table.setColumnWidth(0, col0_w)
                        table.setColumnWidth(1, col1_w)
                        table.setColumnWidth(2, col2_w)
                    except Exception:
                        pass

                try:
                    QTimer.singleShot(0, _apply_column_widths)
                except Exception:
                    _apply_column_widths()
            except Exception:
                # Fall back to content-based sizing if fixed sizing fails
                try:
                    header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
                    header.setSectionResizeMode(1, QHeaderView.Stretch)
                    header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
                except Exception:
                    pass

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
        now = QDateTime.currentDateTime()
        if self._date_label is not None:
            self._date_label.setText(now.toString(DATE_FMT))
        if self._time_label is not None:
            self._time_label.setText(now.toString(TIME_FMT))

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
            qty_raw = item.get("quantity", 0.0)
            try:
                qty = float(qty_raw)
            except Exception:
                qty = 0.0
            desc = item.get("description", "")
            amount = item.get("amount", 0.0)
            unit = canonicalize_unit(item.get('unit', ''))

            # Format quantity for display
            if unit == UNIT_EACH:
                try:
                    qty_text = f"{int(qty)} ea"
                except Exception:
                    qty_text = f"{int(round(qty))} ea"
            elif unit == UNIT_KG:
                if qty < 1.0:
                    grams = int(round(qty * 1000))
                    qty_text = f"{grams} g"
                else:
                    s = f"{qty:.2f}".rstrip('0').rstrip('.')
                    qty_text = f"{s} kg"
            else:
                s = f"{qty:.2f}".rstrip('0').rstrip('.')
                qty_text = s

            # Create items with alignment and non-editable flags
            item_qty = QTableWidgetItem(qty_text)
            item_qty.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            item_qty.setFlags(item_qty.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(row_idx, 0, item_qty)

            item_desc = QTableWidgetItem(str(desc))
            item_desc.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            item_desc.setFlags(item_desc.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(row_idx, 1, item_desc)

            item_amt = QTableWidgetItem(self._format_money(amount))
            item_amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_amt.setFlags(item_amt.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(row_idx, 2, item_amt)
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
