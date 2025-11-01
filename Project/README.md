# ANUMANI POS System

A Point of Sale (POS) application built with PyQt5 and SQLite, featuring a product cache system for fast lookups and a modern UI design.

## Features

✅ **Database Integration**
- Connected to SQLite database (`Anumani.db`) with 22,337+ products
- Preloaded product cache for instant O(1) lookups
- Automatic product name and price fetching from database

✅ **Sales Management**
- Dynamic sales table with real-time calculations
- Quantity input with automatic total calculation
- Product lookup via barcode/product code
- Row deletion with visual feedback
- Alternating row colors for better readability

✅ **Modern UI**
- Runtime .ui file loading (Qt Designer compatible)
- Global QSS stylesheet for consistent theming
- Responsive em-based sizing
- Modal vegetable weight input dialog

✅ **Error Handling**
- Status bar notifications for invalid products
- Graceful fallback when database unavailable

## Project Structure

```
Project/
├── main.py                      # Application entry point
├── config.py                    # Configuration constants (colors, icons)
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── Project_Journal.md           # Detailed development documentation
├── assets/
│   ├── style.qss               # Global stylesheet
│   └── icons/
│       └── delete.svg          # Delete button icon
├── ui/
│   ├── main_window.ui          # Main application window
│   ├── sales_frame.ui          # Sales section UI
│   ├── payment_frame.ui        # Payment section UI
│   └── vegetable.ui            # Digital weight input dialog
└── modules/
    ├── db_operation/
    │   ├── __init__.py
    │   └── database.py         # Database connection & product cache
    └── sales/
        ├── __init__.py
        └── salesTable.py       # Sales table logic & row management
```

## Database Setup

The application expects a SQLite database at `../db/Anumani.db` (one level above the Project folder).

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
- Loads all products into memory on startup (~2-3 MB for 22K products)
- Provides instant lookups without repeated database queries
- Automatically refreshes when needed

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

### Adding Products to Sale

1. Use existing placeholder rows or add new rows via "Vegetable Entry" or "Manual Entry" buttons
2. Enter product code (barcode)
3. Product name and price are automatically fetched from database
4. Edit quantity as needed
5. Total calculates automatically

### Sales Table Operations

- **Edit Quantity:** Click quantity field, type number, press Enter
- **Delete Row:** Click red X button (row highlights before deletion)
- **View Total:** Calculated as Quantity × Unit Price

### Error Handling

- Invalid product codes show warning in status bar for 10 seconds
- Missing database loads with error message (check console output)

## Configuration

### Color Scheme (`config.py`)
```python
ROW_COLOR_EVEN = '#add8e6'  # Light blue (even rows)
ROW_COLOR_ODD = '#ffffe0'   # Light yellow (odd rows)
ROW_COLOR_DELETE_HIGHLIGHT = '#ff6b6b'  # Salmon red (deletion preview)
```

### Database Path (`modules/db_operation/database.py`)
```python
DB_PATH = os.path.join(os.path.dirname(BASE_DIR), 'db', 'Anumani.db')
```

## Development

### Editing UI Files

Open `.ui` files in Qt Designer:
```cmd
designer ui\main_window.ui
```

Changes are loaded automatically at runtime - no compilation needed.

### Refreshing Product Cache

To reload products after database changes:
```python
from modules.db_operation import refresh_product_cache
refresh_product_cache()
```

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

## Troubleshooting

### Database Not Found
```
✗ Database not found at: C:\Users\...\POS\db\Anumani.db
```
**Solution:** Ensure database exists at `../db/Anumani.db` relative to Project folder.

### No Products Loaded
**Solution:** Check database path and table schema. Verify `Product_list` table exists with correct columns.

### QSS Not Loading
**Solution:** Verify `assets/style.qss` exists. Check console for error messages.

## Dependencies

See `requirements.txt` for full list. Main dependencies:
- PyQt5 - GUI framework
- sqlite3 - Database (built-in with Python)

## License

[Add your license here]

## Contact

[Add contact information here]

---

**Last Updated:** October 31, 2025
