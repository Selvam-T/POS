## Note on Device Manager Functionality

The device manager functionality to configure devices such as barcode scanners, receipt printers, and electronic weighing scales was shelved and is not included in this project. This decision was made because such configuration was deemed out of the project scope.
# ANUMANI POS System

A Point of Sale (POS) application built with PyQt5 and SQLite. It features a preloaded product cache for instant lookups, a modular UI composed from .ui files, a compact icon-only right-side menu, and barcode scanner integration.

## Features

✅ **Database Integration**
- Connected to SQLite database (`Anumani.db`) with 22,337+ products
- Preloaded product cache for instant O(1) lookups
- Automatic product name and price fetching from database
 - Strict validation: lookups are performed against the in-memory cache only

✅ **Sales Management**
- Dynamic sales table with real-time calculations
- Quantity input with automatic total calculation
- Product lookup via barcode/product code
- Row deletion with visual feedback
- Alternating row colors for better readability
- Cancel All functionality with confirmation dialog to clear entire sales table

✅ **Modern UI**
- Runtime .ui file loading (Qt Designer compatible)
- Global QSS stylesheet for consistent theming
- Responsive em-based sizing
- Modal vegetable weight input dialog
 - Manual entry dialog (opened only from its button)
 - Right-side icon-only menu with tooltips and modal placeholders
 - Header layout: Date (left), Company (center), Day+Time (right as a single label)
 - Logout flow: dedicated logout dialog with dimmed background; main window Close (X) disabled to enforce proper logout
 - Custom, frameless logout dialog with a stylable title bar and large Close (X) button
 - Admin Settings dialog (Admin/Staff/Email tabs) with masked fields and eye toggles; wired to Admin menu button

✅ **Barcode Scanner**
- Global event filtering with timing-based scan-burst detection
- Focus-based routing: default to Sales table; accept only in `refundInput` when focused; in Product dialog only when `productCodeLineEdit` is focused
- Modal scanner block + dim overlay during dialogs (Manual/Vegetable/etc.) to prevent stray input and clicks
- Enter suppression during bursts and Enter-as-Tab in Product dialog; action buttons are non-default
- Always-on cache diagnostics per scan; optional debug toggles to log focus path and cache lookups

✅ **Error Handling**

- Status bar notifications for invalid products and dialog errors
- Graceful fallback when database or dialog UI files are unavailable
- Dialogs (e.g., Cancel Sale) use a minimal fallback if UI file is missing, with clear messaging and styled buttons
- All dialog/UI errors are logged to `log/error.log` with timestamp using a shared logger
- Windows-console-safe logging (ASCII only)

✅ **Consistent Dialog Button Styling**
- All dialog action buttons now use standardized object names:
    - Constructive: ends with `Ok` (e.g., `btnAdminOk`, `btnVegMOk`)
    - Destructive: ends with `Del` (e.g., `btnVegMDel`)
    - Dismissive: ends with `Cancel` (e.g., `btnAdminCancel`, `btnVegMCancel`)
- QSS uses suffix-based selectors for unified color, font, and hover/pressed effects across all dialogs.

## Project Structure

```
Project/
├── main.py                      # Application entry point & UI composer
├── config.py                    # Configuration constants (colors, etc.)
├── requirements.txt             # Python dependencies
├── README.md                    # Setup and usage
├── Project_Journal.md           # Detailed development documentation
├── test_scanner.py              # Minimal scanner verification app
├── tools/
│   └── format_assets.py         # Formatter for .ui (lxml) and .qss (jsbeautifier)
├── assets/
│   ├── main.qss                # Global stylesheet (QSS)
│   └── icons/                   # SVG/PNG icons (menu, delete, etc.)
├── ui/
│   ├── main_window.ui          # Main application window (info header + work area)
│   ├── sales_frame.ui          # Sales section UI
│   ├── payment_frame.ui        # Payment section UI
│   ├── menu_frame.ui           # Right-side menu (7 icon-only buttons)
│   ├── product_menu.ui         # Product Management dialog content
│   ├── vegetable_entry.ui      # Vegetable (weight) dialog content
│   ├── manual_entry.ui         # Manual entry dialog content
│   ├── logout_menu.ui          # Logout confirmation dialog (frameless, custom title bar)
│   └── admin_menu.ui           # Admin Settings dialog (Admin/Staff/Email tabs)
└── modules/
   ├── db_operation/
   │   ├── __init__.py
   │   ├── db.py                   # Shared sqlite plumbing (path/conn/transaction)
   │   ├── products_repo.py        # Product_list SQL-only repository
   │   └── product_cache.py        # App-wide in-memory PRODUCT_CACHE + fast lookups
   ├── devices/
   │   ├── __init__.py         # Exports BarcodeScanner
   │   └── scanner.py          # Barcode scanner integration (pynput)
   ├── menu/
   │   ├── __init__.py         # Menu exports
   │   ├── logout_menu.py      # Logout dialog controller (frameless, dim overlay, wiring)
   │   └── admin_menu.py       # Admin Settings dialog controller (loads ui/admin_menu.ui)
   └── sales/
      ├── __init__.py
      └── salesTable.py       # Sales table logic & row management
```

