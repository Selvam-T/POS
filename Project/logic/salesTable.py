"""
Sales table setup and helper functions
Provides:
- setup_sales_table(table): configure headers, widths, and insert a placeholder row
- set_sales_rows(table, rows): populate rows with qty input, unit price, totals, and a delete button
- remove_table_row(table, row): delete a row and renumber the first column
- recalc_row_total(table, row): recompute total from qty x unit price
"""
from typing import List, Dict, Any
from PyQt5.QtCore import Qt, QEvent, QObject, QTimer
from PyQt5.QtWidgets import (
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
)
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtGui import QColor, QBrush, QPalette, QIcon
from PyQt5.QtCore import QSize
from functools import partial
from config import ROW_COLOR_EVEN, ROW_COLOR_ODD, ROW_COLOR_DELETE_HIGHLIGHT, ICON_DELETE


def get_row_color(row: int) -> QColor:
    """Get the alternating row color for the given row index.
    
    Args:
        row: The row index (0-based)
    
    Returns:
        QColor object for the row background
    """
    return QColor(ROW_COLOR_EVEN if row % 2 == 0 else ROW_COLOR_ODD)


def setup_sales_table(table: QTableWidget) -> None:
    """Configure headers and add a sample placeholder row. Rows can be
    regenerated dynamically by calling set_sales_rows(table, rows).

            Columns (0..5):
                0 No. (row number)
                1 Product (text)
                2 Quantity (editable input)
                3 Unit Price (non-editable)
                4 Total (calculated/non-editable)
                5 Del (Remove button X)
    """
    if table is None:
        return

    # Default background for the whole table when rows are empty/untouched
    # Use viewport() so the item view's drawing surface gets the color
    try:
        table.viewport().setStyleSheet("background-color: #e4e4e4;")
    except Exception:
        # Fallback: set on the table if viewport styling isn't available
        try:
            table.setStyleSheet("background-color: #e4e4e4;")
        except Exception:
            pass

    # Ensure 6 columns and set headers
    table.setColumnCount(6)
    table.setHorizontalHeaderLabels(['No.', 'Product', 'Quantity', 'Unit Price', 'Total', 'Del'])

    # Resize behavior and widths
    header: QHeaderView = table.horizontalHeader()
    header.setStretchLastSection(False)
    # Set fixed-like widths
    header.setSectionResizeMode(0, QHeaderView.Fixed)            # No.
    header.setSectionResizeMode(1, QHeaderView.Stretch)          # Product
    header.setSectionResizeMode(2, QHeaderView.Fixed)            # Quantity
    header.setSectionResizeMode(3, QHeaderView.Fixed)            # Unit Price
    header.setSectionResizeMode(4, QHeaderView.Fixed)            # Total
    header.setSectionResizeMode(5, QHeaderView.Fixed)            # Del
    # Apply pixel widths
    header.resizeSection(0, 48)   # No.
    header.resizeSection(2, 80)   # Qty (input ~60px + padding)
    header.resizeSection(3, 100)  # Unit Price
    header.resizeSection(4, 110)  # Total
    header.resizeSection(5, 48)   # Del (X)

    # Row header visibility, alternating colors, edit/selection behavior are configured in the .ui

    # Disable alternating row colors to use uniform background
    table.setAlternatingRowColors(False)
    
    # Disable item selection to prevent row highlighting on click
    table.setSelectionMode(QTableWidget.NoSelection)

    # Add one placeholder row (values are placeholders; real code should call set_sales_rows)
    placeholder = [{
        'product': 'Apple',
        'quantity': 2,
        'unit_price': 1.50,
    },
    {
        'product': 'PineApple',
        'quantity': 9,
        'unit_price': 3.50,
    },
    {
        'product': 'Cherry',
        'quantity': 32,
        'unit_price': 8.20,
    },
    {
        'product': 'One',
        'quantity': 2,
        'unit_price': 1.50,
    },
    {
        'product': 'two',
        'quantity': 9,
        'unit_price': 3.50,
    },
    {
        'product': 'three',
        'quantity': 32,
        'unit_price': 8.20,
    },
    {
        'product': 'four',
        'quantity': 2,
        'unit_price': 1.50,
    },
    {
        'product': 'five',
        'quantity': 9,
        'unit_price': 3.50,
    },
    {
        'product': 'six',
        'quantity': 32,
        'unit_price': 8.20,
    },
    {
        'product': 'seven',
        'quantity': 2,
        'unit_price': 1.50,
    },
    {
        'product': 'eight',
        'quantity': 9,
        'unit_price': 3.50,
    },
    {
        'product': 'nine',
        'quantity': 32,
        'unit_price': 8.20,
    },
    {
        'product': 'ten',
        'quantity': 2,
        'unit_price': 1.50,
    },
    {
        'product': 'eleven',
        'quantity': 9,
        'unit_price': 3.50,
    },
    {
        'product': 'twelve',
        'quantity': 32,
        'unit_price': 8.20,
    },
    {
        'product': 'thirteen',
        'quantity': 2,
        'unit_price': 1.50,
    },
    {
        'product': 'fourteen',
        'quantity': 9,
        'unit_price': 3.50,
    },
    {
        'product': 'final',
        'quantity': 32,
        'unit_price': 8.20,
    }]

    set_sales_rows(table, placeholder)


