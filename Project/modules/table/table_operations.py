from typing import List, Dict, Any, Optional
from functools import partial

from PyQt5.QtCore import Qt, QEvent, QObject, QSize, QRegularExpression
from PyQt5.QtWidgets import (
    QWidget, QTableWidget, QTableWidgetItem, QHBoxLayout, 
    QPushButton, QLineEdit, QStatusBar, QLabel, QHeaderView
)
from PyQt5.QtGui import QColor, QBrush, QIcon, QRegularExpressionValidator

# Configuration and Database constants
from config import (
    ROW_COLOR_EVEN, ROW_COLOR_ODD, ROW_COLOR_DELETE_HIGHLIGHT, 
    ICON_DELETE, MAX_TABLE_ROWS
)
from modules.db_operation import get_product_info
from modules.ui_utils.ui_feedback import show_temp_status

# =========================================================
# SECTION 1: UI INITIALIZATION & THEME
# =========================================================

def get_row_color(row: int) -> QColor:
    """Returns alternating row background color."""
    return QColor(ROW_COLOR_EVEN if row % 2 == 0 else ROW_COLOR_ODD)

def setup_sales_table(table: QTableWidget) -> None:
    """Configures table headers, column widths, and basic interaction policies."""
    if table is None: return

    # Apply grey background to viewport
    try:
        table.viewport().setStyleSheet("background-color: #e4e4e4;")
    except:
        pass

    table.setColumnCount(7)
    table.setHorizontalHeaderLabels(['No.', 'Product', 'Quantity', '', 'Unit Price', 'Total', 'Del'])

    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    
    # Column Sizing
    modes = [QHeaderView.Fixed, QHeaderView.Stretch, QHeaderView.Fixed, 
             QHeaderView.Fixed, QHeaderView.Fixed, QHeaderView.Fixed, QHeaderView.Fixed]
    widths = {0: 48, 2: 100, 3: 40, 4: 120, 5: 120, 6: 48}

    for i, mode in enumerate(modes):
        header.setSectionResizeMode(i, mode)
    for col, width in widths.items():
        header.resizeSection(col, width)

    table.setAlternatingRowColors(False)
    table.setSelectionMode(QTableWidget.NoSelection)
    set_table_rows(table, [])

# =========================================================
# SECTION 2: TABLE RENDERING & DATA SYNC
# =========================================================

def set_table_rows(table: QTableWidget, rows: List[Dict[str, Any]], status_bar: Optional[QStatusBar] = None) -> None:
    """Populates the QTableWidget with data. Enforces MAX_TABLE_ROWS limit."""
    from modules.ui_utils.max_rows_dialog import open_max_rows_dialog
    from modules.table.unit_helpers import get_display_unit

    # Enforce Global Row Limit
    if len(rows) > MAX_TABLE_ROWS:
        dlg = open_max_rows_dialog(table.window(), f"Max {MAX_TABLE_ROWS} items. Hold current sale or PAY to continue")
        dlg.exec_()
        return

    table.setRowCount(0)

    for r, data in enumerate(rows):
        table.insertRow(r)
        row_color = get_row_color(r)
        product_name = str(data.get('product_name', data.get('product', '')))
        qty_val = data.get('quantity', 1)
        u_price = data.get('unit_price', 0.0)
        editable = data.get('editable', True)
        unit_canon = data.get('unit', '')

        # Basic Cell Items (Col 0, 1, 4)
        items = {
            0: (str(r + 1), Qt.AlignCenter),
            1: (product_name, Qt.AlignLeft | Qt.AlignVCenter),
            4: (f"{u_price:.2f}", Qt.AlignRight | Qt.AlignVCenter)
        }
        for col, (text, align) in items.items():
            item = QTableWidgetItem(text)
            item.setTextAlignment(align)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item_bg = row_color
            item.setBackground(QBrush(item_bg))
            table.setItem(r, col, item)

        # Col 2: Quantity Editor (Regex-locked for EACH, Read-only for KG)
        if not editable:
            qty_display = str(int(float(qty_val) * 1000)) if qty_val < 1.0 else f"{float(qty_val):.2f}"
        else:
            qty_display = str(int(float(qty_val))) if float(qty_val) == int(float(qty_val)) else f"{float(qty_val):.2f}"
        
        qty_edit = QLineEdit(qty_display)
        qty_edit.setObjectName('qtyInput')
        qty_edit.setProperty('numeric_value', float(qty_val))
        qty_edit.setReadOnly(not editable)
        qty_edit.setAlignment(Qt.AlignCenter)

        if editable:
            regex = QRegularExpression(r"^[1-9][0-9]{0,3}$")
            qty_edit.setValidator(QRegularExpressionValidator(regex, qty_edit))
            qty_edit.textChanged.connect(lambda _t, e=qty_edit, t=table: _recalc_from_editor(e, t))
        
        _install_row_focus_behavior(qty_edit, table, r)

        qty_container = QWidget()
        qty_container.setStyleSheet(f"background-color: {row_color.name()};")
        qty_lay = QHBoxLayout(qty_container)
        qty_lay.setContentsMargins(2, 2, 2, 2)
        qty_lay.addWidget(qty_edit)
        table.setCellWidget(r, 2, qty_container)

        # Col 3: Unit (Non-editable)
        item_unit = QTableWidgetItem(get_display_unit(unit_canon, float(qty_val)))
        item_unit.setTextAlignment(Qt.AlignCenter)
        item_unit.setFlags(item_unit.flags() & ~Qt.ItemIsEditable)
        item_unit.setBackground(QBrush(row_color))
        table.setItem(r, 3, item_unit)

        # Col 5: Total calculation
        row_total = float(qty_val) * float(u_price)
        item_total = QTableWidgetItem(f"{row_total:.2f}")
        item_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        item_total.setFlags(item_total.flags() & ~Qt.ItemIsEditable)
        item_total.setBackground(QBrush(row_color))
        table.setItem(r, 5, item_total)

        # Col 6: Delete Button
        btn = QPushButton('X')
        btn.setObjectName('removeBtn')
        btn.setStyleSheet(f"QPushButton {{ background-color: {row_color.name()}; font-size: 14pt; "
                          f"font-weight: bold; color: red; border: 3px solid red; }}")
        btn.pressed.connect(partial(_highlight_row_by_button, table, btn))
        btn.clicked.connect(partial(_remove_by_button, table, btn))

        btn_container = QWidget()
        btn_lay = QHBoxLayout(btn_container)
        btn_lay.setContentsMargins(0, 0, 0, 0)
        btn_lay.addWidget(btn, 0, Qt.AlignCenter)
        table.setCellWidget(r, 6, btn_container)

    _update_total_value(table)
    if table.rowCount() > 0: table.scrollToBottom()