## Database Setup

The application expects a SQLite database at `../db/Anumani.db` (one level above the Project folder). The path is centralized in `config.py` as `DB_PATH` and used across the app.

**Required table schema:**
```sql
CREATE TABLE Product_list (
    product_code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    selling_price REAL NOT NULL,
    category TEXT,
    supplier TEXT,
    cost_price REAL,
    unit TEXT,
    last_updated TEXT
);
```

**Product Cache:**
- Loads all products into memory on startup
- Keys are normalized (uppercase + trimmed) to avoid case/whitespace mismatches
- Cache updates immediately on ADD/UPDATE/DELETE
- Automatically refreshed after a Product dialog ADD/UPDATE/DELETE to guarantee consistency

## Quick Start

### Prerequisites
- Python 3.7+
- SQLite database at `../db/Anumani.db`

### Installation (Windows)

1. **Create and activate a virtual environment** (recommended):
   ```cmd
   py -3 -m venv .venv
   .venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```cmd
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```cmd
   python main.py
   ```

Optional: verify the barcode scanner with the minimal test app:

```cmd
python test_scanner.py
```

### Installation (Linux/macOS)

1. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```

## Usage
### Header layout (infoSection)

The header at the top of `main_window.ui` is a three-part `QHBoxLayout` named `infoSection`:

- `labelDate` (QLabel) — left aligned
- `labelCompany` (QLabel) — centered
- `labelDayTime` (QLabel) — right aligned, shows combined text like "Thursday 12:00"

Implementation details:

- The old `dayTimeArea` sub-layout and `labelDay`/`labelTime` were removed; `labelDayTime` replaces them.
- Stretch is set programmatically to `1,0,1` so the center stays truly centered.
- QSS no longer forces header label alignment; we use padding for consistent spacing:
   - `QLabel#labelDate { padding-left: 30px; }`
   - `QLabel#labelDayTime { padding-right: 30px; }`
   - You can adjust padding in `assets/main.qss`.


### Adding Products to Sale

1. Use existing placeholder rows or add new rows via "Vegetable Entry" or "Manual Entry" buttons
2. Enter product code (barcode)
3. Product name and price are automatically fetched from database
4. Edit quantity as needed
5. Total calculates automatically

### Scanning Barcodes

- Scan a product barcode with the scanner connected to the POS machine.
- Default behavior: if found in the cache, the product is added to the sales table (or quantity increments).
- Not found (in Sales frame): Product Management opens in ADD mode with the code prefilled. After you save, the new item is automatically added to the sales table.
- Product dialog open: scans are accepted only when the `productCodeLineEdit` is focused; Enter behaves like Tab; buttons are non-default to avoid accidental clicks.
- Payment frame: if `refundInput` is focused, the scan is applied to that field; otherwise the scan routes to the sales table.
- Quantity input (`qtyInput`) is protected: scans are ignored and any stray character is cleaned up.
- Manual and Vegetable dialogs: a modal scanner block is active and the background is dimmed; scans and Enter are swallowed until the dialog closes.

For a deep dive into the exact routing rules, protections, and debug options, see Documentation/scanner_input_infocus.md.

### Logout and window close behavior

- The main window's Close (X) and Alt+F4 are disabled and ignored. Use the Logout button in the right menu to exit.
- Clicking Logout opens a modal confirmation dialog (frameless) and dims the background.
- Yes, Logout: stops the scanner and exits the app. Cancel returns to the app.
- Styling the logout dialog:
   - Title bar background: `QFrame#customTitleBar` in `assets/main.qss`
   - Close (X) button: `QPushButton#customCloseBtn` (font size, colors, hover/pressed)
   - Tip: Use 6‑digit hex `#RRGGBB` (or 8-digit `#ffRRGGBB`) for opaque colors. `#AARRGGBB` with a low AA will appear washed out.

Controller location and wiring:
- Controller function: `modules/menu/logout_menu.py` → `open_logout_dialog(host_window)`
- The menu button in `main.py` calls `open_logout_dialog(self)` when `logoutBtn` is clicked.

### Sales-in-progress restrictions

To prevent inconsistencies between items already listed in the current sale and the master product data:

- When the Sales table contains one or more items, the Product Management dialog allows only ADD.
- REMOVE and UPDATE/View are disabled while a sale is in progress.
- Finish or cancel the current sale (clear the Sales table) to re-enable REMOVE/UPDATE/View.

### Sales Table Operations

