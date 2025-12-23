"""
Configuration file for POS application.

This file centralizes color definitions and other configuration values
that need to be shared across multiple modules.

Also defines the SQLite database path (DB_PATH) so it's easy to locate
and override from a single place if needed.
"""

import os

# =============================================================================
# TABLE ROW COLORS
# =============================================================================
# Alternating row colors for the sales table.
#
# WHY DEFINED IN PYTHON INSTEAD OF QSS:
# -----------------------------------------------------------------------------
# Qt's QSS does support alternating row colors via QTableWidget::item:alternate,
# but that only works when table.setAlternatingRowColors(True) is enabled.
#
# In our sales table, we have cell widgets (QLineEdit for quantity input and
# QPushButton for delete) embedded in columns 2 and 5. These widgets sit inside
# container QWidgets, and their background colors must be set programmatically
# via setStyleSheet() to match the row color. QSS alternating colors don't
# automatically propagate to these embedded widgets.
#
# Therefore, we:
# 1. Disable Qt's built-in alternating colors (setAlternatingRowColors(False))
# 2. Manually assign background colors to both QTableWidgetItems (via setBackground)
#    and container widgets (via setStyleSheet) in Python
# 3. Centralize color values here for maintainability
# -----------------------------------------------------------------------------

ROW_COLOR_EVEN = '#add8e6'  # Light blue for even rows (0, 2, 4, ...)
ROW_COLOR_ODD = '#ffffe0'   # Light yellow for odd rows (1, 3, 5, ...)

# Highlight color for row deletion preview
ROW_COLOR_DELETE_HIGHLIGHT = '#ff6b6b'  # Light red/salmon

# =============================================================================
# ICONS
# =============================================================================
# Icon file paths
ICON_DELETE = 'assets/icons/delete.svg'  # Delete/remove button icon

# Menu and toolbar icons
ICON_ADMIN = 'assets/icons/admin.svg'
ICON_REPORTS = 'assets/icons/reports.svg'
ICON_VEGETABLE = 'assets/icons/vegetable.svg'
ICON_PRODUCT = 'assets/icons/product.svg'
ICON_GREETING = 'assets/icons/greeting.svg'
ICON_DEVICE = 'assets/icons/device.svg'
ICON_LOGOUT = 'assets/icons/logout.svg'

# =============================================================================
# DATE / TIME FORMATS (UI DISPLAY)
# =============================================================================

# Example output: 3 Nov 2025
DATE_FMT = 'd MMM yyyy'

# Example output: Fri
DAY_FMT = 'ddd'

# Example output: 12:22 am
TIME_FMT = 'hh : mm ap'

# =============================================================================
# APP TEXT: COMPANY NAME (baked-in)
# =============================================================================
# Company name shown in the header label 'labelCompany'. This is baked into the
# build and does not change per machine.
COMPANY_NAME = 'Anumani Trading Pte Ltd'

# =============================================================================
# DATABASE PATH
# =============================================================================
# Resolved relative to the repository layout:
#   Project/config.py           (this file)
#   POS/db/Anumani.db           (database lives one level above Project in db/)
#
# Final absolute path example:
#   C:\Users\<USER>\OneDrive\Desktop\POS\db\Anumani.db

_BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # .../POS/Project
DB_PATH = os.path.join(os.path.dirname(_BASE_DIR), 'db', 'Anumani.db')

# =============================================================================
# DEBUG FLAGS
# =============================================================================
# Enable to print where the keyboard/scanner focus is when a barcode is handled
# in the UI. Helpful to understand which widget is active during scans.
DEBUG_SCANNER_FOCUS = True

# Enable to log every Qt focus change (very verbose).
DEBUG_FOCUS_CHANGES = False

# Enable to log cache lookup result for every scanned code
DEBUG_CACHE_LOOKUP = True

# =============================================================================
# APPDATA / FEATURE CONSTANTS
# =============================================================================
# Writable folder for JSON-based settings (e.g., vegetables.json). Not an asset.
# Created at runtime if missing. Keep user-specific data out of version control
# by adding AppData/*.json to .gitignore if desired.
APPDATA_DIR = os.path.join(_BASE_DIR, 'AppData')

# Number of vegetable buttons to manage (veg1..vegN). The vegetable entry UI
# currently provides 16 slots.
VEG_SLOTS = 16
