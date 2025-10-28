#!/usr/bin/env python3
"""
POS System - UI loader that composes `main_window.ui`, `sales_frame.ui`, and `payment_frame.ui`.
Loads a QSS file from `assets/style.qss` when present.
"""

import sys
import os
from PyQt5 import uic
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLineEdit,
    QLabel,
    QDialog,
)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtGui import QFontMetrics
from logic.salesTable import setup_sales_table


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')


def load_qss(app):
    qss_path = os.path.join(ASSETS_DIR, 'style.qss')
    if os.path.exists(qss_path):
        try:
            with open(qss_path, 'r', encoding='utf-8') as f:
                app.setStyleSheet(f.read())
                print('Applied QSS from', qss_path)
        except Exception as e:
            print('Failed to load QSS:', e)


class MainLoader(QMainWindow):
    def __init__(self):
        super().__init__()
        main_ui = os.path.join(UI_DIR, 'main_window.ui')
        uic.loadUi(main_ui, self)

        # Ensure horizontal spacing between the window and central content
        # (set here rather than in the .ui to avoid XML type issues)
        layout = getattr(self, 'mainWindowLayout', None)
        if layout is not None:
            try:
                layout.setContentsMargins(12, 6, 12, 6)
            except Exception:
                # Fail silently; margins are not critical
                pass

        # Make titleBar behave: left column takes available space, burgerBtn takes only needed size
        titleBar = getattr(self, 'titleBar', None)
        burger = getattr(self, 'burgerBtn', None)
        # Prefer titleBar stretch so the left section expands
        if titleBar is not None:
            try:
                titleBar.setStretch(0, 1)
            except Exception:
                pass

        if burger is not None:
            try:
                # Let QSS control button sizing via min/max constraints
                burger.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
            except Exception:
                pass

        # Insert sales_frame.ui into placeholder named 'salesFrame' if present
        sales_placeholder = getattr(self, 'salesFrame', None)
        sales_ui = os.path.join(UI_DIR, 'sales_frame.ui')
        if sales_placeholder is not None and os.path.exists(sales_ui):
            sales_widget = uic.loadUi(sales_ui)
            # Ensure the placeholder has a layout
            layout = sales_placeholder.layout()
            if layout is None:
                layout = QVBoxLayout(sales_placeholder)
                sales_placeholder.setLayout(layout)
            # Keep consistent frame margins so headers align
            try:
                layout.setContentsMargins(8, 8, 8, 8)
            except Exception:
                pass
            # Set proportional vertical space for SalesFrame children and apply em-based heights
            try:
                from PyQt5.QtWidgets import QVBoxLayout as _QVBoxLayout, QWidget as _QWidget, QPushButton as _QPushButton
                main_sales_layout = sales_widget.findChild(_QVBoxLayout, 'mainSalesLayout')
                if main_sales_layout is not None:
                    # Keep inter-item spacing of 10px
                    main_sales_layout.setSpacing(10)
                    # Children order: 0=salesLabel, 1=salesTable, 2=totalContainer, 3=addBtnLayout, 4=receiptLayout
                    # Stretch factors define relative proportions for extra space.
                    # Label stays fixed (0); others share 7:2:2:2 by default.
                    main_sales_layout.setStretch(0, 0)
                    main_sales_layout.setStretch(1, 7)
                    main_sales_layout.setStretch(2, 2)
                    main_sales_layout.setStretch(3, 2)
                    main_sales_layout.setStretch(4, 2)
                # Helper to convert em to px based on current font metrics
                def em_px(widget: QWidget, units: float) -> int:
                    fm = QFontMetrics(widget.font())
                    # Use line spacing for a slightly roomier baseline than raw ascent+descent
                    return int(round(units * fm.lineSpacing()))

                # Ensure the totals container can expand vertically when stretch allocates space
                total_container = sales_widget.findChild(_QWidget, 'totalContainer')
                if total_container is not None:
                    total_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                    h = em_px(total_container, 3.6)  # increased height ~3.6em
                    total_container.setMinimumHeight(h)
                    total_container.setMaximumHeight(h)

                # Add row container: control height in em and let buttons fill
                add_container = sales_widget.findChild(_QWidget, 'addContainer')
                if add_container is not None:
                    add_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                    h = em_px(add_container, 4.0)  # unify with receipt and increase size
                    add_container.setMinimumHeight(h)
                    add_container.setMaximumHeight(h)
                    # Ensure buttons expand vertically to fill container
                    for btn_name in ('vegBtn', 'manualBtn'):
                        btn = sales_widget.findChild(_QPushButton, btn_name)
                        if btn is not None:
                            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

                # Receipt row container: control height in em
                receipt_container = sales_widget.findChild(_QWidget, 'receiptContainer')
                if receipt_container is not None:
                    receipt_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                    h = em_px(receipt_container, 4.0)  # match addContainer height
                    receipt_container.setMinimumHeight(h)
                    receipt_container.setMaximumHeight(h)
                    # Let action buttons fill vertically
                    for btn_name in ('cancelsaleBtn', 'onholdBtn', 'viewholdBtn'):
                        btn = sales_widget.findChild(_QPushButton, btn_name)
                        if btn is not None:
                            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

                # Give the table a reasonable minimum (in em) but let stretch control extra space
                sale_table = sales_widget.findChild(_QWidget, 'salesTable')
                if sale_table is not None:
                    sale_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                    sale_table.setMinimumHeight(em_px(sales_widget, 10))
            except Exception:
                # Non-fatal; layout will fall back to intrinsic sizes
                pass
            layout.addWidget(sales_widget)

            # Configure the Sales table headers and insert a placeholder row
            try:
                setup_sales_table(sales_widget)
            except Exception as e:
                print('Sales table setup failed:', e)

            # Wire up the "Add Vegetables" button to open the vegetable panel
            try:
                veg_btn = sales_widget.findChild(QPushButton, 'vegBtn')
                if veg_btn is not None:
                    veg_btn.clicked.connect(self.open_vegetable_panel)
            except Exception as e:
                print('Failed to wire vegBtn:', e)

        # Insert payment_frame.ui into placeholder named 'paymentFrame' if present
        payment_placeholder = getattr(self, 'paymentFrame', None)
        payment_ui = os.path.join(UI_DIR, 'payment_frame.ui')
        if payment_placeholder is not None and os.path.exists(payment_ui):
            payment_widget = uic.loadUi(payment_ui)
            layout = payment_placeholder.layout()
            if layout is None:
                layout = QVBoxLayout(payment_placeholder)
                payment_placeholder.setLayout(layout)
            try:
                layout.setContentsMargins(8, 8, 8, 8)
            except Exception:
                pass
            layout.addWidget(payment_widget)

    # ----------------- Vegetable panel wiring -----------------

    # ----------------- Vegetable panel wiring -----------------
    def open_vegetable_panel(self):
        """Open the Add Vegetable panel as a modal dialog:
        - Size = 60% of main window, centered
        - Dim the main window background while open
        - Only Close (X) button shown (no minimize/maximize)
        - Close on X, OK, or CANCEL; restore brightness on close
        """
        veg_ui = os.path.join(UI_DIR, 'vegetable.ui')
        if not os.path.exists(veg_ui):
            print('vegetable.ui not found at', veg_ui)
            return

        # Create dimming overlay over the main window
        try:
            if not hasattr(self, '_dimOverlay') or self._dimOverlay is None:
                self._dimOverlay = QWidget(self)
                self._dimOverlay.setObjectName('dimOverlay')
                self._dimOverlay.setStyleSheet('#dimOverlay { background-color: rgba(0, 0, 0, 110); }')
                self._dimOverlay.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self._dimOverlay.setGeometry(self.rect())
            self._dimOverlay.show()
            self._dimOverlay.raise_()
        except Exception:
            pass

        # Build a modal dialog and embed the loaded UI inside
        try:
            content = uic.loadUi(veg_ui)
        except Exception as e:
            print('Failed to load vegetable.ui:', e)
            try:
                self._dimOverlay.hide()
            except Exception:
                pass
            return

        dlg = QDialog(self)
        dlg.setModal(True)
        dlg.setWindowTitle('Digital Weight Input')
        # Window flags: remove min/max, keep title + close
        dlg.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        # Fixed size at 60% of main window, centered
        try:
            mw = self.frameGeometry().width()
            mh = self.frameGeometry().height()
            dw = max(400, int(mw * 0.6))
            dh = max(300, int(mh * 0.6))
            dlg.setFixedSize(dw, dh)
            # Center relative to main window
            mx = self.frameGeometry().x()
            my = self.frameGeometry().y()
            dlg.move(mx + (mw - dw) // 2, my + (mh - dh) // 2)
        except Exception:
            pass

        # Install content into dialog
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(content)

        # Configure the vegetable table headers and behavior
        try:
            vtable: QTableWidget = content.findChild(QTableWidget, 'vegetableTable')
            if vtable is not None:
                vtable.setColumnCount(4)
                vtable.setHorizontalHeaderLabels(['No.', 'Item', 'Weight (kg)', 'Total'])

                header: QHeaderView = vtable.horizontalHeader()
                header.setStretchLastSection(False)
                header.setSectionResizeMode(0, QHeaderView.Fixed)   # No.
                header.setSectionResizeMode(1, QHeaderView.Stretch) # Item grows
                header.setSectionResizeMode(2, QHeaderView.Fixed)   # Weight
                header.setSectionResizeMode(3, QHeaderView.Fixed)   # Total
                header.resizeSection(0, 48)
                header.resizeSection(2, 120)
                header.resizeSection(3, 110)

                vtable.setAlternatingRowColors(True)
                vtable.setEditTriggers(QTableWidget.NoEditTriggers)
                vtable.setSelectionBehavior(QTableWidget.SelectRows)
                vtable.setSelectionMode(QTableWidget.SingleSelection)
        except Exception as e:
            print('Vegetable table setup failed:', e)

        # Wire keypad buttons to update message label and close on OK/CANCEL
        try:
            msg: QLabel = content.findChild(QLabel, 'messageLabel')
            for name in (
                'btnVegTomato','btnVegPotato','btnVegOnion','btnVegCarrot',
                'btnVegCabbage','btnVegSpinach','btnVegCucumber','btnVegPumpkin',
                'btnVegCapsicum','btnVegBeetroot','btnVegRadish','btnVegPeas',
                'btnVegOkra','btnVegCauliflower',
            ):
                btn = content.findChild(QPushButton, name)
                if btn is not None and msg is not None:
                    btn.clicked.connect(lambda _, b=btn: msg.setText(f"Selected: {b.text()}"))

            ok_btn = content.findChild(QPushButton, 'btnOK')
            cancel_btn = content.findChild(QPushButton, 'btnCancel')
            if ok_btn is not None:
                ok_btn.clicked.connect(lambda: dlg.accept())
            if cancel_btn is not None:
                cancel_btn.clicked.connect(lambda: dlg.reject())
        except Exception as e:
            print('Vegetable keypad wiring failed:', e)

        # Ensure overlay hides and focus returns when dialog closes
        def _cleanup_overlay(_code):
            try:
                if hasattr(self, '_dimOverlay') and self._dimOverlay is not None:
                    self._dimOverlay.hide()
            except Exception:
                pass
            # Bring main window back to front
            try:
                self.raise_()
                self.activateWindow()
            except Exception:
                pass

        dlg.finished.connect(_cleanup_overlay)

        # Execute modally
        dlg.exec_()


def main():
    app = QApplication(sys.argv)
    load_qss(app)
    window = MainLoader()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