def set_sales_rows(table: QTableWidget, rows: List[Dict[str, Any]]) -> None:
    """Replace table rows with provided data.
    rows: list of dicts with keys: product (str), quantity (int/float), unit_price (float)
    """
    table.setRowCount(0)
    for r, data in enumerate(rows):
        table.insertRow(r)

        # Get alternating row color
        row_color = get_row_color(r)

        # Col 0: Row number (non-editable)
        item_no = QTableWidgetItem(str(r + 1))
        item_no.setTextAlignment(Qt.AlignCenter)
        item_no.setFlags(item_no.flags() & ~Qt.ItemIsEditable)
        item_no.setBackground(QBrush(row_color))
        table.setItem(r, 0, item_no)

        # Col 1: Product name (non-editable item)
        item_product = QTableWidgetItem(str(data.get('product', '')))
        item_product.setFlags(item_product.flags() & ~Qt.ItemIsEditable)
        item_product.setBackground(QBrush(row_color))
        table.setItem(r, 1, item_product)

        # Col 2: Quantity (QLineEdit to match QSS qtyInput styling) inside a tintable container
        qty_val = data.get('quantity', 0)
        qty_edit = QLineEdit(str(qty_val))
        qty_edit.setObjectName('qtyInput')  # styled via QSS
        # Ensure style-sheet backgrounds are actually painted for this widget
        try:
            qty_edit.setAttribute(Qt.WA_StyledBackground, True)
        except Exception:
            pass
        try:
            qty_edit.setAutoFillBackground(False)  # Allow QSS to control background instead of palette
        except Exception:
            pass
        qty_edit.setAlignment(Qt.AlignCenter)
        # Recalculate total when quantity changes - use dynamic row lookup
        qty_edit.textChanged.connect(lambda _t, e=qty_edit, t=table: _recalc_from_editor(e, t))
        # Select the row when the qty input gains focus; clear selection when editing finishes
        _install_row_focus_behavior(qty_edit, table, r)
        qty_container = QWidget()
        qty_container.setStyleSheet(f"background-color: {row_color.name()};")  # Apply row color to container (is overriding widget background color in cells 2 and 5)
        qty_layout = QHBoxLayout(qty_container)
        qty_layout.setContentsMargins(0, 0, 0, 0)
        qty_layout.setSpacing(0)
        qty_layout.addWidget(qty_edit)
        table.setCellWidget(r, 2, qty_container)

        # Col 3: Unit Price (non-editable item)
        price_val = float(data.get('unit_price', 0.0))
        item_price = QTableWidgetItem(f"{price_val:.2f}")
        item_price.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        item_price.setFlags(item_price.flags() & ~Qt.ItemIsEditable)
        item_price.setBackground(QBrush(row_color))
        table.setItem(r, 3, item_price)

        # Col 4: Total (non-editable item)
        total = float(qty_val) * float(price_val)
        item_total = QTableWidgetItem(f"{total:.2f}")
        item_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        item_total.setFlags(item_total.flags() & ~Qt.ItemIsEditable)
        item_total.setBackground(QBrush(row_color))
        table.setItem(r, 4, item_total)

    # Backgrounds for rows will be applied after all rows are created

        # Col 5: Remove button (centered, circular X)
        btn = QPushButton()
        btn.setObjectName('removeBtn')  # styled via QSS
        btn.setIcon(QIcon(ICON_DELETE))
        btn.setIconSize(QSize(20, 20))
        try:
            btn.setAttribute(Qt.WA_StyledBackground, True)
        except Exception:
            pass
        try:
            btn.setAutoFillBackground(False)  # Allow QSS to control background instead of palette
        except Exception:
            pass
        # Size and look via QSS (QPushButton#removeBtn)
        # Highlight row when button is clicked (before removal)
        btn.pressed.connect(partial(_highlight_row_by_button, table, btn))
        btn.clicked.connect(partial(_remove_by_button, table, btn))
        # Center in cell via container layout
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")  # Transparent to show row color and allow button states
        lay = QHBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(btn, 0, Qt.AlignCenter)
        table.setCellWidget(r, 5, container)

    # After rows are created, ensure at least one empty row exists when no data provided (placeholder)
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
        try:
            qty_edit.setAttribute(Qt.WA_StyledBackground, True)
        except Exception:
            pass
        try:
            qty_edit.setAutoFillBackground(False)  # Allow QSS to control background instead of palette
        except Exception:
            pass
        qty_edit.setAlignment(Qt.AlignCenter)
        qty_edit.textChanged.connect(lambda _t, e=qty_edit, t=table: _recalc_from_editor(e, t))
        _install_row_focus_behavior(qty_edit, table, 0)
        qty_container = QWidget()
        qty_layout = QHBoxLayout(qty_container)
        qty_layout.setContentsMargins(0, 0, 0, 0)
        qty_layout.setSpacing(0)
        qty_layout.addWidget(qty_edit)
        table.setCellWidget(0, 2, qty_container)
        # Unit Price
        item_price = QTableWidgetItem('0.00')
        item_price.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        item_price.setFlags(item_price.flags() & ~Qt.ItemIsEditable)
        table.setItem(0, 3, item_price)
        # Total
        table.setItem(0, 4, QTableWidgetItem(''))
        # Remove (centered button)
        empty_btn = QPushButton()
        empty_btn.setObjectName('removeBtn')
        empty_btn.setIcon(QIcon(ICON_DELETE))
        empty_btn.setIconSize(QSize(20, 20))
        try:
            empty_btn.setAttribute(Qt.WA_StyledBackground, True)
        except Exception:
            pass
        try:
            empty_btn.setAutoFillBackground(False)  # Allow QSS to control background instead of palette
        except Exception:
            pass
        # Highlight row when button is pressed (before removal)
        empty_btn.pressed.connect(partial(_highlight_row_by_button, table, empty_btn))
        empty_btn.clicked.connect(partial(_remove_by_button, table, empty_btn))
        c = QWidget()
        c.setStyleSheet("background-color: transparent;")  # Transparent to show row color
        l = QHBoxLayout(c)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(0)
        l.addWidget(empty_btn, 0, Qt.AlignCenter)
        table.setCellWidget(0, 5, c)


