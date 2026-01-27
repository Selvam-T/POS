# Project Journal - POS System Development

**Project Name:** Point of Sale (POS) System  
**Started:** October 2025  
**Technology Stack:** Python, PyQt5, SQLite  
**Database:** Anumani.db (22,337 products)

---
 
## Update Summary (November 5, 2025)

Sales totals integration (grand total in Sales frame):

- Implemented grand total logic inside `modules/sales/salesTable.py`.
    - `bind_total_label(table, label)`: binds `QLabel#totalValue` to the sales table and initializes it.
    - `recompute_total(table) -> float`: recomputes from column 4 and updates the label.
    - `get_total(table) -> float`: returns the last computed total for other frames (e.g., Payment).
- Hooked total refresh on all table mutations:
    - After `set_sales_rows`, after each `recalc_row_total`, and after `remove_table_row`.
- Wired binding in `main.py` right after `setup_sales_table(...)` by locating `QLabel#totalValue` and calling `bind_total_label(...)`.
- Scan leak reversals: totals remain correct because aggregate is recomputed after each row total update; transient changes and their cleanup cancel out.
- Policy: recompute from column 4 (already-rounded row totals) to keep UI and aggregate consistent.

Docs: README gains a concise “Grand total (totalValue)” subsection; scanner doc notes how scan leaks affect totals.

Quality gates: PASS (syntax/import). Manual validation: scanning adds rows increments total; editing qty recalculates; deleting rows decrements; transient leak-and-clean returns total to expected value.

---
 

## Update Summary (January 9, 2026)

Error logging and fallback dialog improvements:

- Added shared error logger (`modules/ui_utils/error_logger.py`) for consistent, timestamped error logging to `log/error.log`.
- Updated Cancel Sale dialog controller to use fallback dialog if UI file is missing, with clear messaging and styled buttons.
- Fallback dialog logs error and shows statusbar notification using `show_main_status()`.
- Minimal button styling ensures visibility even if QSS is not applied.
- Documentation updated: see `Documentation/error_logging_and_fallback.md` and revised `cancel_all_functionality.md`.

Quality gates: PASS (manual test). Verified fallback dialog appears and logs error if UI is missing; statusbar message shown; error log includes timestamp.

 
## Update Summary (November 4, 2025)

Scanner input in-focus routing, protection, and diagnostics:

    - Default destination: Sales table handler.
    - Payment frame: accept only when `refundInput` is focused.
- Enter-as-Tab in Product dialog inputs; action buttons are explicitly non-default to avoid accidental activation.
- Centralized helpers: `_ignore_scan`, `_cleanup_scanner_leak`, `_show_dim_overlay`/`_hide_dim_overlay`, `_start_scanner_modal_block`/`_end_scanner_modal_block`, `_refocus_sales_table`, `_clear_barcode_override`.
- Diagnostics:
    - Always-on cache lookup logging per scan (found/missed, name, price, cache size).
    - Optional toggles: `DEBUG_SCANNER_FOCUS`, `DEBUG_FOCUS_CHANGES`, `DEBUG_CACHE_LOOKUP`.
- Known limitation (HID wedge): rare first-character leak into disallowed fields; mitigated via cleanup and global suppression windows. Hardware-level fixes (prefix/suffix or serial mode) are documented but deferred.

Docs: Added `Documentation/scanner_input_infocus.md` detailing routing rules, protections, known limitations, and developer guidance. Updated `README.md` to summarize behavior and link to the doc.

Quality gates: PASS (build/import); manual verification confirms no unintended sales increments in Manual/Vegetable dialogs, Product dialog accepts scans only at the code field, `qtyInput` stays clean, and Enter no longer triggers default buttons during scans.

---
 
## Update Summary (November 4, 2025, later)

Product dialog safety rule: ADD-only while a sale has items.

- Rationale: Prevent inconsistencies between items already listed in the current Sales table and any mid-transaction product changes (price edits or deletions) in the master database.
- Behavior:
    - If the Sales table has one or more rows, Product Management opens with only ADD enabled.
    - REMOVE and UPDATE/View are disabled and show tooltips explaining why.
    - If a caller tries to open the dialog with `initial_mode` of REMOVE/UPDATE during an active sale, it is forced to ADD.
