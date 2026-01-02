
"""POS sales table functions (see docs for details)."""
from typing import List, Dict, Any, Optional
from PyQt5.QtCore import Qt, QEvent, QObject, QTimer
from PyQt5.QtWidgets import (
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QStatusBar,
    QLabel,
)
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtGui import QColor, QBrush, QPalette, QIcon
from PyQt5.QtCore import QSize
from functools import partial
from config import ROW_COLOR_EVEN, ROW_COLOR_ODD, ROW_COLOR_DELETE_HIGHLIGHT, ICON_DELETE
from modules.db_operation import get_product_info, show_temp_status


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

            Columns (0..6):
                0 No. (row number)
                1 Product (text)
                2 Quantity (editable input)
                3 Unit (g/kg/ea - non-editable)
                4 Unit Price (non-editable)
                5 Total (calculated/non-editable)
                6 Del (Remove button X)
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

    # Ensure 7 columns and set headers
    table.setColumnCount(7)
    table.setHorizontalHeaderLabels(['No.', 'Product', 'Quantity', '', 'Unit Price', 'Total', 'Del'])

    # Resize behavior and widths
    header: QHeaderView = table.horizontalHeader()
    header.setStretchLastSection(False)
    # Set fixed-like widths
    header.setSectionResizeMode(0, QHeaderView.Fixed)            # No.
    header.setSectionResizeMode(1, QHeaderView.Stretch)          # Product
    header.setSectionResizeMode(2, QHeaderView.Fixed)            # Quantity
    header.setSectionResizeMode(3, QHeaderView.Fixed)            # Unit (empty header)
    header.setSectionResizeMode(4, QHeaderView.Fixed)            # Unit Price
    header.setSectionResizeMode(5, QHeaderView.Fixed)            # Total
    header.setSectionResizeMode(6, QHeaderView.Fixed)            # Del
    # Apply pixel widths
    header.resizeSection(0, 48)   # No.
    header.resizeSection(2, 100)  # Qty (narrower now that unit is separate)
    header.resizeSection(3, 40)   # Unit (3 letters max: 'g', 'kg', 'ea')
    header.resizeSection(4, 120)  # Unit Price
    header.resizeSection(5, 120)  # Total
    header.resizeSection(6, 48)   # Del (X)

    # Row header visibility, alternating colors, edit/selection behavior are configured in the .ui

    # Disable alternating row colors to use uniform background
    table.setAlternatingRowColors(False)
    
    # Disable item selection to prevent row highlighting on click
    table.setSelectionMode(QTableWidget.NoSelection)

    # Start with empty table - products will be added via barcode scanner
    set_table_rows(table, [])

def display_unit(unit, quantity):
    """Return display string for unit column based on canonical unit and quantity."""
    if unit is None:
        return ''
    u = unit.lower()
    if u == 'each':
        return 'ea'
    if u == 'kg':
        return 'g' if quantity < 1 else 'kg'
    return unit