def remove_table_row(table: QTableWidget, row: int) -> None:
    if 0 <= row < table.rowCount():
        table.removeRow(row)
        # Clear any selection so no row shows as highlighted
        try:
            table.clearSelection()
        except Exception:
            pass
        # Renumber the No. column and reapply alternating colors after removal
        for r in range(table.rowCount()):
            # Get alternating row color
            row_color = get_row_color(r)
            
            # Update row number
            num_item = table.item(r, 0)
            if num_item is None:
                num_item = QTableWidgetItem()
                num_item.setFlags(num_item.flags() & ~Qt.ItemIsEditable)
                table.setItem(r, 0, num_item)
            num_item.setText(str(r + 1))
            num_item.setBackground(QBrush(row_color))
            
            # Update colors for other item-based cells
            for col in [1, 3, 4]:  # Product, Unit Price, Total
                item = table.item(r, col)
                if item is not None:
                    item.setBackground(QBrush(row_color))
            
            # Update container background for columns 2 and 5 (widgets)
            for col in [2, 5]:  # Quantity, Remove button
                container = table.cellWidget(r, col)
                if container is not None:
                    # Column 2 (quantity) keeps row color, column 5 (delete button) stays transparent
                    if col == 2:
                        container.setStyleSheet(f"background-color: {row_color.name()};")
                    else:  # col == 5
                        container.setStyleSheet("background-color: transparent;")


def _recalc_from_editor(editor: QLineEdit, table: QTableWidget) -> None:
    """Find the row containing the editor and recalculate its total.
    This dynamically looks up the current row to handle post-deletion shifts.
    """
    # Find which row contains this editor widget
    for r in range(table.rowCount()):
        qty_container = table.cellWidget(r, 2)
        if qty_container is None:
            continue
        # Check if this container contains our editor
        child_editor = qty_container if isinstance(qty_container, QLineEdit) else qty_container.findChild(QLineEdit, 'qtyInput')
        if child_editor is editor:
            recalc_row_total(table, r)
            return