- Implementation (main.py → `open_product_panel`):
    - Compute `sale_active = (self.sales_table and self.sales_table.rowCount() > 0)`.
    - `set_mode_buttons_enabled` respects `sale_active` and keeps REMOVE/UPDATE disabled.
    - Initial wiring disables REMOVE/UPDATE immediately and assigns explanatory tooltips.
    - Guard click handlers and coerce `initial_mode` to `add` when `sale_active`.
- Documentation:
    - Updated `Documentation/product_management.md` with a new “Sales-in-progress restrictions” subsection.
    - Updated `README.md` Usage with a concise “Sales-in-progress restrictions” section.
- Validation:
    - Quality gates: PASS (quick import/syntax check).
    - Manual tests: With rows present, Product dialog shows ADD enabled and REMOVE/UPDATE disabled; clearing the Sales table re-enables them.

---
 
## Update Summary (November 4, 2025, formatter)

Repository formatting utility for UI and styles:

- Added `tools/format_assets.py` to pretty-print `.ui` (via lxml) and `.qss` (via jsbeautifier).
- Updated `requirements.txt` to include `lxml` and `jsbeautifier`.
- Ran the formatter: output summary `UI: 7/7 formatted | QSS: 1/1 formatted`.

Developer usage:
```cmd
pip install -r requirements.txt
python tools\format_assets.py
```

Notes:
- XML attribute ordering in `.ui` files may change when reserialized (no semantic change).
- QSS formatting treats QSS as CSS; quick review recommended for Qt-only selectors/pseudo-states.

Quality gates: PASS (formatting only). No functional changes.

---
## Update Summary (November 3, 2025)

Header refactor and alignment fixes:

- Replaced the right-header sublayout (`dayTimeArea` with `labelDay` and `labelTime`) with a single `QLabel` named `labelDayTime`.
- `infoSection` now contains exactly three widgets: `labelDate` (left), `labelCompany` (center), `labelDayTime` (right).
- Programmatic stretch remains `1,0,1` so the center stays truly centered on resize.
- Removed QSS `qproperty-alignment` overrides for header labels to avoid Designer/runtime mismatches.
- Added explicit padding in QSS for visible edge offsets:
    - `QLabel#labelDate { padding-left: 30px; }`
    - `QLabel#labelDayTime { padding-right: 30px; }`
- Updated references in code and styles; removed all usages of `labelDay`, `labelTime`, and `dayTimeArea`.

See README “Header layout (infoSection)” for the concise how-to.

---

## Update Summary (November 3, 2025, later)

Product Management and scanner flow integration:

- Added a full Product Management dialog (`ui/product_menu.ui`) and wired it to the Product menu. Removed placeholder actions.
- Mode-driven behavior with buttons for ADD, UPDATE, REMOVE:
    - Starts with the form hidden until a mode is chosen; focuses Product Code on mode select.
    - ADD: requires all fields; includes Unit dropdown (pcs, kg); shows live duplicate check on Product Code and disables ADD if duplicate.
    - UPDATE/REMOVE: Product Code enabled; other fields disabled until a successful lookup; populates fields after lookup.
    - Status label at the bottom shows success/errors; on success, dialog auto-closes after a short delay.
- Implemented full CRUD to SQLite and a slim in-memory cache:
    - Cache keys normalized (uppercase + trimmed) for consistent lookups; immediate cache updates on ADD/UPDATE/DELETE.
    - Centralized `DB_PATH` in `config.py` to point to `../db/Anumani.db` and used across modules.
- Scanner routing improvements:
    - While Product dialog is open, all scans fill the Product Code field in the dialog (no Manual Entry auto-open).
    - In Sales frame, if a scanned code isn’t found: opens Product Management in ADD mode with the code prefilled.
    - After a successful ADD from that flow, the new item is automatically inserted into the sales table as if it were scanned again.
- Cleanup: Removed noisy debug prints across scanner, sales table, and main window. Retired empty helpers.

Docs: Created `Documentation/product_management.md`; updated `README.md` to reflect new flows and link to the doc.

Quality gates: No code errors reported post-change; behavior validated via manual flows (scan-found, scan-not-found → add → auto-insert).

---

## Update Summary (November 1, 2025)
## Update Summary (November 7, 2025)

Admin Settings dialog added and wired:

- Created `ui/admin_menu.ui` providing a frameless settings dialog with three tabs: ADMIN, STAFF, EMAIL.
    - Admin/Staff tabs each show current + new password fields with eye toggle buttons.
    - Email tab shows current (read-only) recovery email and a field for a new email.
    - Footer info label clarifies permission: only Admin can modify settings.
