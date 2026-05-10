"""Customer-facing display window for Screen 2."""

from __future__ import annotations

from datetime import datetime
import os
import re
import config
from typing import Iterable

from PyQt5 import uic
from PyQt5.QtCore import QTimer, Qt
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
from modules.ui_utils.error_logger import log_error_message
from modules.date_time.formatters import format_date, format_time
from config import (
    COMPANY_NAME,
    CUSTOMER_DISPLAY_AUTO_DETECT,
    CUSTOMER_DISPLAY_ENABLED,
    CUSTOMER_DISPLAY_FULLSCREEN,
    CUSTOMER_DISPLAY_IDLE_TIMEOUT,
    CUSTOMER_DISPLAY_IDLE_AD_INTERVAL,
    CUSTOMER_DISPLAY_TEST_MODE,
    CUSTOMER_DISPLAY_DATE_FMT,
    CUSTOMER_DISPLAY_TIME_FMT,
    CUSTOMER_SCREEN_HEIGHT,
    CUSTOMER_SCREEN_INDEX,
    CUSTOMER_SCREEN_WIDTH,
    ALLOWED_EXTS,
)

# Resolve project paths and assets (used to apply main QSS to this dialog)
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(THIS_DIR))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ADS_DIR = os.path.join(ASSETS_DIR, 'ads')
QSS_PATH = os.path.join(ASSETS_DIR, 'main.qss')
from modules.table.unit_helpers import canonicalize_unit, UNIT_KG, UNIT_EACH


