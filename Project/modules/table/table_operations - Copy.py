from typing import List, Dict, Any, Optional
from PyQt5.QtCore import Qt, QEvent, QObject
from PyQt5.QtWidgets import (
    QWidget, QTableWidget, QTableWidgetItem, QHBoxLayout, 
    QPushButton, QLineEdit, QStatusBar, QLabel, QHeaderView
)
from PyQt5.QtGui import QColor, QBrush, QIcon
from PyQt5.QtCore import QSize
from functools import partial

from config import ROW_COLOR_EVEN, ROW_COLOR_ODD, ROW_COLOR_DELETE_HIGHLIGHT, ICON_DELETE
from modules.db_operation import get_product_info, show_temp_status

# =========================================================
# SECTION 1: UI SETUP & THEME
# =========================================================

def get_row_color(row: int) -> QColor:
    """Get the alternating row color for the given row index."""
    return QColor(ROW_COLOR_EVEN if row % 2 == 0 else ROW_COLOR_ODD)

def setup_sales_table(table: QTableWidget) -> None:
    """Configure headers and behavioral settings for the sales table."""
    if table is None: return

    try:
        table.viewport().setStyleSheet("background-color: #e4e4e4;")
    except Exception:
        pass

    table.setColumnCount(7)
    table.setHorizontalHeaderLabels(['No.', 'Product', 'Quantity', '', 'Unit Price', 'Total', 'Del'])

    header: QHeaderView = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setSectionResizeMode(0, QHeaderView.Fixed)
    header.setSectionResizeMode(1, QHeaderView.Stretch)
    header.setSectionResizeMode(2, QHeaderView.Fixed)
    header.setSectionResizeMode(3, QHeaderView.Fixed)
    header.setSectionResizeMode(4, QHeaderView.Fixed)
    header.setSectionResizeMode(5, QHeaderView.Fixed)
    header.setSectionResizeMode(6, QHeaderView.Fixed)
    
    header.resizeSection(0, 48)
    header.resizeSection(2, 100)
    header.resizeSection(3, 40)
    header.resizeSection(4, 120)
    header.resizeSection(5, 120)
    header.resizeSection(6, 48)

    table.setAlternatingRowColors(False)
    table.setSelectionMode(QTableWidget.NoSelection)
    set_table_rows(table, [])

# =========================================================
# SECTION 2: ROW RENDERING (UI)
# =========================================================

def set_table_rows(table: QTableWidget, rows: List[Dict[str, Any]], status_bar: Optional[QStatusBar] = None) -> None:
    """Rebuilds the table UI from a clean list of data dictionaries."""
    from modules.table.unit_helpers import get_display_unit

    table.setRowCount(0)

    for r, data in enumerate(rows):
        table.insertRow(r)
        row_color = get_row_color(r)
        product_name = str(data.get('product_name', data.get('product', '')))
        qty_val = data.get('quantity', 1)
        unit_price = data.get('unit_price', 0.0)
        editable = data.get('editable', True)
        unit_canon = data.get('unit', '')

        # Col 0: No.
        item_no = QTableWidgetItem(str(r + 1))
        item_no.setTextAlignment(Qt.AlignCenter)
        item_no.setFlags(item_no.flags() & ~Qt.ItemIsEditable)
        item_no.setBackground(QBrush(row_color))
        table.setItem(r, 0, item_no)

        # Col 1: Product
        item_product = QTableWidgetItem(product_name)
        item_product.setFlags(item_product.flags() & ~Qt.ItemIsEditable)
        item_product.setBackground(QBrush(row_color))
        table.setItem(r, 1, item_product)

        # Col 2: Quantity Editor
        qty_display = str(int(qty_val)) if editable else (f"{qty_val:.2f}" if qty_val >= 1 else str(int(qty_val * 1000)))
        qty_edit = QLineEdit(qty_display)
        qty_edit.setObjectName('qtyInput')
        qty_edit.setProperty('numeric_value', float(qty_val))
        qty_edit.setReadOnly(not editable)
        qty_edit.setAlignment(Qt.AlignCenter)

        if editable:
            from PyQt5.QtGui import QRegularExpressionValidator
            from PyQt5.QtCore import QRegularExpression
            # Blocks '0' as first digit and non-digits entirely
            regex = QRegularExpression(r"^[1-9][0-9]{0,3}$")
            qty_edit.setValidator(QRegularExpressionValidator(regex, qty_edit))    
            qty_edit.textChanged.connect(lambda _t, e=qty_edit, t=table: _recalc_from_editor(e, t))
        
        _install_row_focus_behavior(qty_edit, table, r)

        qty_container = QWidget()
        qty_container.setStyleSheet(f"background-color: {row_color.name()};")
        qty_layout = QHBoxLayout(qty_container)
        qty_layout.setContentsMargins(2, 2, 2, 2)
        qty_layout.addWidget(qty_edit)
        table.setCellWidget(r, 2, qty_container)

        # Col 3: Unit
        display_unit = get_display_unit(unit_canon, float(qty_val))
        item_unit = QTableWidgetItem(display_unit)
        item_unit.setTextAlignment(Qt.AlignCenter)
        item_unit.setFlags(item_unit.flags() & ~Qt.ItemIsEditable)
        item_unit.setBackground(QBrush(row_color))
        table.setItem(r, 3, item_unit)

        # Col 4: Price
        item_price = QTableWidgetItem(f"{unit_price:.2f}")
        item_price.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        item_price.setFlags(item_price.flags() & ~Qt.ItemIsEditable)
        item_price.setBackground(QBrush(row_color))
        table.setItem(r, 4, item_price)

        # Col 5: Total
        total = float(qty_val) * float(unit_price)
        item_total = QTableWidgetItem(f"{total:.2f}")
        item_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        item_total.setFlags(item_total.flags() & ~Qt.ItemIsEditable)
        item_total.setBackground(QBrush(row_color))
        table.setItem(r, 5, item_total)

        # Col 6: Remove
        btn = QPushButton()
        btn.setObjectName('removeBtn')
        btn.setIcon(QIcon(ICON_DELETE))
        btn.setIconSize(QSize(36, 36))
        btn.pressed.connect(partial(_highlight_row_by_button, table, btn))
        btn.clicked.connect(partial(_remove_by_button, table, btn))

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        lay = QHBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(btn, 0, Qt.AlignCenter)
        table.setCellWidget(r, 6, container)

    _update_total_value(table)