- Implemented controller `modules/menu/admin_menu.py`:
    - Function `open_admin_dialog(host_window, current_user='Admin', is_admin=True)` loads the UI, applies frameless flags, centers the dialog, wires close buttons, password reveal toggles, and stub save actions.
    - Supports a read-only mode (`is_admin=False`) disabling modification controls.
    - Reuses dim overlay and drag-to-move pattern established for logout dialog.
- Updated `main.py` wiring so `adminBtn` now opens the Admin Settings dialog instead of a placeholder message.
- Added documentation file: `Documentation/admin_settings.md` covering UI structure, object names, behavior, QSS hooks, and future work (secure persistence, validation feedback, integration with BaseMenuDialog).
- README updated: new feature bullet, project structure entries for `admin_menu.ui` and `admin_menu.py`, and link to the new documentation.

Rationale:
- Centralizes credential management in a dedicated dialog instead of temporary placeholder content.
- Establishes a pattern for future role-based settings and consistency across menu dialogs.

Next steps (not yet implemented):
- Migrate Admin dialog to use `BaseMenuDialog` for consistent title bar layout (currently custom title replicated).
- Add QSS styling (primary Save button, tab highlight, password field states).
- Implement secure password hashing and storage in AppData; add email validation and persistence.
- Introduce a user role state (Admin vs Staff) in the main window to control button enablement before opening the dialog.

Quality gates: PASS (no syntax errors after integration; application runs with new wiring). Manual launch shows dialog centered and functional.

---

### Placeholder Reports / Devices / Greeting dialogs (November 7, 2025, later)

- Added standalone .ui files earlier (now updated) with an `underConstructionLabel` centered beneath the header.
- Created `modules/menu/placeholder_menus.py` providing:
    - `open_reports_dialog(host_window)`
    - `open_devices_dialog(host_window)`
    - `open_greeting_dialog(host_window)`
    Each loads its corresponding `.ui` as a frameless modal, applies dim overlay, centers, and wires Close buttons + drag move on the custom title bar.
- Updated `main.py` menu button wiring:
    - `reportsBtn` → `open_reports_dialog`
    - `deviceBtn` → `open_devices_dialog`
    - `greetingBtn` → `open_greeting_dialog`
    Removed prior generic hardwired fallback dialog for these buttons (no more temporary message-based dialogs). Unknown buttons (none expected) are now disabled instead of spawning a generic dialog.
- Ensures consistent migration path: every right-side menu button now opens a .ui-based dialog (Admin, Reports, Vegetable, Product, Greeting, Device, Logout).

Rationale:
- Eliminates placeholder generic text dialogs so styling/theming can be unified via QSS.
- Makes future feature implementation a matter of enhancing each .ui/controller rather than replacing ad‑hoc code.

Quality gates: PASS (syntax check of new `placeholder_menus.py` and modified `main.py`).


This session introduced a compact right-side icon-only menu and finalized the main window structure:

- Replaced the legacy title bar with an `infoSection` header (company/date/day/time).
- Added `ui/menu_frame.ui` loaded into `menuFrame` with seven icon-only buttons (Admin, Reports, Vegetable, Product, Greeting, Device, Logout). Buttons show labels via tooltips and open modal placeholders.
- Constrained the menu width (min 80, max 100) and increased spacing between header and content.
- Updated `manual_entry.ui` to expose `QTextEdit#manualText` for message injection; unknown barcodes open this dialog.
- Strict product validation now uses `PRODUCT_CACHE` only (all test remapping removed).
- Scanner logs changed to ASCII-only to avoid Windows console Unicode errors. `test_scanner.py` updated accordingly.

For a concise overview and updated project structure, see `README.md`.

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
- **Styling:** Loads global QSS from `assets/main.qss`

### Directory Structure
```
Project/
├── config.py              # Configuration and constants
├── requirements.txt       # Python dependencies
├── Project_Journal.md     # This document
├── assets/
│   ├── main.qss          # Global stylesheet
│   └── icons/
│       └── delete.svg    # Delete button icon
├── ui/
│   ├── main_window.ui    # Main application window
│   ├── payment_frame.ui  # Payment section
│   └── vegetable_entry.ui      # Digital weight input dialog
└── modules/
    ├── db_operation/
        └── salesTable.py # Sales table logic
```

---

## Main Window Structure

### Hierarchy: `main_window.ui`
├── test_scanner.py         # Minimal scanner verification app