class CustomerDisplayWindow(QDialog):
    """Secondary customer display window.

    This window is output-only and should not control cashier actions.
    """

    STATE_IDLE = "idle"
    STATE_PAYMENT = "payment"

    def __init__(self, host=None):
        super().__init__(host)
        self._host = host
        self._connected = False
        self._idle_timer = QTimer(self)
        self._clock_timer = QTimer(self)
        self._idle_ads_timer = QTimer(self)
        self._result_overlay_timer = QTimer(self)
        self._ui_loaded = False
        self._stack = None
        self._mode_stack = None
        self._table = None
        self._total_label = None
        self._count_label = None
        self._date_label = None
        self._time_label = None
        self._company_label = None
        self._qr_label = None
        self._idle_full_label = None
        self._idle_split_label = None
        self._payment_result_overlay = None
        self._result_overlay_label = None
        self._idle_ads_paths = []
        self._idle_ads_index = 0
        self._state = self.STATE_IDLE
        self._using_fallback_ui = False
        self._load_ui()
        self._apply_window_flags()
        self._cache_widgets()
        # Defensive initialization: ensure right-panel starts on idle page (index 0)
        try:
            if self._stack is not None:
                self._stack.setCurrentIndex(0)
        except Exception:
            pass
        # Ensure mode stack defaults to full idle
        try:
            if self._mode_stack is not None:
                self._mode_stack.setCurrentIndex(0)
        except Exception:
            pass
        self._configure_table()
        self._configure_qr_label()
        self._configure_idle_ads()
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()
        self.show_idle()
        if CUSTOMER_DISPLAY_AUTO_DETECT:
            self._wire_screen_events()
        self.refresh_display_visibility(initial=True)

    def _load_ui(self) -> None:
        ui_path = os.path.abspath(os.path.join(UI_DIR, 'screen2.ui'))
        try:
            if not os.path.exists(ui_path):
                raise FileNotFoundError(ui_path)
            uic.loadUi(ui_path, self)
            self._ui_loaded = True
        except Exception as exc:
            import traceback

            tb = traceback.format_exc()
            try:
                log_error_message(f"CustomerDisplay: screen2.ui load failed: {exc}\n{tb}")
            except Exception:
                pass
            report_to_statusbar(self._host, "Customer display UI missing - using fallback.", is_error=True, duration=6000)
            try:
                from modules.customer_display.fallback_screen2 import create_fallback_ui

                create_fallback_ui(self)
                self._ui_loaded = True
                self._using_fallback_ui = True
            except Exception:
                try:
                    log_error_message(f"CustomerDisplay: fallback creation failed:\n{traceback.format_exc()}")
                except Exception:
                    pass
                return
        # Apply main QSS (if present) to this dialog so Screen 2 matches app styling.
        if os.path.exists(QSS_PATH):
            try:
                with open(QSS_PATH, 'r', encoding='utf-8') as _f:
                    q = _f.read()
                if q:
                    self.setStyleSheet(q)
            except Exception:
                pass

    def _apply_window_flags(self) -> None:
        self.setWindowFlag(Qt.WindowDoesNotAcceptFocus, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

    def _safe_log(self, message: str) -> None:
        try:
            log_error_message(message)
        except Exception:
            pass

    def _cache_widgets(self) -> None:
        self._stack = self.findChild(QStackedWidget, "screen2AdDisplayStack")
        self._mode_stack = self.findChild(QStackedWidget, "screen2ModeStack")
        self._table = self.findChild(QTableWidget, "screen2SalesTable")
        self._total_label = self.findChild(QLabel, "screen2ValueLabel")
        self._count_label = self.findChild(QLabel, "screen2NumLabel")
        self._date_label = self.findChild(QLabel, "screen2DateLabel")
        self._time_label = self.findChild(QLabel, "screen2TimeLabel")
        self._company_label = self.findChild(QLabel, "screen2CompanyLabel")
        self._qr_label = self.findChild(QLabel, "screen2QrLabel")
        self._idle_full_label = self.findChild(QLabel, "screen2IdleFullLabel")
        self._idle_split_label = self.findChild(QLabel, "idleAdsLabel")
        self._payment_result_overlay = self.findChild(QFrame, "paymentResultOverlay")
        self._result_overlay_label = self.findChild(QLabel, "paymentResultLabel")

        if self._company_label is not None:
            self._company_label.setText(COMPANY_NAME)

        if self._idle_full_label is not None:
            self._idle_full_label.setAlignment(Qt.AlignCenter)
        if self._idle_split_label is not None:
            self._idle_split_label.setAlignment(Qt.AlignCenter)
            self._idle_split_label.setWordWrap(True)

    def _configure_table(self) -> None:
        table = self._table
        if table is None:
            return
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Hide vertical header (row numbers)
        vh = table.verticalHeader()
        vh.setVisible(False)

        # Ensure gridlines and a visible frame so styles aren't visually missing
        table.setShowGrid(True)
        table.setGridStyle(Qt.SolidLine)
        table.setFrameShape(QFrame.Box)
        table.setLineWidth(1)

        # Apply a readable default font for rows in case stylesheet cascade misses it
        table.setFont(QFont("Segoe UI", 16))

        header = table.horizontalHeader()
        if header is not None:
            # Ensure header is visible and has a reasonable minimum height so
            # stylesheet changes don't collapse it to zero height.
            header.setVisible(True)
            header.setMinimumHeight(36)
            header.setDefaultAlignment(Qt.AlignCenter)
            # Prefer fixed widths for Qty and Amount to control layout on screen2
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.Fixed)
            header.setStretchLastSection(False)
            # Desired fixed widths (px)
            col0_w = 160
            col2_w = 180
            table.setColumnWidth(0, col0_w)
            table.setColumnWidth(2, col2_w)

    def _configure_qr_label(self) -> None:
        if self._qr_label is None:
            return
        self._qr_label.setFixedSize(250, 250)

    def _configure_idle_ads(self) -> None:
        interval_ms = max(1000, int(CUSTOMER_DISPLAY_IDLE_AD_INTERVAL * 1000))
        self._idle_ads_timer.setInterval(interval_ms)
        self._idle_ads_timer.timeout.connect(self._advance_idle_ad)

    def _update_clock(self) -> None:
        now = datetime.now()
        if self._date_label is not None:
            self._date_label.setText(format_date(now, CUSTOMER_DISPLAY_DATE_FMT))
        if self._time_label is not None:
            self._time_label.setText(format_time(now, CUSTOMER_DISPLAY_TIME_FMT))

    def resizeEvent(self, event) -> None:
        """Keep payment result overlay synchronized with dialog resize."""
        super().resizeEvent(event)
        try:
            if self._payment_result_overlay is not None and self._payment_result_overlay.isVisible():
                self._payment_result_overlay.setGeometry(self.rect())
        except Exception:
            pass

    def _wire_screen_events(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        app.screenAdded.connect(self._handle_screen_change)
        app.screenRemoved.connect(self._handle_screen_change)

    def _show_display(self) -> None:
        if CUSTOMER_DISPLAY_FULLSCREEN:
            self.showFullScreen()
        else:
            self.resize(CUSTOMER_SCREEN_WIDTH, CUSTOMER_SCREEN_HEIGHT)
            self.show()

    def _handle_screen_change(self, *args, **kwargs) -> None:
        self.refresh_display_visibility(initial=False)

    def refresh_display_visibility(self, initial: bool = False) -> None:
        if not CUSTOMER_DISPLAY_ENABLED:
            self._connected = False
            self.hide()
            return

        if CUSTOMER_DISPLAY_TEST_MODE:
            self._connected = True
            self._show_display()
            if not initial:
                report_to_statusbar(self._host, "Customer display connected", ok=True, duration=1500)
            return

        screens = QApplication.screens()
        if len(screens) > CUSTOMER_SCREEN_INDEX:
            screen = screens[CUSTOMER_SCREEN_INDEX]
            geometry = screen.geometry()
            self.move(geometry.x(), geometry.y())
            self._connected = True
            self._show_display()
            if not initial:
                report_to_statusbar(self._host, "Customer display connected", ok=True, duration=1500)
        else:
            if self._connected or initial:
                report_to_statusbar(self._host, "Customer display disconnected", ok=True, duration=1500)
            self._connected = False
            self.hide()

    def show_idle(self) -> None:
        self.set_mode_full_idle()
        self._set_state(self.STATE_IDLE)
        self.clear_items()
        self.set_total(0.0)
        self.set_item_count(0)

    def set_mode_full_idle(self) -> None:
        if self._mode_stack is None:
            return
        try:
            self._mode_stack.setCurrentIndex(0)
        except Exception:
            pass
        self._sync_idle_ads_for_context()

    def set_mode_split(self) -> None:
        if self._mode_stack is None:
            return
        try:
            self._mode_stack.setCurrentIndex(1)
        except Exception:
            pass
        self._sync_idle_ads_for_context()

    def _active_idle_label(self) -> QLabel | None:
        if self._mode_stack is not None:
            try:
                if self._mode_stack.currentIndex() == 0:
                    return self._idle_full_label
            except Exception:
                pass
        return self._idle_split_label

    def _sync_idle_ads_for_context(self) -> None:
        """Run ad rotation only for full-idle mode or right-panel idle state."""
        if self._mode_stack is None:
            self._stop_idle_ads()
            return
        try:
            mode_idx = self._mode_stack.currentIndex()
        except Exception:
            mode_idx = 0

        if mode_idx == 0:
            self._start_idle_ads()
            return

        if mode_idx == 1 and self._state == self.STATE_IDLE:
            self._start_idle_ads()
            return

        self._stop_idle_ads()

    def _start_idle_ads(self) -> None:
        target = self._active_idle_label()
        if target is None:
            return
        # If the ads directory doesn't exist, log an error and show fallback text.
        if not os.path.isdir(ADS_DIR):
            self._safe_log(f"CustomerDisplay: ads directory not found: {ADS_DIR}")
            self._show_image_unavailable()
            return

        # Directory exists: list ad files. If none, show fallback text (no log).
        self._idle_ads_paths = self._list_idle_ad_files()
        self._idle_ads_index = 0
        if not self._idle_ads_paths:
            # No images present: show unified fallback text without logging.
            self._show_image_unavailable()
            return

        # Render first ad and start rotation if multiple images are present.
        self._render_idle_ad()
        if len(self._idle_ads_paths) > 1:
            self._idle_ads_timer.start()

    def _stop_idle_ads(self) -> None:
        self._idle_ads_timer.stop()

    def _advance_idle_ad(self) -> None:
        if not self._idle_ads_paths:
            return
        self._idle_ads_index = (self._idle_ads_index + 1) % len(self._idle_ads_paths)
        self._render_idle_ad()

    def _render_idle_ad(self) -> None:
        label = self._active_idle_label()
        if label is None:
            return
        if not self._idle_ads_paths:
            label.setText("Image not available")
            label.setPixmap(QPixmap())
            return

        path = self._idle_ads_paths[self._idle_ads_index]
        pix = QPixmap(path)
        if pix.isNull():
            self._safe_log(f"CustomerDisplay: failed to load ad image: {path}")
            self._show_image_unavailable()
            return

        size = label.size()
        if size.width() > 0 and size.height() > 0:
            scaled = pix.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            scaled = pix
        # Clear any fallback styling when an image is rendered so text remains readable
        label.setStyleSheet("")
        label.setPixmap(scaled)
        label.setText("")

    def _list_idle_ad_files(self) -> list[str]:
        try:
            names = [
                name for name in os.listdir(ADS_DIR)
                if os.path.splitext(name)[1].lower() in ALLOWED_EXTS
            ]
        except FileNotFoundError:
            return []
        except Exception:
            return []

        def sort_key(name: str) -> tuple[int, str]:
            match = re.match(r'^(\d+)_', name)
            if match:
                return int(match.group(1)), name.lower()
            return 9999, name.lower()

        names.sort(key=sort_key)
        return [os.path.join(ADS_DIR, name) for name in names]

    def _show_image_unavailable(self) -> None:
        """Show a unified, high-contrast fallback message on the full-idle label."""
        lbl = self._active_idle_label()
        if lbl is None:
            return
        lbl.setPixmap(QPixmap())
        lbl.setText("Screen active. Image not available")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        # Styling for a/b failure: brown background, sky-blue text, reduced font
        lbl.setStyleSheet(
            "color: #FFFFFF; background-color: #6F4E37; font-size: 20px; font-weight: bold; padding: 12px;"
        )
        lbl.setVisible(True)
        lbl.repaint()

    def show_payment(self) -> None:
        self._set_state(self.STATE_PAYMENT)

    def _set_state(self, state: str) -> None:
        self._state = state
        if self._stack is None:
            return
        index = {
            self.STATE_IDLE: 0,
            self.STATE_PAYMENT: 1,
        }.get(state, 0)
        self._stack.setCurrentIndex(index)
        self._sync_idle_ads_for_context()

    def clear_items(self) -> None:
        if self._table is None:
            return
        self._table.setRowCount(0)
        self.set_item_count(0)

    def set_items(self, items: Iterable[dict]) -> None:
        if self._table is None:
            return
        rows = list(items or [])
        self._table.setRowCount(len(rows))
        item_count = 0
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

            if unit == UNIT_KG:
                if qty > 0:
                    item_count += 1
            else:
                try:
                    item_count += max(0, int(round(qty)))
                except Exception:
                    pass

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
        self.set_item_count(item_count)

    def set_total(self, total: float) -> None:
        if self._total_label is None:
            return
        self._total_label.setText(self._format_money(total))

    def set_item_count(self, count: int) -> None:
        if self._count_label is None:
            return
        try:
            self._count_label.setText(str(max(0, int(count))))
        except Exception:
            self._count_label.setText("0")

    def set_qr_image(self, pixmap: QPixmap | None) -> None:
        if self._qr_label is None:
            return
        if getattr(self, '_using_fallback_ui', False):
            try:
                self._qr_label.setVisible(False)
                self._qr_label.setPixmap(QPixmap())
                self._qr_label.setText("")
            except Exception:
                pass
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

        state = payload.get("state", self.STATE_IDLE)
        items = payload.get("items", [])
        total = payload.get("total", 0.0)

        if state == self.STATE_IDLE:
            # Keep the current mode decision (full-idle vs split) from caller;
            # only set right-panel stack to idle so split mode remains visible.
            self._set_state(self.STATE_IDLE)
        elif state == self.STATE_PAYMENT:
            self.show_payment()
        else:
            self._set_state(self.STATE_IDLE)

        self.set_items(items)
        self.set_total(total)

    def show_payment_result(self, is_success: bool) -> None:
        """Display payment result overlay (success or failure message).
        
        Starts a single-shot timer to auto-hide the overlay.
        Stops any previous timer to avoid signal conflicts.
        Ensures overlay covers entire dialog and is brought to front.
        """
        if self._payment_result_overlay is None or self._result_overlay_label is None:
            return
        
        # Stop previous timer and disconnect all its signals
        try:
            self._result_overlay_timer.stop()
            self._result_overlay_timer.timeout.disconnect()
        except Exception:
            pass
        
        # Set message based on result
        message = "Payment Completed.\nThank You!" if is_success else "Payment Failed.\nPlease Retry."
        self._result_overlay_label.setText(message)
        
        # Apply styling (different colors for success vs failure)
        if is_success:
            color = "#4CAF50"  # Green for success
        else:
            color = "#F44336"  # Red for failure
        self._result_overlay_label.setStyleSheet(
            f"color: white; font-size: 36px; font-weight: bold; "
            f"background-color: {color}; padding: 30px; border-radius: 10px;"
        )
        
        # Ensure overlay fills entire parent dialog
        try:
            parent_rect = self.rect()
            self._payment_result_overlay.setGeometry(parent_rect)
        except Exception:
            pass
        
        # Show overlay and bring to front
        self._payment_result_overlay.setVisible(True)
        self._payment_result_overlay.raise_()
        self._payment_result_overlay.setFocus()
        
        # Start single-shot timer to auto-hide
        timeout_ms = max(1, int(CUSTOMER_DISPLAY_IDLE_TIMEOUT * 1000))
        self._result_overlay_timer.setSingleShot(True)
        self._result_overlay_timer.timeout.connect(self.hide_payment_result_overlay)
        self._result_overlay_timer.start(timeout_ms)

    def hide_payment_result_overlay(self) -> None:
        """Hide payment result overlay and stop/disconnect timer."""
        if self._payment_result_overlay is None:
            return
        
        self._payment_result_overlay.setVisible(False)
        
        # Stop and disconnect timer
        try:
            self._result_overlay_timer.stop()
            self._result_overlay_timer.timeout.disconnect()
        except Exception:
            pass

    @staticmethod
    def _format_money(amount) -> str:
        try:
            value = float(amount)
        except Exception:
            value = 0.0
        return f"${value:.2f}"
