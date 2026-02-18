import os
import re
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
	'clear_cart': (0.25, 0.25),
    'MaxRowsDialog': (0.25, 0.25)
}

# Product Categories (Don't exceed 25 Characters)
PRODUCT_CATEGORIES = [
    '--Select Category--',
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

# Company name for header and receipts
COMPANY_NAME = 'Anumani Trading Pte Ltd'
ADDRESS_LINE_1 = "BLK 77 INDUS RD, #01-501"
ADDRESS_LINE_2 = "INDUS GARDEN SINGAPORE"

# Receipt formatting
RECEIPT_DEFAULT_WIDTH = 48
RECEIPT_QTY_WIDTH = 7
RECEIPT_AMOUNT_WIDTH = 8  # $9999.99
RECEIPT_GAP = 2

# Network settings for printer
PRINTER_IP = "192.168.0.10"
PC_IP = "192.168.0.5"
SUBNET_MASK = "255.255.255.0"
PRINTER_PORT = 9100
ENABLE_PRINTER_PRINT = True # set to True to enable network printing
# Cash drawer settings
ENABLE_CASH_DRAWER = True # set to True to enable cash drawer
CASH_DRAWER_PIN = 2
CASH_DRAWER_TIMEOUT = 2.0

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

# =========================================================
# Validation / Input Constraints (moved from input_validation.py)
# =========================================================

PRODUCT_CODE_MIN_LEN = 4
PRODUCT_CODE_MAX_LEN = 15

QUANTITY_MIN_KG = 0.005
QUANTITY_MAX_KG = 25.0
QUANTITY_MIN_UNIT = 1
QUANTITY_MAX_UNIT = 9999

UNIT_PRICE_MIN = 0.1
UNIT_PRICE_MAX = 5000

CURRENCY_MIN = 0.1
CURRENCY_MAX = 100000

VOUCHER_MIN = 1
VOUCHER_MAX = 1000

# STRING LENGTH for product_name, category, supplier, note
STRING_MAX_LENGTH = 40
PASSWORD_MIN_LENGTH = 8

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")
ALPHANUMERIC_REGEX = re.compile(r"^[A-Za-z0-9 \-']+$")

# ALTERNATIVE: Field-specific configurations (not implemented yet with validate_field)
STRING_CONFIG = {
    'product_code': {'min_len': 4, 'max_len': 14, 'required': True},
    'product_name': {'min_len': 4, 'max_len': 40, 'required': True},
    'supplier': {'min_len': 3, 'max_len': 15, 'required': False},  
    'notes': {'min_len': 0, 'max_len': 25, 'required': False}, 
    'category': {'min_len': 4, 'max_len': 25, 'required': False}
}

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

# Current greeting message (can be updated by admin)
GREETING_SELECTED = "Thanks for shopping with us!"
