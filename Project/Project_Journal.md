# Project Journal - POS System Development

**Project Name:** Point of Sale (POS) System  
**Started:** October 2025  
**Technology Stack:** Python, PyQt5, SQLite  
**Database:** Anumani.db (22,337 products)

---

## Table of Contents
1. [Application Architecture](#application-architecture)
2. [Main Window Structure](#main-window-structure)
3. [Sales Frame Implementation](#sales-frame-implementation)
4. [Sales Table Design](#sales-table-design)
5. [Database Integration](#database-integration)
6. [Design Decisions & Rationale](#design-decisions--rationale)

---

## Application Architecture

### Entry Point: `main.py`
- **Purpose:** Application loader and UI composer
- **Framework:** PyQt5 with .ui file loading via `uic`
- **Structure:** Composes multiple UI frames into a single main window
- **Styling:** Loads global QSS from `assets/style.qss`

### Directory Structure
```
Project/
├── main.py                 # Application entry point
├── config.py              # Configuration and constants
├── requirements.txt       # Python dependencies
├── Project_Journal.md     # This document
├── assets/
│   ├── style.qss         # Global stylesheet
│   └── icons/
│       └── delete.svg    # Delete button icon
├── ui/
│   ├── main_window.ui    # Main application window
│   ├── sales_frame.ui    # Sales section
│   ├── payment_frame.ui  # Payment section
│   └── vegetable.ui      # Digital weight input dialog
└── modules/
    ├── db_operation/
    │   ├── __init__.py
    │   └── database.py   # Database utilities & product cache
    └── sales/
        ├── __init__.py
        └── salesTable.py # Sales table logic
```

---

## Main Window Structure

### Hierarchy: `main_window.ui`

```
QMainWindow (MainLoader)
└── centralwidget
    └── mainWindowLayout (QVBoxLayout)
        ├── titleBar (QHBoxLayout)
        │   ├── Left Section (QHBoxLayout) - [stretch=1]
        │   │   ├── appNameLabel (QLabel) - "ANUMANI POS"
        │   │   └── stateLabel (QLabel) - Current state/mode
        │   └── burgerBtn (QPushButton) - Menu button
        │       └── Icon: Three horizontal lines (☰)
        │       └── Size: Fixed, controlled by QSS
        │
        ├── contentArea (QHBoxLayout)
        │   ├── salesFrame (QFrame) - Sales section placeholder
        │   └── paymentFrame (QFrame) - Payment section placeholder
```

### Title Bar Implementation

**Components:**
1. **App Name Label:** "ANUMANI POS" - identifies the application
2. **State Label:** Displays current mode/state (e.g., "Sale Mode", "Hold", etc.)
3. **Burger Button:** Menu/settings access point

**Design Decisions:**
- **Left section gets stretch factor 1:** Allows app name and state to expand, pushing burger button to the right
- **Burger button:** `QSizePolicy.Minimum` - takes only needed space, stays compact
- **Margins:** `(12, 6, 12, 6)` - Horizontal spacing from window edges

**Styling:**
- Controlled via `style.qss` for consistency
- Burger button size managed through QSS min/max constraints

---

## Sales Frame Implementation

### Hierarchy: `sales_frame.ui`

```
salesFrame (QFrame)
└── mainSalesLayout (QVBoxLayout) - spacing: 10px
    ├── salesLabel (QLabel) - "Sales" - [stretch=0]
    │   └── Fixed height, doesn't consume extra space
    │
    ├── salesTable (QTableWidget) - [stretch=7]
    │   └── Minimum height: 10em
    │   └── Expands to fill available vertical space
    │
    ├── totalContainer (QWidget) - [stretch=2]
    │   └── Height: ~3.6em
    │   └── Displays subtotal, tax, total
    │
    ├── addContainer (QWidget) - [stretch=2]
    │   └── addBtnLayout (QHBoxLayout)
    │       ├── vegBtn (QPushButton) - "Add Vegetables"
    │       │   └── Opens vegetable.ui dialog
    │       └── manualBtn (QPushButton) - "Add Manually"
    │           └── Manual product entry
    │   └── Height: 4.0em, buttons expand vertically
    │
    └── receiptContainer (QWidget) - [stretch=2]
        └── receiptLayout (QHBoxLayout)
            ├── cancelsaleBtn (QPushButton) - "Cancel Sale"
            ├── onholdBtn (QPushButton) - "On Hold"
            └── viewholdBtn (QPushButton) - "View Hold"
        └── Height: 4.0em, buttons expand vertically
```

### Layout Strategy

**Stretch Factors (Proportional Space Distribution):**
- `salesLabel`: 0 (fixed, no extra space)
- `salesTable`: 7 (gets 7/13 of extra space)
- `totalContainer`: 2 (gets 2/13 of extra space)
- `addContainer`: 2 (gets 2/13 of extra space)
- `receiptContainer`: 2 (gets 2/13 of extra space)

**Rationale:**
- Sales table is the primary workspace - gets most vertical space
- Totals, buttons are secondary - fixed proportions for consistency
- Uses `em` units for height (font-relative) - scales with system font settings

**Em-based Sizing:**
```python
def em_px(widget: QWidget, units: float) -> int:
    fm = QFontMetrics(widget.font())
    return int(round(units * fm.lineSpacing()))
```
- `totalContainer`: 3.6em
- `addContainer`: 4.0em
- `receiptContainer`: 4.0em
- `salesTable` minimum: 10em

**Why em instead of fixed pixels?**
- Responsive to user's font size settings
- Better accessibility
- Consistent visual proportions across different displays

---

## Sales Table Design

### Table Structure: `salesTable (QTableWidget)`

**Columns (6 total):**

| Col | Name       | Type          | Width      | Resize Mode | Editable | Purpose                    |
|-----|------------|---------------|------------|-------------|----------|----------------------------|
| 0   | No.        | QTableWidgetItem | 48px    | Fixed       | No       | Row number (1, 2, 3...)   |
| 1   | Product    | QTableWidgetItem | Stretch | Stretch     | No       | Product name              |
| 2   | Quantity   | QLineEdit     | 80px       | Fixed       | Yes      | Quantity input            |
| 3   | Unit Price | QTableWidgetItem | 100px   | Fixed       | No       | Price per unit            |
| 4   | Total      | QTableWidgetItem | 110px   | Fixed       | No       | Qty × Unit Price          |
| 5   | Del        | QPushButton   | 48px       | Fixed       | N/A      | Remove row button         |

### Table Configuration

**Settings:**
```python
table.setAlternatingRowColors(False)  # Manual color control
table.setSelectionMode(QTableWidget.NoSelection)  # No row selection
table.viewport().setStyleSheet("background-color: #e4e4e4;")  # Default bg
```

**Rationale for Manual Row Colors:**
- Qt's built-in alternating colors don't propagate to cell widgets (QLineEdit, QPushButton)
- Cell widgets are inside container QWidgets - need programmatic styling
- Solution: Manual color assignment to both items AND container widgets

**Color Scheme (from `config.py`):**
```python
ROW_COLOR_EVEN = '#add8e6'  # Light blue (rows 0, 2, 4, ...)
ROW_COLOR_ODD = '#ffffe0'   # Light yellow (rows 1, 3, 5, ...)
ROW_COLOR_DELETE_HIGHLIGHT = '#ff6b6b'  # Salmon red (deletion preview)
```

### Row Implementation Details

#### Column 0: Row Number
```python
item_no = QTableWidgetItem(str(r + 1))
item_no.setTextAlignment(Qt.AlignCenter)
item_no.setFlags(item_no.flags() & ~Qt.ItemIsEditable)  # Non-editable
item_no.setBackground(QBrush(row_color))  # Alternating color
```

#### Column 1: Product Name
```python
item_product = QTableWidgetItem(product_name)  # Fetched from cache
item_product.setFlags(item_product.flags() & ~Qt.ItemIsEditable)
item_product.setBackground(QBrush(row_color))
```
- **Source:** Product cache lookup via `get_product_info(product_code)`
- **Fallback:** Product code if not found in cache

#### Column 2: Quantity Input (Complex Widget Cell)

**Structure:**
```
QWidget (qty_container) - Colored background
└── QHBoxLayout (0 margins, 0 spacing)
    └── QLineEdit (qty_edit) - objectName='qtyInput'
        ├── Styled via QSS
        ├── Center-aligned text
        ├── WA_StyledBackground = True
        ├── AutoFillBackground = False
        └── Connected signals:
            ├── textChanged → _recalc_from_editor()
            └── editingFinished/returnPressed → _on_qty_commit()
```

**Why this complex structure?**
1. **Container Widget Needed:** To apply row background color (QLineEdit alone ignores cell background)
2. **QSS Styling:** `objectName='qtyInput'` allows targeted CSS rules
3. **Background Attributes:**
   - `WA_StyledBackground=True`: Enables QSS background rendering
   - `AutoFillBackground=False`: Prevents palette override of QSS

**Quantity Input Behavior:**

**Dynamic Row Lookup:**
```python
def _recalc_from_editor(editor: QLineEdit, table: QTableWidget) -> None:
    # Find which row contains this editor
    for r in range(table.rowCount()):
        qty_container = table.cellWidget(r, 2)
        child_editor = qty_container.findChild(QLineEdit, 'qtyInput')
        if child_editor is editor:
            recalc_row_total(table, r)  # Recalculate total
            return
```

**Why not use lambda with row index?**
- Rows can be deleted → indices shift
- Dynamic lookup ensures correct row after deletions
- More robust than storing static row numbers

**Focus Behavior:**
```python
class _RowSelectFilter(QObject):
    # On FocusIn: Clear table selection (no row highlighting)
    # On FocusOut: Do nothing (handled by editingFinished)
```

**Commit Behavior (Enter key or blur):**
```python
def _on_qty_commit(editor: QLineEdit, table: QTableWidget):
    table.clearSelection()  # Remove any selection
    table.setFocus()        # Move focus to table
    editor.clearFocus()     # Remove focus from input
```
- Prevents row staying "selected" after editing
- Returns visual state to neutral

#### Column 3: Unit Price
```python
item_price = QTableWidgetItem(f"{unit_price:.2f}")
item_price.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
item_price.setFlags(item_price.flags() & ~Qt.ItemIsEditable)
item_price.setBackground(QBrush(row_color))
```
- **Format:** Always 2 decimal places (e.g., "1.20")
- **Alignment:** Right-aligned (standard for numbers)
- **Source:** Product cache or provided data

#### Column 4: Total
```python
total = float(qty_val) * float(unit_price)
item_total = QTableWidgetItem(f"{total:.2f}")
item_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
item_total.setFlags(item_total.flags() & ~Qt.ItemIsEditable)
item_total.setBackground(QBrush(row_color))
```
- **Calculation:** Quantity × Unit Price
- **Recalculated:** Every time quantity changes (via `textChanged` signal)
- **Format:** 2 decimal places

#### Column 5: Delete Button (Complex Widget Cell)

**Structure:**
```
QWidget (container) - Transparent background
└── QHBoxLayout (0 margins, centered)
    └── QPushButton (btn) - objectName='removeBtn'
        ├── Icon: delete.svg (36×36)
        ├── WA_StyledBackground = True
        ├── AutoFillBackground = False
        └── Connected signals:
            ├── pressed → _highlight_row_by_button()
            └── clicked → _remove_by_button()
```

**Delete Flow:**
1. **Press:** Highlight entire row in salmon red (`ROW_COLOR_DELETE_HIGHLIGHT`)
2. **Click:** Remove row, renumber remaining rows, reapply alternating colors

**Why transparent container?**
- Allows row highlight to show through
- Button states (hover, pressed) controlled by QSS
- Clean visual separation from row colors

**Dynamic Row Removal:**
```python
def _remove_by_button(table: QTableWidget, btn: QPushButton):
    # Find which row contains this button instance
    for r in range(table.rowCount()):
        cell = table.cellWidget(r, 5)
        child = cell.findChild(QPushButton, 'removeBtn')
        if child is btn:
            remove_table_row(table, r)
            return
```

**Post-Deletion Cleanup:**
```python
def remove_table_row(table: QTableWidget, row: int):
    table.removeRow(row)
    table.clearSelection()
    
    # Renumber and recolor all remaining rows
    for r in range(table.rowCount()):
        row_color = get_row_color(r)  # Recalculate alternating color
        
        # Update row number
        num_item.setText(str(r + 1))
        num_item.setBackground(QBrush(row_color))
        
        # Update colors for all cells (items and containers)
        # ... (details in salesTable.py)
```

### Row Color Function

```python
def get_row_color(row: int) -> QColor:
    """Get alternating row color based on row index."""
    return QColor(ROW_COLOR_EVEN if row % 2 == 0 else ROW_COLOR_ODD)
```

**Usage:** Called whenever rows are created, renumbered, or deleted to maintain consistent alternating pattern.

---

## Database Integration

### Architecture: Preloaded Product Cache

**File:** `modules/db_operation/database.py`

**Database Details:**
- **Path:** `../db/Anumani.db` (one level above Project folder)
- **Type:** SQLite3
- **Table:** `Product_list`
- **Schema:**
  ```sql
  product_code TEXT PRIMARY KEY
  name TEXT NOT NULL
  category TEXT
  supplier TEXT
  selling_price REAL NOT NULL
  cost_price REAL
  unit TEXT
  last_updated TEXT
  ```
- **Record Count:** 22,337 products

### Cache Implementation

**Global Cache Structure:**
```python
PRODUCT_CACHE: Dict[str, Dict[str, any]] = {
    'product_code': {
        'name': 'Product Name',
        'price': 12.50
    },
    # ... 22,337 entries
}
```

**Loading Process:**
```python
def load_product_cache(db_path: str = DB_PATH) -> bool:
    global PRODUCT_CACHE
    PRODUCT_CACHE.clear()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT product_code, name, selling_price 
        FROM Product_list
    """)
    
    rows = cursor.fetchall()
    
    for row in rows:
        product_code, name, price = row
        PRODUCT_CACHE[str(product_code)] = {
            'name': str(name),
            'price': float(price)
        }
    
    conn.close()
    return True
```

**Loaded on:** Module import (automatic when application starts)

### Product Lookup

**Function:**
```python
def get_product_info(product_code: str) -> Tuple[bool, str, float]:
    """
    Returns: (found, name, price)
    - found: True if product exists
    - name: Product name or product_code if not found
    - price: Selling price or 0.0 if not found
    """
    if product_code in PRODUCT_CACHE:
        product = PRODUCT_CACHE[product_code]
        return True, product['name'], product['price']
    else:
        return False, product_code, 0.0
```

**Performance:** O(1) dictionary lookup - instant for all 22K+ products

### Integration with Sales Table

**In `set_sales_rows()`:**
```python
product_code = str(data.get('product', ''))
unit_price = data.get('unit_price', None)

if unit_price is None:
    # Fetch from cache
    found, name, price = get_product_info(product_code)
    if found:
        product_name = name
        unit_price = price
    else:
        # Product not found
        unit_price = 0.0
        if status_bar:
            show_temp_status(status_bar, 
                f"⚠ Product '{product_code}' not found in database", 
                10000)
```

**Data Flow:**
```
User Input (product_code) 
    → get_product_info(product_code)
    → PRODUCT_CACHE lookup
    → (found, name, price)
    → Display in table row
```

### Error Handling

**Status Bar Notifications:**
```python
def show_temp_status(status_bar: Optional[QStatusBar], 
                     message: str, 
                     duration_ms: int = 10000):
    status_bar.showMessage(message)
    QTimer.singleShot(duration_ms, status_bar.clearMessage)
```

**Behavior:**
- Invalid product codes show warning for 10 seconds
- Message clears automatically OR on next action (whichever comes first)
- Non-blocking - user can continue working

**Future Enhancement Placeholder:**
- Currently: Temporary status bar message
- Planned: More sophisticated error handling/UI feedback

### Cache Refresh

**Function:**
```python
def refresh_product_cache(db_path: str = DB_PATH) -> bool:
    return load_product_cache(db_path)
```

**When to call:**
- After adding new products
- After updating product prices
- After deleting products
- On manual refresh action (future feature)

---

## Design Decisions & Rationale

### 1. Preloaded Cache vs. Per-Query Database Access

**Decision:** Preload all 22K+ products into memory on startup

**Rationale:**

**Performance:**
- **Cache (chosen):** O(1) lookup, instant response
- **Per-query:** O(n) database query, I/O overhead per row
- **Impact:** Loading 5 rows: 5 cache lookups vs. 5 DB queries
- **Result:** Faster, smoother UX

**Memory:**
- 22,337 products × ~100 bytes ≈ 2.2 MB
- Negligible on modern systems
- Trade-off: Memory for speed is favorable

**Simplicity:**
- Single load on startup
- No connection pooling needed
- No query optimization needed
- Cleaner code

**Drawbacks:**
- Stale data if database changes externally
- Solution: Manual refresh or periodic reload

**Alternative Considered:** Per-row database queries
- Rejected: Too slow, blocks UI, complex connection management

### 2. Dict of Dict vs. Other Data Structures

**Decision:** `Dict[str, Dict[str, any]]` for product cache

**Alternatives Considered:**

**Dict of Set?**
```python
# ❌ Rejected
PRODUCT_CACHE = {
    '8888200708009': {'Product A', 12.50}
}
```
**Problems:**
- Sets are unordered - can't access by position
- No semantic clarity (which is name? which is price?)
- Not extensible (can't add more fields)
- No indexing support

**Dict of Tuple?**
```python
# ❌ Rejected
PRODUCT_CACHE = {
    '8888200708009': ('Product A', 12.50)
}
```
**Problems:**
- Tuple indexing: `[0]` and `[1]` - not self-documenting
- Adding fields requires changing all access code
- No named access

**Dict of Dict (chosen):**
```python
# ✅ Selected
PRODUCT_CACHE = {
    '8888200708009': {'name': 'Product A', 'price': 12.50}
}
```
**Advantages:**
- Named access: `product['name']`, `product['price']` - self-documenting
- Extensible: Easy to add `'category'`, `'stock'`, etc.
- Type-flexible: Can store any value type
- Readable code

**Access Pattern:**
```python
# Clear and explicit
if product_code in PRODUCT_CACHE:
    name = PRODUCT_CACHE[product_code]['name']
    price = PRODUCT_CACHE[product_code]['price']
```

### 3. Manual Row Colors vs. Qt's Built-in Alternating Colors

**Decision:** Manual color assignment for rows

**Qt's Built-in Approach:**
```python
table.setAlternatingRowColors(True)  # ❌ Doesn't work for us
```

**Problem:**
- QTableWidget's alternating colors only affect `QTableWidgetItem`
- Our columns 2 and 5 use **cell widgets** (QLineEdit, QPushButton)
- Cell widgets are inside container QWidgets
- Qt's alternating colors don't propagate to these containers

**Manual Approach (chosen):**
```python
table.setAlternatingRowColors(False)  # Disable built-in

# For each row:
row_color = get_row_color(r)  # Calculate color

# Apply to items
item.setBackground(QBrush(row_color))

# Apply to widget containers
container.setStyleSheet(f"background-color: {row_color.name()};")
```

**Why Necessary:**
- Cell widgets need color from their parent container
- QSS and palette backgrounds don't auto-sync
- Manual control ensures consistency

**Centralized Config:**
```python
# config.py - Single source of truth
ROW_COLOR_EVEN = '#add8e6'
ROW_COLOR_ODD = '#ffffe0'
```

### 4. Dynamic Row Lookup vs. Stored Indices

**Decision:** Dynamic lookup for row operations

**Problem:**
- Rows can be deleted
- Row indices shift after deletion
- Lambda closures capture current index, not dynamic value

**Bad Approach (index capture):**
```python
# ❌ Breaks after deletions
qty_edit.textChanged.connect(lambda: recalc_row_total(table, r))
# 'r' is captured at creation time, won't update if rows deleted
```

**Good Approach (dynamic lookup):**
```python
# ✅ Always finds correct row
qty_edit.textChanged.connect(
    lambda _t, e=qty_edit, t=table: _recalc_from_editor(e, t)
)

def _recalc_from_editor(editor: QLineEdit, table: QTableWidget):
    # Search for row containing this editor instance
    for r in range(table.rowCount()):
        if table.cellWidget(r, 2).findChild(QLineEdit) is editor:
            recalc_row_total(table, r)  # Use current row index
```

**Rationale:**
- Robust against row deletions
- Always operates on correct row
- Slight overhead acceptable (few rows, fast search)

### 5. Em-based Sizing vs. Fixed Pixels

**Decision:** Use font-relative `em` units for container heights

**Implementation:**
```python
def em_px(widget: QWidget, units: float) -> int:
    fm = QFontMetrics(widget.font())
    return int(round(units * fm.lineSpacing()))

# Apply em-based heights
totalContainer.setMinimumHeight(em_px(totalContainer, 3.6))
addContainer.setMinimumHeight(em_px(addContainer, 4.0))
```

**Benefits:**
- **Accessibility:** Scales with user's font size settings
- **Responsive:** Adapts to different DPI/scaling
- **Consistent:** Visual proportions maintained across displays
- **Professional:** Industry-standard approach (web, modern apps)

**Trade-off:**
- More complex than fixed pixels
- Calculated at runtime
- Worth it for better UX

### 6. Cell Widget Container Structure

**Decision:** Wrap editable widgets in container QWidgets

**Structure:**
```python
container = QWidget()  # Parent container
layout = QHBoxLayout(container)
layout.setContentsMargins(0, 0, 0, 0)
layout.addWidget(actual_widget)  # QLineEdit or QPushButton
table.setCellWidget(row, col, container)
```

**Why Not Direct setCellWidget?**
```python
# ❌ Doesn't work for backgrounds
table.setCellWidget(row, col, qty_edit)  # Can't color cell background
```

**Problem:**
- Cell widgets don't inherit table cell backgrounds
- Need parent container to provide colored background
- Container shows through widget's transparent areas

**Container Background:**
- **Quantity (col 2):** Colored with row color
- **Delete (col 5):** Transparent (shows row color through)

**Attributes Needed:**
```python
widget.setAttribute(Qt.WA_StyledBackground, True)  # Enable QSS backgrounds
widget.setAutoFillBackground(False)  # Don't override with palette
```

### 7. No Row Selection Mode

**Decision:** Disable table selection entirely

```python
table.setSelectionMode(QTableWidget.NoSelection)
```

**Rationale:**
- Prevents row highlighting on click
- Quantity inputs handle their own focus styling
- Cleaner visual: only active input shows focus
- Row selection not needed for our use case

**Focus Handling:**
- Quantity input shows focus via QSS `:focus` selector
- Delete button shows hover/pressed states
- No need for row-level selection feedback

### 8. Status Bar for Error Messaging

**Decision:** Use status bar for non-critical errors (invalid product codes)

**Current Implementation:**
```python
show_temp_status(status_bar, f"⚠ Product '{code}' not found", 10000)
```

**Why Status Bar?**
- Non-blocking
- User can continue working
- Auto-dismisses (10 seconds or next action)
- Unobtrusive

**Future Consideration:**
- More prominent UI for critical errors
- Dialog boxes for blocking issues
- Status bar for informational messages

---

## Recent Changes

### October 31, 2025

**Database Module Reorganization:**
- Created `modules/db_operation/` folder
- Moved `database.py` to `modules/db_operation/database.py`
- Created `__init__.py` with proper exports
- Updated import path in `salesTable.py`: `from modules.db_operation import ...`
- Fixed database path calculation for new folder depth

**Database Connection:**
- Corrected database path to `../db/Anumani.db`
- Updated schema query to use correct column names: `name` instead of `product_name`
- Successfully loaded 22,337 products into cache
- Removed sample data fallback (no longer needed)

**Product Cache Implementation:**
- Implemented preloaded product cache system
- Added `get_product_info()` for fast O(1) lookups
- Integrated cache lookup into `set_sales_rows()`
- Added status bar notifications for invalid product codes
- Sales table now displays real product names and prices from database

---

## Next Steps / Planned Features

1. **Status bar integration in main window**
   - Currently `set_sales_rows()` accepts optional status_bar parameter
   - Need to wire main window's status bar to sales table

2. **Product search/autocomplete**
   - Leverage product cache for instant search
   - Add product code input field

3. **Barcode scanner integration**
   - Read product codes from scanner
   - Auto-populate rows via cache lookup

4. **Cache refresh mechanism**
   - Manual refresh button
   - Auto-refresh on product CRUD operations

5. **Transaction totals**
   - Sum all row totals
   - Display in totalContainer

6. **Payment processing**
   - Integrate payment frame
   - Transaction completion flow

---

## Technical Notes

### QSS Styling Challenges
- Cell widgets inside tables need special handling
- `WA_StyledBackground` attribute required for QSS backgrounds
- Container widgets needed for proper background colors
- QSS `:focus` states work on input widgets but not table cells

### PyQt5 Quirks
- `uic.loadUi()` returns widget but doesn't parent it (must manually add to layout)
- Signal/slot connections with lambdas require careful closure handling
- Widget hierarchy important for finding children (`findChild()`)

### SQLite Performance
- 22K+ record query: ~100ms on SSD
- Dictionary population: ~50ms
- Total cache load: <200ms (acceptable startup time)

### Future Optimizations
- Consider lazy loading if product count grows significantly (100K+)
- Index optimization if adding complex queries
- Periodic cache refresh in background thread

---

**Document maintained by:** Development team  
**Last updated:** October 31, 2025  
**Update frequency:** End of each development session / before each commit
