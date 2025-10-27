#!/usr/bin/env python3
"""
POS System - UI loader that composes `main_window.ui`, `sales_frame.ui`, and `payment.ui`.
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
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLineEdit,
)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtGui import QFontMetrics


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
                self.setup_sales_table(sales_widget)
            except Exception as e:
                print('Sales table setup failed:', e)

        # Insert payment.ui into placeholder named 'paymentFrame' if present
        payment_placeholder = getattr(self, 'paymentFrame', None)
        payment_ui = os.path.join(UI_DIR, 'payment.ui')
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

    # ----------------- Sales table setup and helpers -----------------
    def setup_sales_table(self, sales_widget: QWidget):
        """Configure headers and add a sample placeholder row. Rows can be
        regenerated dynamically by calling self.set_sales_rows(data).

                Columns (0..5):
                    0 No. (row number)
                    1 Product (text)
                    2 Quantity (editable input)
                    3 Unit Price (non-editable)
                    4 Total (calculated/non-editable)
                    5 Del (Remove button X)
        """
        table: QTableWidget = sales_widget.findChild(QTableWidget, 'salesTable')
        if table is None:
            return

        # Ensure 6 columns and set headers
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(['No.', 'Product', 'Quantity', 'Unit Price', 'Total', 'Del'])

        # Resize behavior and widths (approximate the mockup proportions)
        header: QHeaderView = table.horizontalHeader()
        header.setStretchLastSection(False)
        # Set fixed-like widths to correspond to mockup behavior
        header.setSectionResizeMode(0, QHeaderView.Fixed)            # No.
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Product
        header.setSectionResizeMode(2, QHeaderView.Fixed)            # Quantity
        header.setSectionResizeMode(3, QHeaderView.Fixed)            # Unit Price
        header.setSectionResizeMode(4, QHeaderView.Fixed)            # Total
        header.setSectionResizeMode(5, QHeaderView.Fixed)            # Del
        # Apply pixel widths approximated from the HTML mockup
        header.resizeSection(0, 48)   # No.
        header.resizeSection(2, 80)   # Qty (input ~60px + padding)
        header.resizeSection(3, 100)  # Unit Price
        header.resizeSection(4, 110)  # Total
        header.resizeSection(5, 48)   # Del (X)

        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)  # disable direct item edits
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)

        # Add one placeholder row (values are placeholders; real code should call set_sales_rows)
        placeholder = [{
            'product': 'Apple',
            'quantity': 2,
            'unit_price': 1.50,
        }]
        self.set_sales_rows(table, placeholder)

    def set_sales_rows(self, table: QTableWidget, rows: list):
        """Replace table rows with provided data.
        rows: list of dicts with keys: product (str), quantity (int/float), unit_price (float)
        """
        table.setRowCount(0)
        for r, data in enumerate(rows):
            table.insertRow(r)

            # Col 0: Row number (non-editable)
            item_no = QTableWidgetItem(str(r + 1))
            item_no.setTextAlignment(Qt.AlignCenter)
            item_no.setFlags(item_no.flags() & ~Qt.ItemIsEditable)
            table.setItem(r, 0, item_no)

            # Col 1: Product name (non-editable item)
            item_product = QTableWidgetItem(str(data.get('product', '')))
            item_product.setFlags(item_product.flags() & ~Qt.ItemIsEditable)
            table.setItem(r, 1, item_product)

            # Col 2: Quantity (QLineEdit to match QSS qtyInput styling)
            qty_val = data.get('quantity', 0)
            qty_edit = QLineEdit(str(qty_val))
            qty_edit.setObjectName('qtyInput')  # styled via QSS
            qty_edit.setAlignment(Qt.AlignCenter)
            # Recalculate total when quantity changes
            qty_edit.textChanged.connect(lambda _t, row=r: self._recalc_row_total(table, row))
            table.setCellWidget(r, 2, qty_edit)

            # Col 3: Unit Price (non-editable item)
            price_val = float(data.get('unit_price', 0.0))
            item_price = QTableWidgetItem(f"{price_val:.2f}")
            item_price.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_price.setFlags(item_price.flags() & ~Qt.ItemIsEditable)
            table.setItem(r, 3, item_price)

            # Col 4: Total (non-editable item)
            total = float(qty_val) * float(price_val)
            item_total = QTableWidgetItem(f"{total:.2f}")
            item_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_total.setFlags(item_total.flags() & ~Qt.ItemIsEditable)
            table.setItem(r, 4, item_total)

            # Col 5: Remove button (square X)
            btn = QPushButton('X')
            btn.setObjectName('removeBtn')  # styled via QSS
            try:
                btn.setFixedSize(28, 28)
            except Exception:
                pass
            btn.clicked.connect(lambda _, row=r: self._remove_table_row(table, row))
            table.setCellWidget(r, 5, btn)

        # Ensure at least one empty row exists when no data provided (placeholder)
        if not rows:
            table.setRowCount(1)
            # No.
            item_no = QTableWidgetItem('1')
            item_no.setTextAlignment(Qt.AlignCenter)
            item_no.setFlags(item_no.flags() & ~Qt.ItemIsEditable)
            table.setItem(0, 0, item_no)
            # Product
            table.setItem(0, 1, QTableWidgetItem(''))
            # Quantity
            qty_edit = QLineEdit('')
            qty_edit.setObjectName('qtyInput')
            qty_edit.setAlignment(Qt.AlignCenter)
            qty_edit.textChanged.connect(lambda _t: self._recalc_row_total(table, 0))
            table.setCellWidget(0, 2, qty_edit)
            # Unit Price
            item_price = QTableWidgetItem('0.00')
            item_price.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_price.setFlags(item_price.flags() & ~Qt.ItemIsEditable)
            table.setItem(0, 3, item_price)
            # Total
            table.setItem(0, 4, QTableWidgetItem(''))
            # Remove
            empty_btn = QPushButton('X')
            empty_btn.setObjectName('removeBtn')
            try:
                empty_btn.setFixedSize(28, 28)
            except Exception:
                pass
            empty_btn.clicked.connect(lambda _: self._remove_table_row(table, 0))
            table.setCellWidget(0, 5, empty_btn)

    def _remove_table_row(self, table: QTableWidget, row: int):
        if 0 <= row < table.rowCount():
            table.removeRow(row)
            # Renumber the No. column after removal
            for r in range(table.rowCount()):
                num_item = table.item(r, 0)
                if num_item is None:
                    num_item = QTableWidgetItem()
                    num_item.setFlags(num_item.flags() & ~Qt.ItemIsEditable)
                    table.setItem(r, 0, num_item)
                num_item.setText(str(r + 1))

    def _recalc_row_total(self, table: QTableWidget, row: int):
        # Read qty from column 2 QLineEdit if present; fallback to item
        qty_widget = table.cellWidget(row, 2)
        if isinstance(qty_widget, QLineEdit):
            try:
                qty = float(qty_widget.text()) if qty_widget.text() not in ('', None) else 0.0
            except ValueError:
                qty = 0.0
        else:
            qty_item = table.item(row, 2)
            try:
                qty = float(qty_item.text()) if qty_item is not None else 0.0
            except ValueError:
                qty = 0.0
        # Read unit price from column 3 item (non-editable)
        price_item = table.item(row, 3)
        try:
            price = float(price_item.text()) if price_item is not None else 0.0
        except (ValueError, AttributeError):
            price = 0.0
        total = qty * price
        total_item = QTableWidgetItem(f"{total:.2f}")
        total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
        table.setItem(row, 4, total_item)


def main():
    app = QApplication(sys.argv)
    load_qss(app)
    window = MainLoader()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
