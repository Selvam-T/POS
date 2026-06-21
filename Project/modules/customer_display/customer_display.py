"""Customer-facing display window for Screen 2."""

from __future__ import annotations

from datetime import datetime
import os
import re
import config
from typing import Iterable

from PyQt5 import uic
from PyQt5.QtCore import QTimer, Qt, QFileSystemWatcher
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
from modules.runtime_data import ensure_ads_dir
from modules.runtime_paths import load_stylesheet, stylesheet_path, ui_path
from modules.date_time.formatters import format_date, format_time
from modules.menu.greeting_menu import _load_greeting
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
    GREETING_STRINGS,
    GREETING_SELECTED,
    ADS_DIR,
)

QSS_PATH = stylesheet_path('main.qss')
from modules.table.unit_helpers import canonicalize_unit, UNIT_KG, UNIT_EACH
try:
    from modules.payment import qr_generator as qr_generator
except Exception:
    qr_generator = None


QR_WIDTH_RATIO = 0.67
QR_HEIGHT_RATIO = 0.57
QR_FALLBACK_SIZE = max(
    1,
    round(min(((CUSTOMER_SCREEN_WIDTH - 40) / 2) * QR_WIDTH_RATIO, (CUSTOMER_SCREEN_HEIGHT - 20) * QR_HEIGHT_RATIO)),
)


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
        self._ads_watcher = QFileSystemWatcher(self)
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
        self._qr_frame = None
        self._right_frame = None
        self._qr_pixmap = None
        self._qr_ref = None
        self._qr_target_size = 0
        self._idle_full_label = None
        self._payment_result_overlay = None
        self._result_overlay_label = None
        self._payment_result_card = None
        self._payment_result_title = None
        self._payment_result_subtitle = None
        self._payment_result_total = None
        self._payment_result_greeting = None
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
        self._wire_ads_watcher()
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()
        self.show_idle()
        if CUSTOMER_DISPLAY_AUTO_DETECT:
            self._wire_screen_events()
        self.refresh_display_visibility(initial=True)

    def _load_ui(self) -> None:
        ui_file = ui_path('screen2.ui')
        try:
            if not os.path.exists(ui_file):
                raise FileNotFoundError(ui_file)
            uic.loadUi(ui_file, self)
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
                q = load_stylesheet(QSS_PATH)
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
        self._qr_frame = self.findChild(QFrame, "screen2QrFrame")
        self._right_frame = self.findChild(QFrame, "screen2RightFrame")
        self._idle_full_label = self.findChild(QLabel, "screen2IdleFullLabel")
        self._payment_result_overlay = self.findChild(QFrame, "paymentResultOverlay")
        self._result_overlay_label = self.findChild(QLabel, "paymentResultLabel")
        # New card-based overlay widgets (Lightbox)
        self._payment_result_card = self.findChild(QFrame, "paymentResultCard")
        self._payment_result_title = self.findChild(QLabel, "paymentResultTitle")
        self._payment_result_subtitle = self.findChild(QLabel, "paymentResultSubtitle")
        self._payment_result_total = self.findChild(QLabel, "paymentResultTotal")
        self._payment_result_greeting = self.findChild(QLabel, "paymentResultGreeting")

        if self._company_label is not None:
            self._company_label.setText(COMPANY_NAME)

        if self._idle_full_label is not None:
            self._idle_full_label.setAlignment(Qt.AlignCenter)
            self._idle_full_label.setScaledContents(False)

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
        self._qr_label.setAlignment(Qt.AlignCenter)
        self._apply_qr_label_size()

    def _get_qr_display_size(self) -> int:
        frame = self._right_frame or self._qr_frame
        if frame is None:
            return QR_FALLBACK_SIZE

        width = frame.width()
        height = frame.height()
        if width <= 0 or height <= 0:
            return QR_FALLBACK_SIZE

        return max(1, round(min(width * QR_WIDTH_RATIO, height * QR_HEIGHT_RATIO)))

    def _apply_qr_label_size(self) -> int:
        size = self._get_qr_display_size()
        if self._qr_label is not None:
            self._qr_label.setFixedSize(size, size)
        return size

    def _configure_idle_ads(self) -> None:
        try:
            ensure_ads_dir(ADS_DIR)
        except Exception as exc:
            log_error_message(f"Customer display ad directory creation failed: {exc}")
        interval_ms = max(1000, int(CUSTOMER_DISPLAY_IDLE_AD_INTERVAL * 1000))
        self._idle_ads_timer.setInterval(interval_ms)
        self._idle_ads_timer.timeout.connect(self._advance_idle_ad)

    def _wire_ads_watcher(self) -> None:
        try:
            if os.path.isdir(ADS_DIR):
                self._ads_watcher.addPath(ADS_DIR)
        except Exception:
            pass
        try:
            self._ads_watcher.directoryChanged.connect(self._handle_ads_directory_change)
        except Exception:
            pass

    def _handle_ads_directory_change(self, *args) -> None:
        # Keep only the live full-idle screen synchronized; split mode already
        # shows the payment page and will rescan when it returns to idle.
        try:
            if self._mode_stack is None or self._mode_stack.currentIndex() != 0:
                return
        except Exception:
            return
        self._refresh_idle_ads_from_disk(preserve_current=True)

    def _update_clock(self) -> None:
        now = datetime.now()
        if self._date_label is not None:
            self._date_label.setText(format_date(now, CUSTOMER_DISPLAY_DATE_FMT))
        if self._time_label is not None:
            self._time_label.setText(format_time(now, CUSTOMER_DISPLAY_TIME_FMT))

    def resizeEvent(self, event) -> None:
        """Keep payment result overlay synchronized with dialog resize."""
        super().resizeEvent(event)
        QTimer.singleShot(0, self._refresh_qr_for_current_size)
        QTimer.singleShot(0, self._refresh_idle_ad_for_current_size)
        try:
            if self._payment_result_overlay is not None and self._payment_result_overlay.isVisible():
                self._payment_result_overlay.setGeometry(self.rect())
        except Exception:
            pass

    def _refresh_qr_for_current_size(self) -> None:
        if self._qr_label is None:
            return
        size = self._apply_qr_label_size()
        if self._qr_pixmap is not None and not self._qr_pixmap.isNull() and size != self._qr_target_size:
            self.generate_and_set_qr(self._qr_ref, size=size)
        else:
            self.set_qr_image(self._qr_pixmap)

    def _refresh_idle_ad_for_current_size(self) -> None:
        if self._idle_full_label is None or not self._idle_ads_paths:
            return
        try:
            if self._mode_stack is None or self._mode_stack.currentIndex() != 0:
                return
        except Exception:
            return
        self._render_idle_ad()

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
                report_to_statusbar(self._host, "Customer display connected", is_error=False, duration=1500)
            return

        screens = QApplication.screens()
        if len(screens) > CUSTOMER_SCREEN_INDEX:
            screen = screens[CUSTOMER_SCREEN_INDEX]
            geometry = screen.geometry()
            self.move(geometry.x(), geometry.y())
            self._connected = True
            self._show_display()
            if not initial:
                report_to_statusbar(self._host, "Customer display connected", is_error=False, duration=1500)
        else:
            if self._connected or initial:
                report_to_statusbar(self._host, "Customer display disconnected", is_error=False, duration=1500)
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

    def _sync_idle_ads_for_context(self) -> None:
        """Run ad rotation only for full-idle mode."""
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

        self._stop_idle_ads()

    def _current_idle_ad_path(self) -> str | None:
        try:
            if self._idle_ads_paths and 0 <= self._idle_ads_index < len(self._idle_ads_paths):
                return self._idle_ads_paths[self._idle_ads_index]
        except Exception:
            pass
        return None

    def _refresh_idle_ads_from_disk(self, *, preserve_current: bool = True, advance: bool = False) -> None:
        target = self._idle_full_label
        if target is None:
            return

        try:
            mode_idx = self._mode_stack.currentIndex() if self._mode_stack is not None else 1
        except Exception:
            mode_idx = 1
        if mode_idx != 0:
            return

        if not os.path.isdir(ADS_DIR):
            self._idle_ads_paths = []
            self._idle_ads_index = 0
            self._stop_idle_ads()
            self._show_image_unavailable()
            return

        new_paths = self._list_idle_ad_files()
        if not new_paths:
            self._idle_ads_paths = []
            self._idle_ads_index = 0
            self._stop_idle_ads()
            self._show_image_unavailable()
            return

        previous_path = self._current_idle_ad_path()
        self._idle_ads_paths = new_paths

        if advance:
            if previous_path in new_paths:
                self._idle_ads_index = (new_paths.index(previous_path) + 1) % len(new_paths)
            else:
                self._idle_ads_index = min(self._idle_ads_index + 1, len(new_paths) - 1)
        elif preserve_current and previous_path in new_paths:
            self._idle_ads_index = new_paths.index(previous_path)
        else:
            self._idle_ads_index = min(self._idle_ads_index, len(new_paths) - 1)

        self._render_idle_ad()

        if len(new_paths) > 1:
            self._idle_ads_timer.start()
        else:
            self._stop_idle_ads()

    def _start_idle_ads(self) -> None:
        target = self._idle_full_label
        if target is None:
            return
        # Reload from disk so newly added, removed, or reordered images are reflected immediately.
        self._idle_ads_index = 0
        self._refresh_idle_ads_from_disk(preserve_current=False)

    def _stop_idle_ads(self) -> None:
        self._idle_ads_timer.stop()

    def _advance_idle_ad(self) -> None:
        self._refresh_idle_ads_from_disk(preserve_current=True, advance=True)

    def _render_idle_ad(self) -> None:
        label = self._idle_full_label
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
        lbl = self._idle_full_label
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
            self.STATE_PAYMENT: 0,
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
        size = self._apply_qr_label_size()
        scaled = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._qr_label.setPixmap(scaled)
        self._qr_label.setText("")

    def generate_and_set_qr(self, ref: str | None = None, size: int | None = None) -> None:
        """Generate a QR pixmap via `modules.payment.qr_generator` and set it.

        If the generator is unavailable, falls back to clearing the label.
        """
        if qr_generator is None:
            try:
                self._qr_label.setText("QR CODE")
                self._qr_label.setPixmap(QPixmap())
            except Exception:
                pass
            return

        try:
            target_size = size or self._apply_qr_label_size()
            pix = qr_generator.generate_qr_pixmap(ref, target_size=target_size)
            self._qr_pixmap = pix
            self._qr_ref = ref
            self._qr_target_size = target_size
            self.set_qr_image(pix)
        except Exception:
            try:
                self._qr_label.setText("QR CODE")
                self._qr_label.setPixmap(QPixmap())
            except Exception:
                pass

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
            # Generate and display QR for the payment page.
            try:
                self.generate_and_set_qr()
            except Exception:
                pass
        else:
            self._set_state(self.STATE_IDLE)

        self.set_items(items)
        self.set_total(total)

    def show_payment_result(self, total: float | None = None, greeting: str | None = None) -> None:
        """Display the success payment overlay with optional total and greeting.
        
        Args:
            total: Optional transaction total to display on success.
            greeting: Optional greeting text; defaults to GREETING_SELECTED from config.
        
        Starts a single-shot timer to auto-hide the overlay.
        Stops any previous timer to avoid signal conflicts.
        Ensures overlay covers entire dialog and is brought to front.
        """
        if self._payment_result_overlay is None:
            return
        
        # Stop previous timer and disconnect all its signals
        try:
            self._result_overlay_timer.stop()
            self._result_overlay_timer.timeout.disconnect()
        except Exception:
            pass
        
        result_status = "success"
        title_text = "Payment is successful."
        subtitle_text = "Thank you for your purchase."
        footer_text = _load_greeting() or GREETING_SELECTED or "Thanks for shopping with us!"
        
        if self._payment_result_card is not None:
            # Set card status then repolish the card first so QSS selectors
            # that depend on [status="..."] apply before we refresh child widgets.
            self._payment_result_card.setProperty("status", result_status)
            self._refresh_widget_style(self._payment_result_card)

        # Populate title
        if self._payment_result_title is not None:
            self._payment_result_title.setText(title_text)

        if self._payment_result_subtitle is not None:
            self._payment_result_subtitle.setText(subtitle_text)
            self._payment_result_subtitle.setVisible(True)
        
        # Populate total (show if provided)
        if self._payment_result_total is not None:
            self._payment_result_total.setStyleSheet("background: transparent;")
            if total is not None:
                try:
                    total_val = float(total)
                    self._payment_result_total.setText(f"$ {total_val:.2f}")
                    self._payment_result_total.setVisible(True)
                except Exception:
                    self._payment_result_total.setVisible(False)
            else:
                self._payment_result_total.setVisible(False)
        
        # Populate greeting
        if self._payment_result_greeting is not None:
            self._payment_result_greeting.setVisible(True)
            self._payment_result_greeting.setStyleSheet("background: transparent;")
            greeting_text = footer_text if greeting is None else greeting
            self._payment_result_greeting.setText(greeting_text)

        # Now that all child text values are set, repolish children so their
        # colors/styles resolve against the updated card status.
        self._refresh_widget_style(self._payment_result_title)
        self._refresh_widget_style(self._payment_result_subtitle)
        self._refresh_widget_style(self._payment_result_total)
        self._refresh_widget_style(self._payment_result_greeting)
        # Finally repolish the card again to ensure border/style applied.
        self._refresh_widget_style(self._payment_result_card)
        # As a fallback, ensure the card paints an opaque white background
        # at runtime in case stylesheet ordering prevents QSS from taking effect.
        try:
            if self._payment_result_card is not None:
                from PyQt5.QtGui import QPalette, QColor
                # Ensure widget paints its own background (not transparent)
                self._payment_result_card.setAttribute(Qt.WA_StyledBackground, True)
                self._payment_result_card.setAutoFillBackground(True)
                pal = self._payment_result_card.palette()
                pal.setColor(QPalette.Window, QColor(255, 255, 255))
                self._payment_result_card.setPalette(pal)
                # Ensure child labels are transparent so they render over the
                # card rather than painting their own backgrounds.
                for lbl in (
                    self._payment_result_title,
                    self._payment_result_subtitle,
                    self._payment_result_total,
                    self._payment_result_greeting,
                ):
                    try:
                        if lbl is not None:
                            lbl.setStyleSheet("background: transparent;")
                            try:
                                lbl.setAutoFillBackground(False)
                            except Exception:
                                pass
                    except Exception:
                        pass
                # Force an explicit inline white background style on the card
                # to override any transparency/parent background issues.
                # Do NOT set border inline so QSS status selectors can control border color.
                self._payment_result_card.setStyleSheet(
                    "QFrame#paymentResultCard { "
                    "background-color: white; "
                    "border-radius: 12px; "
                    "padding: 12px; "
                    "}"
                )
                self._payment_result_card.update()
        except Exception:
            pass

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

    def show_hold_result_message(self, duration_ms: int = 1000) -> None:
        """Briefly acknowledge a held receipt before returning to idle ads."""
        if self._payment_result_overlay is None:
            return

        try:
            self._result_overlay_timer.stop()
            self._result_overlay_timer.timeout.disconnect()
        except Exception:
            pass

        if self._payment_result_card is not None:
            self._payment_result_card.setProperty("status", "success")
            self._refresh_widget_style(self._payment_result_card)

        if self._payment_result_title is not None:
            self._payment_result_title.setText("Receipts placed on hold")

        if self._payment_result_subtitle is not None:
            self._payment_result_subtitle.setText("")
            self._payment_result_subtitle.setVisible(False)

        if self._payment_result_total is not None:
            self._payment_result_total.setText("")
            self._payment_result_total.setVisible(False)

        if self._payment_result_greeting is not None:
            self._payment_result_greeting.setText("")
            self._payment_result_greeting.setVisible(False)

        self._refresh_widget_style(self._payment_result_title)
        self._refresh_widget_style(self._payment_result_subtitle)
        self._refresh_widget_style(self._payment_result_total)
        self._refresh_widget_style(self._payment_result_greeting)
        self._refresh_widget_style(self._payment_result_card)

        try:
            self._payment_result_overlay.setGeometry(self.rect())
        except Exception:
            pass

        self._payment_result_overlay.setVisible(True)
        self._payment_result_overlay.raise_()

        self._result_overlay_timer.setSingleShot(True)
        self._result_overlay_timer.timeout.connect(self.hide_payment_result_overlay)
        self._result_overlay_timer.start(max(1, int(duration_ms)))

    def _refresh_widget_style(self, widget) -> None:
        if widget is None:
            return
        try:
            style = widget.style()
            style.unpolish(widget)
            style.polish(widget)
            widget.update()
        except Exception:
            pass

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

    def keep_payment_result_overlay_visible(self) -> None:
        """Keep the current payment result overlay visible until explicitly hidden."""
        if self._payment_result_overlay is None:
            return
        try:
            self._result_overlay_timer.stop()
            self._result_overlay_timer.timeout.disconnect()
        except Exception:
            pass
        try:
            self._payment_result_overlay.setVisible(True)
            self._payment_result_overlay.raise_()
        except Exception:
            pass

    @staticmethod
    def _format_money(amount) -> str:
        try:
            value = float(amount)
        except Exception:
            value = 0.0
        return f"${value:.2f}"