def get_sales_data(table: QTableWidget) -> List[Dict[str, Any]]:
    """Extracts data from the QTableWidget back into a dictionary list."""
    from modules.ui_utils import input_handler
    from modules.table.unit_helpers import canonicalize_unit
    
    rows = []
    for r in range(table.rowCount()):
        name_item = table.item(r, 1)
        unit_item = table.item(r, 3)
        price_item = table.item(r, 4)
        qty_container = table.cellWidget(r, 2)
        if not (name_item and qty_container): continue
            
        editor = qty_container.findChild(QLineEdit, 'qtyInput')
        unit_canon = canonicalize_unit(unit_item.text()) if unit_item else ''
        
        try:
            qty = float(editor.property('numeric_value') or 0.0) if editor.isReadOnly() else \
                  input_handler.handle_quantity_input(editor, unit_type='unit')
        except:
            qty = 0.0

        rows.append({
            'product_name': name_item.text(),
            'quantity': qty,
            'unit_price': float(price_item.text() or 0.0),
            'unit': unit_canon,
            'editable': not editor.isReadOnly()
        })
    return rows

def is_transaction_active(table_widget) -> bool:
    """Step 0 Helper: Returns True if there are items in the sales table."""
    try:
        return table_widget is not None and table_widget.rowCount() > 0
    except Exception:
        return False
    
# =========================================================
# SECTION 3: MATH & TOTALS
# =========================================================

def recalc_row_total(table: QTableWidget, row: int) -> None:
    """Updates row and grand totals after an editor change."""
    from modules.ui_utils import input_handler
    
    qty_container = table.cellWidget(row, 2)
    price_item = table.item(row, 4)
    if not qty_container: return
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
    total_item = QTableWidgetItem(f"{qty * price:.2f}")
    total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
    total_item.setBackground(QBrush(get_row_color(row)))
    table.setItem(row, 5, total_item)
    _update_total_value(table)

def _recalc_from_editor(editor: QLineEdit, table: QTableWidget) -> None:
    """Finds row for a specific QLineEdit and triggers total update."""
    for r in range(table.rowCount()):
        container = table.cellWidget(r, 2)
        if container:
            child = container if isinstance(container, QLineEdit) else container.findChild(QLineEdit, 'qtyInput')
            if child is editor:
                recalc_row_total(table, r)
                return

def recompute_total(table: QTableWidget) -> float:
    """Calculates sum of all rows and updates the bound label."""
    total = 0.0
    for r in range(table.rowCount()):
        item = table.item(r, 5)
        if item:
            try: total += float(item.text())
            except: pass
    table._current_total = total
    label = getattr(table, '_total_label', None)
    if isinstance(label, QLabel):
        label.setText(f"$ {total:.2f}")
    return total

def _update_total_value(table: QTableWidget) -> None:
    recompute_total(table)

# =========================================================
# SECTION 4: INTERACTION & EVENT FILTERS
# =========================================================

def _on_qty_commit(editor: QLineEdit, table: QTableWidget) -> None:
    """Clears errors and updates math on commit. Focus handled by Coordinator."""
    from modules.ui_utils import input_handler, ui_feedback
    _recalc_from_editor(editor, table)
    status_lbl = getattr(table, '_status_label', None)
    try:
        input_handler.handle_quantity_input(editor, unit_type='unit')
        if status_lbl: ui_feedback.clear_status_label(status_lbl)
    except:
        pass