```
QMainWindow (MainLoader)
└── centralwidget
    └── mainWindowLayout (QVBoxLayout)
        ├── titleBar (QHBoxLayout)
        │   ├── Left Section (QHBoxLayout) - [stretch=1]
        │   │   ├── appNameLabel (QLabel) - "ANUMANI POS"
        │   │   └── stateLabel (QLabel) - Current state/mode
    │   
        │       └── Icon: Three horizontal lines (☰)
        │       └── Size: Fixed, controlled by QSS
        │
        ├── contentArea (QHBoxLayout)
        │   ├── salesFrame (QFrame) - Sales section placeholder
        │   └── paymentFrame (QFrame) - Payment section placeholder
```

### Header (infoSection) – Current Implementation

`infoSection` is a `QHBoxLayout` with three labels:

1. `labelDate` — AlignLeft | AlignVCenter
2. `labelCompany` — AlignHCenter | AlignVCenter
3. `labelDayTime` — AlignRight | AlignVCenter (combined day and time text)

Behavior:
- Stretch factors are set in `main.py` to `(1, 0, 1)` so the center label remains centered as the window resizes.
- Alignment is applied in code and not overridden by QSS (we removed previous `qproperty-alignment` centers for these labels).
- Edge spacing uses QSS padding rather than label margins to ensure consistent rendering across styles.

Historical note:
- Earlier versions used a nested layout with `labelDay` and `labelTime`. This was simplified to a single `labelDayTime` to avoid alignment confusion and easier styling.

### Title Bar Implementation (Historic)
**Components:**
1. **App Name Label:** "ANUMANI POS" - identifies the application
2. **State Label:** Displays current mode/state (e.g., "Sale Mode", "Hold", etc.)
3. **Burger Button:** Menu/settings access point

**Design Decisions:**
- **Left section gets stretch factor 1:** Allows app name and state to expand, pushing burger button to the right
- **Burger button:** `QSizePolicy.Minimum` - takes only needed space, stays compact
- **Margins:** `(12, 6, 12, 6)` - Horizontal spacing from window edges

**Styling:**
- Controlled via `main.qss` for consistency
- Burger button size managed through QSS min/max constraints

---

## Sales Frame Implementation

### Hierarchy: `sales_frame.ui`

```
salesFrame (QFrame)
└── mainSalesLayout (QVBoxLayout) - spacing: 10px
    ├── salesTable (QTableWidget) - [stretch=7]
    │   └── Minimum height: 10em
    │   └── Expands to fill available vertical space
    │
    ├── totalContainer (QWidget) - [stretch=2]
    │   └── Displays subtotal, tax, total
    │       ├── vegBtn (QPushButton) - "Vegetable Entry"
    │       │   └── Opens vegetable_entry.ui dialog
    │       └── manualBtn (QPushButton) - "Manual Entry"
    │           └── Manual product entry
    └── receiptContainer (QWidget) - [stretch=2]
        └── receiptLayout (QHBoxLayout)
            ├── cancelsaleBtn (QPushButton) - "Cancel Sale"
            ├── holdSalesBtn (QPushButton) - "On Hold"
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
- Responsive to user's font size settings
- Better accessibility

---


**Columns (6 total):**

| Col | Name       | Type          | Width      | Resize Mode | Editable | Purpose                    |
| 5   | Del        | QPushButton   | 48px       | Fixed       | N/A      | Remove row button         |

**Settings:**
```python
table.viewport().setStyleSheet("background-color: #e4e4e4;")  # Default bg
```
**Rationale for Manual Row Colors:**
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

**Module:** `modules/db_operation/` (see `product_cache.py`, `products_repo.py`, `db.py`)

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
PRODUCT_CACHE: Dict[str, Tuple[str, float, str]] = {
    'PRODUCT_CODE': ('Display Name', 12.50, 'Each'),
    # ... N entries
}
```

**Normalization:** Product codes are always normalized to UPPER CASE, and product names/other strings to CamelCase, both when loaded into PRODUCT_CACHE and when user input is compared. Legacy DB data is normalized at cache load and input time.

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

### October 31, 2025 - Barcode Scanner Integration

**Hardware Integration Architecture:**
- Created `modules/devices/` folder for all hardware interfaces
  - `scanner.py` - Barcode scanner (implemented)
  - `receipt_printer.py` - Receipt printer (future)
  - `weighing_scale.py` - Digital scale (future)
  - `secondary_display.py` - Customer display (future)