def set_table_rows(table: QTableWidget, rows: List[Dict[str, Any]], status_bar: Optional[QStatusBar] = None) -> None:
    # Debug print removed
    """Rebuild table with per-row editable states based on product unit type.

    The editable state is determined when products are added:
    - KG items (requires weighing): editable=False, display shows weight (e.g., "600 g")
    - EACH items (count-based): editable=True, display shows numeric count

    Unit information comes from PRODUCT_CACHE which includes (name, price, unit).

    Args:
        table: QTableWidget to populate
        rows: List of row dicts with keys: product, quantity, unit_price, editable, display_text (optional)
        status_bar: Optional status bar for messages
    """
    from PyQt5.QtWidgets import QTableWidgetItem, QHBoxLayout, QPushButton, QLineEdit, QWidget
    from PyQt5.QtGui import QBrush, QIcon
    from PyQt5.QtCore import QSize, Qt
    from functools import partial
    from config import ICON_DELETE

    table.setRowCount(0)

    from modules.table.unit_helpers import get_display_unit
    for r, data in enumerate(rows):
        table.insertRow(r)

        row_color = get_row_color(r)
        product_name = str(data.get('product_name', data.get('product', '')))
        qty_val = data.get('quantity', 1)
        unit_price = data.get('unit_price', 0.0)
        editable = data.get('editable', True)

        # Col 0: Row number
        item_no = QTableWidgetItem(str(r + 1))
        item_no.setTextAlignment(Qt.AlignCenter)
        item_no.setFlags(item_no.flags() & ~Qt.ItemIsEditable)
        item_no.setBackground(QBrush(row_color))
        table.setItem(r, 0, item_no)

        # Col 1: Product name (display)
        item_product = QTableWidgetItem(product_name)
        item_product.setFlags(item_product.flags() & ~Qt.ItemIsEditable)
        item_product.setBackground(QBrush(row_color))
        table.setItem(r, 1, item_product)

        # Col 2: Quantity (editable or read-only based on row data)
        if not editable:
            # KG item - stored value is in kg
            if qty_val < 1.0:
                qty_display = str(int(float(qty_val) * 1000))  # Show grams
            else:
                qty_display = f"{float(qty_val):.2f}"  # Show kg
        else:
            # EACH item - display as integer
            if float(qty_val) == int(float(qty_val)):
                qty_display = str(int(float(qty_val)))
            else:
                qty_display = f"{float(qty_val):.2f}"
        qty_edit = QLineEdit(qty_display)
        qty_edit.setObjectName('qtyInput')
        qty_edit.setProperty('numeric_value', float(qty_val))
        qty_edit.setReadOnly(not editable)
        qty_edit.setAttribute(Qt.WA_StyledBackground, True)
        qty_edit.setAutoFillBackground(False)
        qty_edit.setAlignment(Qt.AlignCenter)

        if editable:
            from PyQt5.QtGui import QIntValidator
            validator = QIntValidator(1, 9999, qty_edit)
            qty_edit.setValidator(validator)
            qty_edit.textChanged.connect(lambda _t, e=qty_edit, t=table: _recalc_from_editor(e, t))
        _install_row_focus_behavior(qty_edit, table, r)

        qty_container = QWidget()
        qty_container.setStyleSheet(f"background-color: {row_color.name()};")
        qty_layout = QHBoxLayout(qty_container)
        qty_layout.setContentsMargins(2, 2, 2, 2)
        qty_layout.setSpacing(0)
        qty_layout.addWidget(qty_edit)
        table.setCellWidget(r, 2, qty_container)

        # Col 3: Unit (non-editable item) - use get_display_unit for display
        unit_canon = data.get('unit', '')
        display_unit = get_display_unit(unit_canon, float(qty_val))
        item_unit = QTableWidgetItem(display_unit)
        item_unit.setTextAlignment(Qt.AlignCenter)
        item_unit.setFlags(item_unit.flags() & ~Qt.ItemIsEditable)
        item_unit.setBackground(QBrush(row_color))
        table.setItem(r, 3, item_unit)
        
        # Col 4: Unit Price
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
        
        # Col 6: Remove button
        btn = QPushButton()
        btn.setObjectName('removeBtn')
        btn.setIcon(QIcon(ICON_DELETE))
        btn.setIconSize(QSize(36, 36))
        btn.setAttribute(Qt.WA_StyledBackground, True)
        btn.setAutoFillBackground(False)
        btn.pressed.connect(partial(_highlight_row_by_button, table, btn))
        btn.clicked.connect(partial(_remove_by_button, table, btn))
        
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        lay = QHBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(btn, 0, Qt.AlignCenter)
        table.setCellWidget(r, 6, container)
    
    try:
        _update_total_value(table)
    except Exception:
        pass


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
            for col in [1, 3, 4, 5]:  # Product, Unit, Unit Price, Total
                item = table.item(r, col)
                if item is not None:
                    item.setBackground(QBrush(row_color))
            
            # Update container background for columns 2 and 6 (widgets)
            for col in [2, 6]:  # Quantity, Remove button
                container = table.cellWidget(r, col)
                if container is not None:
                    # Column 2 (quantity) keeps row color, column 6 (delete button) stays transparent
                    if col == 2:
                        container.setStyleSheet(f"background-color: {row_color.name()};")
                    else:  # col == 6
                        container.setStyleSheet("background-color: transparent;")
        # Update the aggregated total if bound
        try:
            _update_total_value(table)
        except Exception:
            pass


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
            # Check if field is read-only (uses stored numeric value) or editable (parse text)
            if editor.isReadOnly():
                # For read-only KG fields, use stored numeric value (in kg)
                numeric_val = editor.property('numeric_value')
                if numeric_val is not None:
                    try:
                        qty = float(numeric_val)
                    except (ValueError, TypeError):
                        qty = 0.0
                else:
                    qty = 0.0
            else:
                # For editable EACH fields, parse integer text and update stored value
                try:
                    text = editor.text()
                    qty = float(text) if text not in ('', None, '') else 0.0
                    # Enforce max value
                    if qty > 9999:
                        qty = 9999
                        editor.setText('9999')
                    # Update stored numeric value for consistency
                    editor.setProperty('numeric_value', qty)
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
    # Read unit price from column 4 item (non-editable)
    price_item = table.item(row, 4)
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
    table.setItem(row, 5, total_item)
    # Update the aggregated total on every row total change
    try:
        _update_total_value(table)
    except Exception:
        pass