# =========================================================
# SECTION 3: DATA EXTRACTION & MATH
# =========================================================

def get_sales_data(table: QTableWidget) -> List[Dict[str, Any]]:
    """Converts Table UI to a list of dicts. Single source of truth for data."""
    from modules.ui_utils import input_handler
    from modules.table.unit_helpers import canonicalize_unit
    
    rows = []
    for r in range(table.rowCount()):
        name_item = table.item(r, 1)
        unit_item = table.item(r, 3)
        price_item = table.item(r, 4)
        qty_container = table.cellWidget(r, 2)
        if not name_item or not qty_container: continue
            
        editor = qty_container.findChild(QLineEdit, 'qtyInput')
        unit_canon = canonicalize_unit(unit_item.text()) if unit_item else ''
        
        try:
            if editor.isReadOnly():
                qty = float(editor.property('numeric_value') or 0.0)
            else:
                qty = input_handler.handle_quantity_input(editor, unit_type='unit')
        except (ValueError, TypeError):
            qty = 0.0

        rows.append({
            'product_name': name_item.text(),
            'quantity': qty,
            'unit_price': float(price_item.text() or 0.0),
            'unit': unit_canon,
            'editable': not editor.isReadOnly()
        })
    return rows

def recalc_row_total(table: QTableWidget, row: int) -> None:
    """Calculates row total using centralized input validation."""
    from modules.ui_utils import input_handler
    
    qty_container = table.cellWidget(row, 2)
    price_item = table.item(row, 4)
    if qty_container is None: return
    editor = qty_container.findChild(QLineEdit, 'qtyInput')
    
    qty = 0.0
    try:
        if editor.isReadOnly():
            qty = float(editor.property('numeric_value') or 0.0)
        else:
            qty = input_handler.handle_quantity_input(editor, unit_type='unit')
            editor.setProperty('numeric_value', qty)
    except ValueError:
        qty = 0.0

    price = float(price_item.text()) if price_item else 0.0
    total = qty * price
    
    total_item = QTableWidgetItem(f"{total:.2f}")
    total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
    total_item.setBackground(QBrush(get_row_color(row)))
    table.setItem(row, 5, total_item)
    _update_total_value(table)

def _recalc_from_editor(editor: QLineEdit, table: QTableWidget) -> None:
    for r in range(table.rowCount()):
        qty_container = table.cellWidget(r, 2)
        if qty_container:
            child = qty_container.findChild(QLineEdit, 'qtyInput')
            if child is editor:
                recalc_row_total(table, r)
                return

# =========================================================
# SECTION 4: INTERACTION & FOCUS
# =========================================================

def _on_qty_commit(editor: QLineEdit, table: QTableWidget) -> None:
    """Updates totals and clears stale errors. Focus is handled by FieldCoordinator."""
    from modules.ui_utils import input_handler, ui_feedback
    
    # 1. Update Math
    _recalc_from_editor(editor, table)

    # 2. Clear Label if fixed
    status_lbl = getattr(table, '_status_label', None)
    try:
        input_handler.handle_quantity_input(editor, unit_type='unit')
        if status_lbl:
            ui_feedback.clear_status_label(status_lbl)
    except ValueError:
        pass

def bind_status_label(table: QTableWidget, label: QLabel) -> None:
    table._status_label = label

def bind_next_focus_widget(table: QTableWidget, widget: QWidget) -> None:
    table._next_focus_widget = widget

def _install_row_focus_behavior(editor: QLineEdit, table: QTableWidget, row: int) -> None:
    """Installs event filter to prevent row selection while typing."""
    filt = _RowSelectFilter(table, row)
    editor.installEventFilter(filt)
    editor._rowSelectFilter = filt 
    editor.editingFinished.connect(lambda e=editor, t=table: _on_qty_commit(e, t))

