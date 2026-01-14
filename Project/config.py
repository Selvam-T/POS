import os
# Dialog size ratios (width_ratio, height_ratio) as fraction of main window
DIALOG_RATIOS = {
	'vegetable_entry': (0.5, 0.9),
	'manual_entry': (0.4, 0.3),
	'logout_menu': (0.25, 0.25),
	'admin_menu': (0.4, 0.3),
	'history_menu': (0.4, 0.4),
	'reports_menu': (0.7, 0.7),
	'greeting_menu': (0.3, 0.3),
	'product_menu': (0.5, 0.7),
	'vegetable_menu': (0.32, 0.7),
	'hold_sales': (0.4, 0.4),
	'view_hold': (0.5, 0.7),
	'cancel_sale': (0.25, 0.25),
    'MaxRowsDialog': (0.25, 0.25)
}

# Product Categories
PRODUCT_CATEGORIES = [
    'Alcohol',
	'Beverages',
	'Bread & Bakery',
	'Canned & Packaged Foods',
	'Dairy Products',
	'Frozen Foods',
	'Household Supplies',
	'Personal Care',
	'Snacks & Confectionery',
	'Tobacco',
	'Vegetables',
	'Other'
]

# Maximum allowed rows in active sales table
MAX_TABLE_ROWS = 50

# Greeting message options
GREETING_STRINGS = [
	"Happy Deepavali !",
	"Happy New Year !!!",
	"Merry Christmas !",
	"Gōng xǐ fā cái !",
	"Selamat Hari Raya !",
	"Happy Vesak Day !",
	"Selamat Hari Raya Haji !",
	"Majulah Singapura !",
	"Happy Labor Day !",
	"Happy Good Friday !",
	"Thanks for shopping with us!"
]

# Table row colors
ROW_COLOR_EVEN = '#add8e6'      # Even row color
ROW_COLOR_ODD = '#ffffe0'       # Odd row color
ROW_COLOR_DELETE_HIGHLIGHT = '#ff6b6b'  # Row deletion highlight

# Icon file paths
ICON_DELETE = 'assets/icons/delete.svg'
ICON_ADMIN = 'assets/icons/admin.svg'
ICON_REPORTS = 'assets/icons/reports.svg'
ICON_VEGETABLE = 'assets/icons/vegetable.svg'
ICON_PRODUCT = 'assets/icons/product.svg'
ICON_GREETING = 'assets/icons/greeting.svg'
ICON_HISTORY = 'assets/icons/receipt_history.svg'
ICON_LOGOUT = 'assets/icons/logout.svg'

# Date/time display formats
DATE_FMT = 'd MMM yyyy'
DAY_FMT = 'ddd'
TIME_FMT = 'hh : mm ap'

# Company name for header
COMPANY_NAME = 'Anumani Trading Pte Ltd'

# Database path (absolute)
_BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(os.path.dirname(_BASE_DIR), 'db', 'Anumani.db')

# Debug flags (disabled; console logging removed)
DEBUG_SCANNER_FOCUS = False
DEBUG_FOCUS_CHANGES = False
DEBUG_CACHE_LOOKUP = False

# Writable app data directory and feature constants
APPDATA_DIR = os.path.join(_BASE_DIR, 'AppData')
VEG_SLOTS = 16