def _remove_by_button(table: QTableWidget, btn: QPushButton) -> None:
    """Slot to remove a row based on which delete button was clicked.
    Looks up the row containing the provided button and removes it.
    Robust against row reordering/renumbering.
    """
    # Find the row whose column 6 cell contains this button instance
    for r in range(table.rowCount()):
        cell = table.cellWidget(r, 6)
        if cell is None:
            continue
        child = cell.findChild(QPushButton, 'removeBtn')
        if child is btn:
            remove_table_row(table, r)
            return


def _highlight_row_for_deletion(table: QTableWidget, row: int) -> None:
    """Highlight the row (columns 0-5) when the remove button is pressed.
    Column 6 (the remove button itself) is excluded from highlighting.
    """
    if row < 0 or row >= table.rowCount():
        return
    
    # Get highlight color from config
    highlight_color = QColor(ROW_COLOR_DELETE_HIGHLIGHT)
    
    # Apply highlight to item-based cells (columns 0, 1, 3, 4, 5)
    for col in [0, 1, 3, 4, 5]:
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
    # Find the row whose column 6 cell contains this button instance
    for r in range(table.rowCount()):
        cell = table.cellWidget(r, 6)
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


# ----------------- Grand total helpers -----------------
def bind_total_label(table: QTableWidget, label: QLabel) -> None:
    """Bind a QLabel (ui/sales_frame.ui: QLabel#totalValue) to display grand total.

    Stores the label on the table object and computes the initial total.
    Subsequent row edits/add/remove will auto-update via internal calls.
    """
    try:
        # Attach dynamically; PyQt widgets allow Python attributes
        table._total_label = label  # type: ignore[attr-defined]
    except Exception:
        # Fallback via Qt dynamic property (not used by QSS here)
        try:
            table.setProperty('_total_label', label)
        except Exception:
            pass
    # Initialize current total cache
    try:
        table._current_total = 0.0  # type: ignore[attr-defined]
    except Exception:
        pass
    # Compute once now
    recompute_total(table)


def _format_currency(val: float) -> str:
    """Format currency for totalValue label. UI uses a single label with prefix.

    Example: '$ 0.00'
    """
    try:
        return f"$ {val:.2f}"
    except Exception:
        return "$ 0.00"


def recompute_total(table: QTableWidget) -> float:
    """Recompute the grand total from the 'Total' column (col 5) and update label if bound.

    Returns the computed total.
    """
    total = 0.0
    try:
        for r in range(table.rowCount()):
            item = table.item(r, 5)
            if item is None:
                continue
            try:
                total += float(item.text())
            except (ValueError, TypeError):
                continue
    except Exception:
        total = 0.0
    # Cache on table for external reads (e.g., payment frame)
    try:
        table._current_total = float(f"{total:.2f}")  # type: ignore[attr-defined]
    except Exception:
        pass
    # Update bound label if present
    try:
        label = getattr(table, '_total_label', None)
        if isinstance(label, QLabel):
            label.setText(_format_currency(total))
    except Exception:
        pass
    return total


def _update_total_value(table: QTableWidget) -> None:
    """Internal helper to refresh total on any row change."""
    try:
        recompute_total(table)
    except Exception:
        pass


def get_total(table: QTableWidget) -> float:
    """Return last computed grand total for the given sales table."""
    try:
        return float(getattr(table, '_current_total', 0.0))
    except Exception:
        return 0.0


def handle_barcode_scanned(table: QTableWidget, barcode: str, status_bar: Optional[QStatusBar] = None) -> None:
    """
    Process barcode scanned for sales table.
    
    Args:
        table: QTableWidget to update
        barcode: Scanned barcode/product code
        status_bar: Optional QStatusBar to show messages
        
    Logic:
        1. Look up product from barcode in cache
        2. Check if product already exists in table
           - If exists: increment quantity by 1
           - If new: add new row with quantity 1
        3. Recalculate totals
        4. Show status message (success/not found)
    """
    if not barcode:
        return
        
    if status_bar:
        show_temp_status(status_bar, f"Scanned: {barcode}", 3000)
    
    # Look up product in cache (includes unit type)
    from modules.table.unit_helpers import canonicalize_unit
    found, product_name, unit_price, unit = get_product_info(barcode)
    unit_canon = canonicalize_unit(unit)

    if not found:
        if status_bar:
            show_temp_status(status_bar, f"Product '{barcode}' not found in database", 5000)
        return

    is_kg_item = (unit_canon == 'Kg')

    existing_row = find_product_in_table(table, barcode, unit_canon)

    if existing_row is not None:
        qty_container = table.cellWidget(existing_row, 2)
        if qty_container:
            editor = qty_container.findChild(QLineEdit, 'qtyInput')
            if editor and not editor.isReadOnly():
                increment_row_quantity(table, existing_row)
                if status_bar:
                    show_temp_status(status_bar, f"Added {product_name} (quantity updated)", 3000)
            else:
                if status_bar:
                    show_temp_status(status_bar, f"KG item - use Vegetable Entry to weigh", 3000)
        return
    else:
        if is_kg_item:
            if status_bar:
                show_temp_status(status_bar, f"{product_name} is KG item - use Vegetable Entry to weigh", 5000)
        else:
            _add_product_row(table, barcode, product_name, unit_price, unit_canon, quantity=1, status_bar=status_bar, editable=True)
            if status_bar:
                show_temp_status(status_bar, f"Added {product_name}", 3000)