class _RowSelectFilter(QObject):
    def __init__(self, table: QTableWidget, row: int):
        super().__init__()
        self._table = table
    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            try: self._table.clearSelection()
            except: pass
        return False

# =========================================================
# SECTION 5: HELPERS (DELETION & TOTALS)
# =========================================================

def _remove_by_button(table: QTableWidget, btn: QPushButton) -> None:
    data = get_sales_data(table)
    idx_to_remove = -1
    for r in range(table.rowCount()):
        cell = table.cellWidget(r, 6)
        if cell and cell.findChild(QPushButton, 'removeBtn') is btn:
            idx_to_remove = r
            break
    if idx_to_remove != -1:
        data.pop(idx_to_remove)
        set_table_rows(table, data)

def _highlight_row_by_button(table: QTableWidget, btn: QPushButton) -> None:
    for r in range(table.rowCount()):
        cell = table.cellWidget(r, 6)
        if cell and cell.findChild(QPushButton, 'removeBtn') is btn:
            highlight_color = QColor(ROW_COLOR_DELETE_HIGHLIGHT)
            for col in [0, 1, 3, 4, 5]:
                item = table.item(r, col)
                if item: item.setBackground(QBrush(highlight_color))
            qty_container = table.cellWidget(r, 2)
            if qty_container: qty_container.setStyleSheet(f"background-color: {highlight_color.name()};")
            return

def bind_total_label(table: QTableWidget, label: QLabel) -> None:
    table._total_label = label
    recompute_total(table)

def recompute_total(table: QTableWidget) -> float:
    total = 0.0
    for r in range(table.rowCount()):
        item = table.item(r, 5)
        if item:
            try: total += float(item.text())
            except: continue
    table._current_total = total
    label = getattr(table, '_total_label', None)
    if isinstance(label, QLabel):
        label.setText(f"$ {total:.2f}")
    return total

def _update_total_value(table: QTableWidget) -> None:
    recompute_total(table)

# =========================================================
# SECTION 6: BARCODE SCANNING & TOTAL RETRIEVAL
# =========================================================

def get_total(table: QTableWidget) -> float:
    """Return last computed grand total for the given sales table."""
    try:
        return float(getattr(table, '_current_total', 0.0))
    except Exception:
        return 0.0

def handle_barcode_scanned(table: QTableWidget, barcode: str, status_bar: Optional[QStatusBar] = None) -> None:
    """Process barcode scanned for the main sales table."""
    if not barcode: return
        
    if status_bar:
        show_temp_status(status_bar, f"Scanned: {barcode}", 3000)
    
    from modules.table.unit_helpers import canonicalize_unit
    found, product_name, unit_price, unit = get_product_info(barcode)
    unit_canon = canonicalize_unit(unit)

    if not found:
        if status_bar:
            show_temp_status(status_bar, f"Product '{barcode}' not found", 5000)
        return

    # Check for duplicates
    existing_row = find_product_in_table(table, barcode, unit_canon)

    if existing_row is not None:
        qty_container = table.cellWidget(existing_row, 2)
        if qty_container:
            editor = qty_container.findChild(QLineEdit, 'qtyInput')
            if editor and not editor.isReadOnly():
                increment_row_quantity(table, existing_row)
                if status_bar:
                    show_temp_status(status_bar, f"Updated {product_name}", 3000)
            else:
                if status_bar:
                    show_temp_status(status_bar, f"KG item: Use Vegetable Entry to weigh", 3000)
        return
    else:
        # Add as new row if not KG
        if unit_canon == 'Kg':
            if status_bar:
                show_temp_status(status_bar, f"{product_name} is a KG item: Use Vegetable Entry", 5000)
        else:
            _add_product_row(table, barcode, product_name, unit_price, unit_canon, quantity=1, status_bar=status_bar, editable=True)

def find_product_in_table(table: QTableWidget, product_code: str, unit_canon: str = None) -> Optional[int]:
    """Search table for existing product by comparing names and units."""
    from modules.table.unit_helpers import canonicalize_unit
    found, product_name, _, unit = get_product_info(product_code)
    if not found: return None
    
    unit_canon = unit_canon or canonicalize_unit(unit)
    for row in range(table.rowCount()):
        item = table.item(row, 1)
        unit_item = table.item(row, 3)
        if item and unit_item:
            if item.text() == product_name and canonicalize_unit(unit_item.text()) == unit_canon:
                return row
    return None

def increment_row_quantity(table: QTableWidget, row: int) -> None:
    """Increment quantity in specified row by 1."""
    data = get_sales_data(table)
    if 0 <= row < len(data):
        data[row]['quantity'] += 1
        set_table_rows(table, data)

def _add_product_row(table: QTableWidget, product_code: str, product_name: str, 
                     unit_price: float, unit: str, quantity: float = 1, status_bar: Optional[QStatusBar] = None, 
                     editable: bool = True) -> None:
    """Internal helper to add a new row using get_sales_data as source."""
    current_data = get_sales_data(table)
    current_data.append({
        'product_name': product_name,
        'quantity': quantity,
        'unit_price': unit_price,
        'unit': unit,
        'editable': editable
    })
    set_table_rows(table, current_data, status_bar)