**Barcode Scanner Implementation:**
- Built event-driven barcode scanner module using `pynput` library
- Implemented Qt signal-slot pattern for thread-safe communication
- Scanner runs in background thread, emits signals to main UI thread

**Key Design Decisions:**

1. **Signal-Based Architecture:**
   ```python
   class BarcodeScanner(QObject):
       barcode_scanned = pyqtSignal(str)  # Emits when barcode detected
   ```
   - **Why signals?** Thread-safe communication between pynput listener (background) and Qt UI (main thread)
   - **Decoupled:** Scanner doesn't know about tables/UI, just emits events
   - **Multiple subscribers:** Multiple widgets can listen to same signal

2. **Barcode vs. Manual Input Detection:**
   - **Timing threshold:** 50ms between characters
   - **Scanner input:** <50ms intervals (fast, mechanical)
   - **Manual typing:** >100ms intervals (slow, human)
   - **Logic:** If time_diff > timeout → reset buffer (manual), else append (scanner)

3. **Barcode Focus vs. Keyboard Focus:**
   - **Keyboard Focus:** Qt built-in, visual (one widget at a time)
   - **Barcode Focus:** Custom logical state (which section receives barcodes)
   - **Independent:** User can type in QLineEdit while barcode goes to sales table
   - **Future:** Will use `BarcodeContext` enum to route to different sections:
     ```python
     class BarcodeContext(Enum):
         SALES_TABLE = 1    # Current implementation
         MANUAL_ENTRY = 2   # Future
         REFUND = 3         # Future
         MENU = 4           # Future (price check, inventory lookup, etc.)
     ```

4. **Event Flow:**
   ```
   Barcode Scanner (hardware)
       ↓ (rapid keystrokes)
   pynput listener (background thread)
       ↓ (detects Enter key)
   scanner.barcode_scanned.emit(code)
       ↓ (Qt signal, thread-safe)
   MainWindow.on_barcode_scanned(code)
       ↓ (route based on context)
   handle_barcode_scanned(table, code, status_bar)
       ↓
   Sales table updated (product added or quantity incremented)
   ```

**Sales Table Barcode Integration:**

1. **Product Lookup:**
   - Uses existing product cache (`get_product_info()`)
   - O(1) instant lookup from 22K+ products

2. **Duplicate Detection:**
   - Searches existing table rows by product name
   - If found: increment quantity by 1
   - If new: add new row with quantity 1

3. **User Feedback:**
   - Status bar shows: `📷 Scanned: [barcode]`
   - Success: `✓ Added [product name]`
   - Not found: `⚠ Product '[barcode]' not found in database`

**Implementation Details:**

**Scanner Module (`modules/devices/scanner.py`):**
```python
class BarcodeScanner(QObject):
    def __init__(self, timeout=0.05):
        self._buffer = ''
        self._last_time = 0
        self._timeout = timeout  # 50ms threshold
        self._listener = None
        self._enabled = True
        self._min_barcode_length = 3  # Minimum valid barcode
    
    def _on_key_press(self, key):
        # Timing logic to distinguish scanner from manual
        time_diff = now - self._last_time
        if time_diff > self._timeout:
            self._buffer = char  # Slow → reset (manual)
        else:
            self._buffer += char  # Fast → append (scanner)
        
        # Enter key triggers barcode emission
        if key == keyboard.Key.enter and len(self._buffer) >= self._min_barcode_length:
            self.barcode_scanned.emit(barcode)
```

**Main Window Integration:**
```python
class MainLoader(QMainWindow):
    def __init__(self):
        # Initialize scanner
        self.scanner = BarcodeScanner()
        self.scanner.barcode_scanned.connect(self.on_barcode_scanned)
        self.scanner.start()
        
        # Store table reference
        self.sales_table = None  # Set during UI loading
    
    def on_barcode_scanned(self, barcode: str):
        # Route to sales table (current implementation)
        if self.sales_table is not None:
            handle_barcode_scanned(self.sales_table, barcode, self.statusbar)
```

**Sales Table Handler (`modules/sales/salesTable.py`):**
```python
def handle_barcode_scanned(table, barcode, status_bar):
    # 1. Look up product
    found, product_name, unit_price = get_product_info(barcode)
    
    if not found:
        status_bar.showMessage(f"⚠ Product '{barcode}' not found")
        return
    
    # 2. Check if product exists in table
    existing_row = _find_product_in_table(table, barcode)
    
    if existing_row is not None:
        # 3a. Product exists → increment quantity
        _increment_row_quantity(table, existing_row)
    else:
        # 3b. New product → add row
        _add_product_row(table, barcode, product_name, unit_price, status_bar)
```

