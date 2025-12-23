"""
sales_frame_setup.py - Setup function for the sales frame UI in the POS system.
"""
import os
from PyQt5 import uic
from PyQt5.QtWidgets import QVBoxLayout, QSizePolicy, QPushButton, QWidget, QTableWidget, QLabel
from PyQt5.QtGui import QFontMetrics
from modules.table import setup_sales_table

def setup_sales_frame(main_window, UI_DIR):
    """
    Loads and sets up the sales frame UI, wiring up widgets and buttons.
    Sets main_window.sales_table for use elsewhere.
    """
    sales_placeholder = getattr(main_window, 'salesFrame', None)
    sales_ui = os.path.join(UI_DIR, 'sales_frame.ui')
    if sales_placeholder is not None and os.path.exists(sales_ui):
        sales_widget = uic.loadUi(sales_ui)
        # Load and apply sales.qss
        ASSETS_DIR = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'assets'
        )
        qss_path = os.path.join(ASSETS_DIR, 'sales.qss')
        if os.path.exists(qss_path):
            try:
                with open(qss_path, 'r', encoding='utf-8') as f:
                    qss_content = f.read()
                    sales_widget.setStyleSheet(qss_content)
                    sales_placeholder.setStyleSheet(qss_content)
            except Exception as e:
                print('Failed to load sales.qss:', e)
        sales_layout = sales_placeholder.layout()
        if sales_layout is None:
            sales_layout = QVBoxLayout(sales_placeholder)
            sales_placeholder.setLayout(sales_layout)
        try:
            sales_layout.setContentsMargins(8, 8, 8, 8)
            sales_layout.setSpacing(10)
        except Exception:
            pass
        sales_layout.addWidget(sales_widget)

        # Restore sales frame layout logic for table and containers
        try:
            # Children order: 0=salesLabel, 1=salesTable, 2=totalContainer, 3=addBtnLayout, 4=receiptLayout
            sales_layout.setStretch(0, 0)
            sales_layout.setStretch(1, 7)
            sales_layout.setStretch(2, 2)
            sales_layout.setStretch(3, 2)
            sales_layout.setStretch(4, 2)

            def em_px(widget: QWidget, units: float) -> int:
                fm = QFontMetrics(widget.font())
                return int(round(units * fm.lineSpacing()))

            total_container = sales_widget.findChild(QWidget, 'totalContainer')
            if total_container is not None:
                total_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                h = em_px(total_container, 3.6)
                total_container.setMinimumHeight(h)
                total_container.setMaximumHeight(h)

            add_container = sales_widget.findChild(QWidget, 'addContainer')
            if add_container is not None:
                add_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                h = em_px(add_container, 4.0)
                add_container.setMinimumHeight(h)
                add_container.setMaximumHeight(h)
                # Wire addContainer buttons to new dialog methods
                veg_btn = sales_widget.findChild(QPushButton, 'vegBtn')
                if veg_btn is not None:
                    veg_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
                    veg_btn.clicked.connect(main_window.open_vegetable_entry_dialog)
                manual_btn = sales_widget.findChild(QPushButton, 'manualBtn')
                if manual_btn is not None:
                    manual_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
                    manual_btn.clicked.connect(main_window.open_manual_panel)

            receipt_container = sales_widget.findChild(QWidget, 'receiptContainer')
            if receipt_container is not None:
                receipt_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                h = em_px(receipt_container, 4.0)
                receipt_container.setMinimumHeight(h)
                receipt_container.setMaximumHeight(h)
                # Wire receiptContainer buttons to new dialog methods
                cancelsale_btn = sales_widget.findChild(QPushButton, 'cancelsaleBtn')
                if cancelsale_btn is not None:
                    cancelsale_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
                    cancelsale_btn.clicked.connect(main_window.open_cancelsale_panel)
                onhold_btn = sales_widget.findChild(QPushButton, 'onholdBtn')
                if onhold_btn is not None:
                    onhold_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
                    onhold_btn.clicked.connect(main_window.open_onhold_panel)
                viewhold_btn = sales_widget.findChild(QPushButton, 'viewholdBtn')
                if viewhold_btn is not None:
                    viewhold_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
                    viewhold_btn.clicked.connect(main_window.open_viewhold_panel)

            sale_table = sales_widget.findChild(QTableWidget, 'salesTable')
            if sale_table is not None:
                sale_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                sale_table.setMinimumHeight(em_px(sales_widget, 10))
                setup_sales_table(sale_table)
                main_window.sales_table = sale_table
                # Now bind the totalValue label to the sales table for automatic updates
                if total_container is not None:
                    total_label = total_container.findChild(QLabel, 'totalValue')
                    if total_label is not None:
                        from modules.table import bind_total_label
                        bind_total_label(sale_table, total_label)
        except Exception:
            pass
