"""sales_frame_setup.py - Controller for the sales frame UI with signal support."""
import os
from PyQt5 import uic
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import QVBoxLayout, QSizePolicy, QPushButton, QWidget, QTableWidget, QLabel

from modules.table import setup_sales_table, bind_total_label, add_total_listener
from modules.ui_utils.error_logger import log_error

ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'assets'
)


class SalesFrame(QObject):
    saleTotalChanged = pyqtSignal(float)
    holdRequested = pyqtSignal()
    viewHoldLoaded = pyqtSignal(int, float)
    cancelRequested = pyqtSignal()

    def __init__(self, main_window, placeholder, ui_path):
        super().__init__()
        self._main_window = main_window
        self._placeholder = placeholder
        self.widget = uic.loadUi(ui_path)
        self.sales_table = None
        self._total_label = None
        self._apply_styles()
        self._attach_to_placeholder()
        self._configure_widgets()

    def notify_hold_loaded(self, receipt_id: int, total: float) -> None:
        """External callers can notify the frame that a held receipt was loaded."""
        self.viewHoldLoaded.emit(receipt_id, total)

    def _apply_styles(self) -> None:
        qss_path = os.path.join(ASSETS_DIR, 'sales.qss')
        if os.path.exists(qss_path):
            try:
                with open(qss_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.widget.setStyleSheet(content)
                self._placeholder.setStyleSheet(content)
            except Exception as e:
                log_error(f"Failed to load sales.qss: {e}")

    def _attach_to_placeholder(self) -> None:
        layout = self._placeholder.layout()
        if layout is None:
            layout = QVBoxLayout(self._placeholder)
            self._placeholder.setLayout(layout)
        try:
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(10)
        except Exception:
            pass
        layout.addWidget(self.widget)

    def _configure_widgets(self) -> None:
        self._set_stretches()
        self._wire_add_buttons()
        self._wire_receipt_buttons()
        self._setup_sales_table()

    def _set_stretches(self) -> None:
        try:
            layout = self._placeholder.layout()
            layout.setStretch(0, 0)
            layout.setStretch(1, 7)
            layout.setStretch(2, 2)
            layout.setStretch(3, 2)
            layout.setStretch(4, 2)
        except Exception:
            pass

    def _wire_add_buttons(self) -> None:
        add_container = self.widget.findChild(QWidget, 'addContainer')
        if add_container is not None:
            add_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            height = self._em_px(add_container, 4.0)
            add_container.setMinimumHeight(height)
            add_container.setMaximumHeight(height)
            veg_btn = self.widget.findChild(QPushButton, 'vegBtn')
            if veg_btn is not None:
                veg_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
                veg_btn.clicked.connect(self._main_window.launch_vegetable_entry_dialog)
            manual_btn = self.widget.findChild(QPushButton, 'manualBtn')
            if manual_btn is not None:
                manual_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
                manual_btn.clicked.connect(self._main_window.launch_manual_entry_dialog)

    def _wire_receipt_buttons(self) -> None:
        receipt_container = self.widget.findChild(QWidget, 'receiptContainer')
        if receipt_container is None:
            return
        receipt_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        height = self._em_px(receipt_container, 4.0)
        receipt_container.setMinimumHeight(height)
        receipt_container.setMaximumHeight(height)

        cancelsale_btn = receipt_container.findChild(QPushButton, 'cancelsaleBtn')
        if cancelsale_btn is not None:
            cancelsale_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            cancelsale_btn.clicked.connect(self._on_cancel_clicked)

        holdsales_btn = receipt_container.findChild(QPushButton, 'holdSalesBtn')
        if holdsales_btn is not None:
            holdsales_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            holdsales_btn.clicked.connect(self._on_hold_requested)

        viewhold_btn = receipt_container.findChild(QPushButton, 'viewholdBtn')
        if viewhold_btn is not None:
            viewhold_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            viewhold_btn.clicked.connect(self._main_window.open_viewhold_panel)

    def _setup_sales_table(self) -> None:
        sale_table = self.widget.findChild(QTableWidget, 'salesTable')
        if sale_table is None:
            return
        sale_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sale_table.setMinimumHeight(self._em_px(self.widget, 10))
        setup_sales_table(sale_table)
        self.sales_table = sale_table
        setattr(self._main_window, 'sales_table', sale_table)
        total_container = self.widget.findChild(QWidget, 'totalContainer')
        if total_container is not None:
            total_label = total_container.findChild(QLabel, 'totalValue')
            if total_label is not None:
                bind_total_label(sale_table, total_label)
                add_total_listener(sale_table, self._handle_total_change)

    def _handle_total_change(self, total: float) -> None:
        self.saleTotalChanged.emit(total)

    def _on_cancel_clicked(self) -> None:
        self._main_window.open_cancelsale_dialog()

    def _on_hold_requested(self) -> None:
        self.holdRequested.emit()
        self._main_window.launch_hold_sales_dialog()

    @staticmethod
    def _em_px(widget: QWidget, units: float) -> int:
        fm = QFontMetrics(widget.font())
        return int(round(units * fm.lineSpacing()))


def setup_sales_frame(main_window, UI_DIR):
    sales_placeholder = getattr(main_window, 'salesFrame', None)
    sales_ui = os.path.join(UI_DIR, 'sales_frame.ui')
    if sales_placeholder is None or not os.path.exists(sales_ui):
        return None
    try:
        return SalesFrame(main_window, sales_placeholder, sales_ui)
    except Exception as e:
        log_error(f"Failed to initialize sales frame: {e}")
        return None