**Helper Functions:**
- `_find_product_in_table()` - Searches rows for matching product
- `_increment_row_quantity()` - Adds 1 to existing row quantity
- `_add_product_row()` - Appends new row to table (rebuilds table via `set_sales_rows()`)

**Testing Strategy:**
- Created `test_scanner.py` - Minimal Qt app to verify scanner signal emission
- Useful for debugging scanner without full POS UI
- Console debug output shows timing, buffer state, signal emission

**Dependencies Added:**
- `pynput>=1.7.6` - Keyboard listener library
- Already available in miniconda environment

**Technical Challenges Solved:**

1. **Thread Safety:**
   - Problem: pynput listener runs in background thread, Qt UI must update in main thread
   - Solution: Qt signals automatically queue events to main thread

2. **Widget Container Background Colors:**
   - Problem: QLineEdit cells don't show alternating row colors
   - Solution: Already solved with container approach (applies to scanner-added rows too)

3. **Dynamic Row Operations:**
   - Problem: Scanner might add product that already exists
   - Solution: Search table before adding, increment if found

4. **Signal Connection Timing:**
   - Problem: Sales table created after scanner initialization
   - Solution: Store table reference when UI loads, check for None in handler

**Performance:**
- Scanner listener: Minimal CPU usage (event-driven)
- Barcode processing: <5ms (cache lookup + table update)
- No noticeable lag when scanning rapidly

**Future Enhancements (Planned):**

1. **Context Switching:**
   - Implement `BarcodeContext` enum
   - Router in `on_barcode_scanned()` to direct to active section
   - Refund section: populate refund input field
   - Manual entry dialog: auto-fill product code
   - Menu options: price check, inventory lookup

2. **Scanner Configuration:**
   - Adjustable timeout for different scanner models
   - Enable/disable scanner (e.g., during data entry)
   - Minimum barcode length validation

3. **Multi-Quantity Scanning:**
   - Hold scanner button for rapid fire (3 scans = qty 3)
   - Or: scan twice in <2 seconds → qty 2

4. **Barcode Validation:**
   - Check format (EAN-13, UPC, etc.)
   - Checksum validation
   - Invalid format feedback

5. **Visual Feedback:**
   - Flash row when product added
   - Beep/sound on successful scan
   - Different sound for errors

6. **Scanner Status Indicator:**
   - Icon in status bar showing scanner active/inactive
   - Connection status for USB scanners

---

### October 31, 2025 - Database Integration

**Database Module Reorganization:**
- Created `modules/db_operation/` folder
- (Historical) Moved `product_crud.py` under `modules/db_operation/` and adjusted imports
- (Current) `product_crud.py` was later retired in favor of:
    - `db.py` (connections/transactions)
    - `products_repo.py` (SQL-only repository)
    - `product_cache.py` (in-memory `PRODUCT_CACHE` + `get_product_info()`)
    - `__init__.py` (public facade + compatibility wrappers)
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

## Update Summary (December 23, 2025)

### Dialog Button Naming and QSS Styling Standardization

- **Dialog button object names standardized** across all menu dialogs for consistency and maintainability:
    - Constructive actions (OK, Save, Add, Update, Print, etc.) now end with `Ok` (e.g., `btnAdminOk`, `btnVegMOk`, `btnTodayOk`).
    - Destructive actions (Delete/Remove) now end with `Del` (e.g., `btnVegMDel`).
    - Dismissive actions (Cancel/Close) now end with `Cancel` (e.g., `btnAdminCancel`, `btnVegMCancel`, `btnRangeCancel`).
- **All references in Python controller files updated** to match new object names.
- **QSS styling for QPushButton** now uses suffix-based selectors for consistent look and feel:
    - `[objectName$="Ok"]` for constructive (green)
    - `[objectName$="Del"]` for destructive (red)
    - `[objectName$="Cancel"]` for dismissive (gray)
    - Includes hover and pressed effects, and unified font styling.
- **Documentation and code comments updated** to reflect new naming and styling conventions.

Quality gates: PASS (manual dialog testing, button wiring, and visual validation). All dialogs now have consistent button appearance and reliable signal connections.

---