def recalc_row_total(table: QTableWidget, row: int) -> None:
    # Read qty from column 2 editor inside container if present; fallback to item
    qty_container = table.cellWidget(row, 2)
    qty = 0.0
    if qty_container is not None:
        editor = qty_container if isinstance(qty_container, QLineEdit) else qty_container.findChild(QLineEdit, 'qtyInput')
        if isinstance(editor, QLineEdit):
            try:
                text = editor.text()
                qty = float(text) if text not in ('', None, '') else 0.0
            except ValueError:
                qty = 0.0
        else:
            # Unlikely, but try reading from an item if present
            qty_item = table.item(row, 2)
            try:
                qty = float(qty_item.text()) if qty_item is not None else 0.0
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
    
    # Get alternating row color
    row_color = get_row_color(row)
    
    total_item = QTableWidgetItem(f"{total:.2f}")
    total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
    total_item.setBackground(QBrush(row_color))  # Apply alternating row color
    table.setItem(row, 4, total_item)


def _remove_by_button(table: QTableWidget, btn: QPushButton) -> None:
    """Slot to remove a row based on which delete button was clicked.
    Looks up the row containing the provided button and removes it.
    Robust against row reordering/renumbering.
    """
    # Find the row whose column 5 cell contains this button instance
    for r in range(table.rowCount()):
        cell = table.cellWidget(r, 5)
        if cell is None:
            continue
        child = cell.findChild(QPushButton, 'removeBtn')
        if child is btn:
            remove_table_row(table, r)
            return


def _highlight_row_for_deletion(table: QTableWidget, row: int) -> None:
    """Highlight the row (columns 0-4) when the remove button is pressed.
    Column 5 (the remove button itself) is excluded from highlighting.
    """
    if row < 0 or row >= table.rowCount():
        return
    
    # Get highlight color from config
    highlight_color = QColor(ROW_COLOR_DELETE_HIGHLIGHT)
    
    # Apply highlight to item-based cells (columns 0, 1, 3, 4)
    for col in [0, 1, 3, 4]:
        item = table.item(row, col)
        if item is not None:
            item.setBackground(QBrush(highlight_color))
    
    # Apply highlight to the container of column 2 (quantity input)
    qty_container = table.cellWidget(row, 2)
    if qty_container is not None:
        qty_container.setStyleSheet(f"background-color: {highlight_color.name()};")


def _highlight_row_by_button(table: QTableWidget, btn: QPushButton) -> None:
    """Find the row containing the button and highlight it.
    This dynamically looks up the row index to handle post-deletion shifts.
    """
    # Find the row whose column 5 cell contains this button instance
    for r in range(table.rowCount()):
        cell = table.cellWidget(r, 5)
        if cell is None:
            continue
        child = cell.findChild(QPushButton, 'removeBtn')
        if child is btn:
            _highlight_row_for_deletion(table, r)
            return


class _RowSelectFilter(QObject):
    """Event filter to keep rows unselected while editing qty.
    On focus-in: clear any table selection so row colors don't change.
    """
    def __init__(self, table: QTableWidget, row: int):
        super().__init__()
        self._table = table
        self._row = row

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            # Ensure no row is selected; only the editor will show focus styling
            try:
                self._table.clearSelection()
            except Exception:
                pass
        elif event.type() == QEvent.FocusOut:
            # Nothing special on focus out; editingFinished will clear if needed
            pass
        return False


def _install_row_focus_behavior(editor: QLineEdit, table: QTableWidget, row: int) -> None:
    """Keep rows unselected on focus and revert editor visuals on commit."""
    filt = _RowSelectFilter(table, row)
    editor.installEventFilter(filt)
    # Keep a reference to prevent GC of the filter
    editor._rowSelectFilter = filt  # type: ignore[attr-defined]
    # On commit (Enter), clear selection and move focus off the editor so :focus styles revert
    editor.editingFinished.connect(lambda e=editor, t=table: _on_qty_commit(e, t))
    try:
        editor.returnPressed.connect(lambda e=editor, t=table: _on_qty_commit(e, t))
    except Exception:
        # Some line edit variants may not have returnPressed; editingFinished is sufficient
        pass


def _on_qty_commit(editor: QLineEdit, table: QTableWidget) -> None:
    """Clear selection and defocus the qty editor so focus-based styles revert."""
    try:
        table.clearSelection()
    except Exception:
        pass
    try:
        table.setFocus(Qt.OtherFocusReason)
    except Exception:
        pass
    try:
        editor.clearFocus()
    except Exception:
        pass