def find_product_in_table(table: QTableWidget, product_code: str, unit_canon: str = None) -> Optional[int]:
    """
    Search table for existing product by code.
    
    Used by barcode scanning and vegetable entry dialog for duplicate detection.
    Searches by product code, looks up name from cache, and compares with table rows.
    
    Args:
        table: QTableWidget to search
        product_code: Product code to find (e.g., barcode or 'Veg01')
        
    Returns:
        Row index if found, None otherwise
    """
    # Look up product name once before searching
    from modules.table.unit_helpers import canonicalize_unit
    found, product_name, _, unit = get_product_info(product_code)
    if not found:
        return None
    unit_canon = unit_canon or canonicalize_unit(unit)
    for row in range(table.rowCount()):
        item = table.item(row, 1)
        unit_item = table.item(row, 3)
        if item is None or unit_item is None:
            continue
        table_product_name = item.text()
        table_unit = canonicalize_unit(unit_item.text())
        if table_product_name == product_name and table_unit == unit_canon:
            return row
    return None


def increment_row_quantity(table: QTableWidget, row: int) -> None:
    """
    Increment quantity in specified row by 1.
    
    Automatically handles both EACH and KG items:
    - EACH items (editable): Increments integer count by 1
    - KG items (read-only): Adds weight (caller must use add_product_row for KG)
    
    Args:
        table: QTableWidget containing the row
        row: Row index to update
    """
    # Get current quantity from column 2 (QLineEdit in container)
    qty_container = table.cellWidget(row, 2)
    if qty_container is None:
        return
        
    editor = qty_container.findChild(QLineEdit, 'qtyInput')
    if editor is None:
        return
        
    try:
        current_qty = float(editor.text()) if editor.text() else 0.0
        new_qty = current_qty + 1
        editor.setText(str(int(new_qty)))
        # recalc_row_total will be triggered by textChanged signal
    except ValueError:
        # If text is invalid, reset to 1
        editor.setText('1')


def _add_product_row(table: QTableWidget, product_code: str, product_name: str, 
                     unit_price: float, unit: str, quantity: float = 1, status_bar: Optional[QStatusBar] = None, 
                     editable: bool = True, display_text: Optional[str] = None) -> None:
    """
    Add a new product row to the table.
    
    Args:
        table: QTableWidget to update
        product_code: Product barcode/code
        product_name: Product display name
        unit_price: Product unit price
        quantity: Quantity of product to add (default: 1)
        status_bar: Optional QStatusBar for error messages
        editable: Whether quantity cell should be editable (default: True)
        display_text: Optional custom display text for quantity (e.g., "500 g")
    """
    # Get current rows data
    current_rows = []
    for r in range(table.rowCount()):
        # Extract product code from row
        product_item = table.item(r, 1)
        if product_item is None:
            continue
            
        # Get quantity, display text, and editable state
        qty_container = table.cellWidget(r, 2)
        qty = 1
        row_editable = True
        if qty_container is not None:
            editor = qty_container.findChild(QLineEdit, 'qtyInput')
            if editor is not None:
                # Preserve editable state
                row_editable = not editor.isReadOnly()
                
                # Use numeric_value property if available (preserves read-only values)
                numeric_val = editor.property('numeric_value')
                if numeric_val is not None:
                    try:
                        qty = float(numeric_val)
                    except (ValueError, TypeError):
                        qty = 1
                else:
                    # Parse text for editable fields
                    try:
                        qty = float(editor.text()) if editor.text() else 1
                    except ValueError:
                        qty = 1
        
        # Get unit price from column 4
        price_item = table.item(r, 4)
        price = 0.0
        if price_item is not None:
            try:
                price = float(price_item.text())
            except ValueError:
                price = 0.0
        
        unit_item = table.item(r, 3)
        unit_val = unit_item.text() if unit_item is not None else ''
        row_data = {
            'product': product_item.text(),
            'quantity': qty,
            'unit_price': price,
            'editable': row_editable,
            'unit': unit_val
        }
        current_rows.append(row_data)
    
    # Add new product
    new_row = {
        'product': product_name,
        'quantity': quantity,
        'unit_price': unit_price,
        'editable': editable,
        'unit': unit
    }
    current_rows.append(new_row)
    
    # Rebuild table with mixed editable states
    set_table_rows(table, current_rows, status_bar)