- **Edit Quantity:** Click quantity field, type number, press Enter
- **Delete Row:** Click red X button (row highlights before deletion)
- **View Total:** Calculated as Quantity × Unit Price

#### Grand total (totalValue)

- The `QLabel#totalValue` in `sales_frame.ui` is bound at runtime and always shows the sum of all row totals (column 4).
- It updates immediately when rows are added, quantities change, prices change, or rows are deleted.
- Scanner “leak” and reversal: if a transient character briefly changes a quantity and is then cleaned, the grand total is recomputed and returns to the correct value.
- Developer helpers (in `modules/sales/salesTable.py`):
   - `bind_total_label(table, label)` — attach the label to a sales table instance (called in `main.py`).
   - `recompute_total(table) -> float` — recompute from column 4 and refresh the label.
   - `get_total(table) -> float` — read the last computed total (e.g., for Payment frame).
  
Note: The static text in the `.ui` file remains `$ 0.00`; the value is updated at runtime.

### Error Handling

- Invalid product codes show warning in status bar for 10 seconds
- Missing database loads with error message (check console output)

### Right-side Menu

The compact icon-only menu lives on the right side and contains seven buttons:

- Admin, Reports, Vegetable, Product, Greeting, Device, Logout
- Buttons show their label on hover via tooltips.
- Clicking any button currently opens a modal with a placeholder message and dims the background.
- Buttons are square (64x64) with gray borders and large icons; menu width is constrained to stay narrow.

Logout button opens the dedicated Logout dialog described above.

## Configuration

### Color Scheme (`config.py`)
```python
ROW_COLOR_EVEN = '#add8e6'  # Light blue (even rows)
ROW_COLOR_ODD = '#ffffe0'   # Light yellow (odd rows)
ROW_COLOR_DELETE_HIGHLIGHT = '#ff6b6b'  # Salmon red (deletion preview)
```

### Database Path (`config.py`)
`DB_PATH` is defined in `config.py` and points to `../db/Anumani.db` relative to the Project folder.

## Development

### Editing UI Files

Open `.ui` files in Qt Designer:
```cmd
designer ui\main_window.ui
```

Changes are loaded automatically at runtime—no compilation needed.

### Formatting UI (.ui) and styles (.qss)

A small formatter script keeps Qt Designer XML and stylesheets tidy:

- .ui files: formatted with lxml (pretty-printed, normalized whitespace)
- .qss files: formatted with jsbeautifier (CSS-style formatter)

Run from the project root:

```cmd
pip install -r requirements.txt
python tools\format_assets.py
```

Notes:
- XML attribute order may change on first run (semantically safe).
- QSS is CSS-like; most files format well—quick review recommended for Qt-specific selectors.

### Product Management Documentation

See `Documentation/product_menu.md` for in-depth behavior, rationale, and integration details.

### Adding New Features

See `Project_Journal.md` for detailed architecture documentation, design decisions, and implementation rationale.

## Documentation


- **README.md** (this file) - Setup guide and usage instructions
- **Project_Journal.md** - Complete development documentation with:
   - Widget hierarchy and parent-child relationships
   - Design decisions and rationale
   - Implementation details
   - Code examples and technical explanations
   - Development history
- **error_logging_and_fallback.md** - Error logging and fallback dialog documentation
- Database layer architecture: see Documentation/db_operation.md for `modules/db_operation` structure and public API.
- Scanner input architecture: see Documentation/scanner_input_infocus.md for focus-first routing, modal block, and debug guidance.
- Logout dialog and custom title bar: see Documentation/logout_and_titlebar.md for styling and behavior details.
- Admin Settings dialog: see Documentation/admin_settings.md for structure, wiring, and QSS hooks.

## Troubleshooting

### Database Not Found
```
✗ Database not found at: C:\Users\...\POS\db\Anumani.db
```
**Solution:** Ensure database exists at `../db/Anumani.db` relative to Project folder.

### No Products Loaded
**Solution:** Check database path and table schema. Verify `Product_list` table exists with correct columns.

### QSS Not Loading
**Solution:** Verify `assets/main.qss` exists. Check console for error messages.

### Scanner types characters into the wrong field
This can happen with HID “keyboard wedge” scanners before the app detects the scan burst (first-character leak). The app:
- Blocks scans during modal dialogs and dims the background
- Ignores scans in `qtyInput` and cleans stray characters
- Suppresses Enter during scan bursts to avoid clicking default buttons

See Documentation/scanner_input_infocus.md for details, debug flags, and optional hardware-level fixes (prefix/suffix or serial mode).

## Dependencies

See `requirements.txt` for full list. Main dependencies:
- PyQt5 - GUI framework
- sqlite3 - Database (built-in with Python)
- pynput - Barcode scanner keyboard listener

## License

[Add your license here]

## Contact

[Add contact information here]

---
**Last Updated:** November 5, 2025