def _install_row_focus_behavior(editor: QLineEdit, table: QTableWidget, row: int) -> None:
    """Prevents row selection logic from interfering with editing."""
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
# SECTION 5: EXTERNAL BINDINGS
# =========================================================

def bind_status_label(table: QTableWidget, label: QLabel) -> None:
    table._status_label = label

def bind_next_focus_widget(table: QTableWidget, widget: QWidget) -> None:
    table._next_focus_widget = widget

def bind_total_label(table: QTableWidget, label: QLabel) -> None:
    table._total_label = label
    recompute_total(table)

def get_total(table: QTableWidget) -> float:
    return float(getattr(table, '_current_total', 0.0))

# =========================================================
# SECTION 6: ROW DELETION & HIGHLIGHTS
# =========================================================

def _remove_by_button(table: QTableWidget, btn: QPushButton) -> None:
    data = get_sales_data(table)
    idx = -1
    for r in range(table.rowCount()):
        cell = table.cellWidget(r, 6)
        if cell and cell.findChild(QPushButton, 'removeBtn') is btn:
            idx = r
            break
    if idx != -1:
        data.pop(idx)
        set_table_rows(table, data)

def _highlight_row_for_deletion(table: QTableWidget, row: int) -> None:
    if not (0 <= row < table.rowCount()): return
    highlight_color = QColor(ROW_COLOR_DELETE_HIGHLIGHT)
    for col in [0, 1, 3, 4, 5]:
        item = table.item(row, col)
        if item: item.setBackground(QBrush(highlight_color))
    qty_container = table.cellWidget(row, 2)
    if qty_container: qty_container.setStyleSheet(f"background-color: {highlight_color.name()};")

def _highlight_row_by_button(table: QTableWidget, btn: QPushButton) -> None:
    for r in range(table.rowCount()):
        cell = table.cellWidget(r, 6)
        if cell and cell.findChild(QPushButton, 'removeBtn') is btn:
            _highlight_row_for_deletion(table, r)
            break

# =========================================================
# SECTION 7: BARCODE SCANNER LOGIC
# =========================================================

def handle_barcode_scanned(table: QTableWidget, barcode: str, status_bar: Optional[QStatusBar] = None) -> None:
    """Processes scan. Enforces MAX_TABLE_ROWS for new items, but allows existing qty updates."""
    from modules.ui_utils.max_rows_dialog import open_max_rows_dialog
    from modules.table.unit_helpers import canonicalize_unit

    if not barcode: return
    if status_bar: show_temp_status(status_bar, f"Scanned: {barcode}", 3000)
    
    found, product_name, unit_price, unit = get_product_info(barcode)
    unit_canon = canonicalize_unit(unit)

    if not found:
        if status_bar: show_temp_status(status_bar, f"Product '{barcode}' not found", 5000)
        return

    existing_row = find_product_in_table(table, barcode, unit_canon)

    # Global Limit Check
    if existing_row is None and table.rowCount() >= MAX_TABLE_ROWS:
        dlg = open_max_rows_dialog(table.window(), f"Maximum of {MAX_TABLE_ROWS} items reached.")
        dlg.exec_()
        return

    if existing_row is not None:
        qty_container = table.cellWidget(existing_row, 2)
        if qty_container:
            editor = qty_container.findChild(QLineEdit, 'qtyInput')
            if editor and not editor.isReadOnly():
                increment_row_quantity(table, existing_row)
            elif status_bar:
                show_temp_status(status_bar, "KG item - use Vegetable Entry to weigh", 3000)
    else:
        if unit_canon == 'Kg':
            if status_bar: show_temp_status(status_bar, "KG item - use Vegetable Entry to weigh", 5000)
        else:
            _add_product_row(table, barcode, product_name, unit_price, unit_canon)

def find_product_in_table(table: QTableWidget, product_code: str, unit_canon: str = None) -> Optional[int]:
    """Helper for duplicate detection in barcode scanning."""
    from modules.table.unit_helpers import canonicalize_unit
    found, product_name, _, unit = get_product_info(product_code)
    if not found: return None
    u_canon = unit_canon or canonicalize_unit(unit)
    for row in range(table.rowCount()):
        item = table.item(row, 1)
        unit_item = table.item(row, 3)
        if item and unit_item:
            if item.text() == product_name and canonicalize_unit(unit_item.text()) == u_canon:
                return row
    return None

def increment_row_quantity(table: QTableWidget, row: int) -> None:
    data = get_sales_data(table)
    if 0 <= row < len(data):
        data[row]['quantity'] += 1
        set_table_rows(table, data)

def _add_product_row(table: QTableWidget, product_code: str, name: str, price: float, unit: str) -> None:
    data = get_sales_data(table)
    data.append({'product_name': name, 'quantity': 1, 'unit_price': price, 'unit': unit, 'editable': True})
    set_table_rows(table, data)

