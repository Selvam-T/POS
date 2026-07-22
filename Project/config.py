import os
import re
import sys
from datetime import date


# -----------------------------------------------------------------------------
# Deployment paths
# -----------------------------------------------------------------------------

def _resolve_path_layout(module_file=None, executable=None, frozen=None):
    """Resolve development and packaged roots without relying on the CWD."""
    runtime_dir = os.path.abspath(os.path.dirname(module_file or __file__))
    is_packaged = bool(
        getattr(sys, 'frozen', False) if frozen is None else frozen
    )
    if is_packaged:
        app_dir = os.path.abspath(os.path.dirname(executable or sys.executable))
        client_root = os.path.dirname(app_dir)
    else:
        app_dir = runtime_dir
        client_root = os.path.dirname(runtime_dir)

    return {
        'is_packaged': is_packaged,
        'runtime_dir': runtime_dir,
        'app_dir': app_dir,
        'client_root': client_root,
        'assets_dir': os.path.join(runtime_dir, 'assets'),
        'ui_dir': os.path.join(runtime_dir, 'ui'),
        'db_dir': os.path.join(client_root, 'db'),
        'logs_dir': os.path.join(client_root, 'logs'),
        'backups_dir': os.path.join(client_root, 'backups'),
        'data_dir': os.path.join(client_root, 'data'),
    }


_PATHS = _resolve_path_layout()
IS_PACKAGED = _PATHS['is_packaged']
RUNTIME_DIR = _PATHS['runtime_dir']
APP_DIR = _PATHS['app_dir']
CLIENT_ROOT = _PATHS['client_root']
ASSETS_DIR = _PATHS['assets_dir']
QSS_DIR = os.path.join(ASSETS_DIR, 'qss')
UI_DIR = _PATHS['ui_dir']
DB_DIR = _PATHS['db_dir']
LOGS_DIR = _PATHS['logs_dir']
BACKUPS_DIR = _PATHS['backups_dir']
DATA_DIR = _PATHS['data_dir']

DATABASE_FILENAME = 'Anumani.db'
LOGIN_LOGO_FILENAME = 'anumani_logo.png'
ERROR_LOG_FILENAME = 'error.log'
BARCODE_ROUTING_LOG_FILENAME = 'barcode_routing.log'

# Existing modules still use this alias for runtime resource paths.
_BASE_DIR = RUNTIME_DIR
DB_PATH = os.path.join(DB_DIR, DATABASE_FILENAME)
LOG_PATH = os.path.join(LOGS_DIR, ERROR_LOG_FILENAME)
BARCODE_ROUTING_LOG_PATH = os.path.join(LOGS_DIR, BARCODE_ROUTING_LOG_FILENAME)
LOGIN_BACKGROUND = os.path.join(
    ASSETS_DIR, 'images', LOGIN_LOGO_FILENAME
)

# Runtime resources are read-only; mutable state lives outside the app bundle.
JSON_DATA_DIR = os.path.join(DATA_DIR, 'json')
APPDATA_DIR = JSON_DATA_DIR
ADS_DIR = os.path.join(DATA_DIR, 'ads')

# Single source for the application release version.
# Use semantic versioning: major.minor.patch.
# Examples: 1.0.0 first release, 1.1.0 feature release, 1.1.1 bug fix.
APP_VERSION = '1.0.0'

# -----------------------------------------------------------------------------
# Business identity and localization
# -----------------------------------------------------------------------------

COMPANY_NAME = 'ANUMANI TRADING PTE LTD'
ADDRESS_LINE_1 = 'BLK 77 INDUS RD, #01-501'
ADDRESS_LINE_2 = 'INDUS GARDEN SINGAPORE'


DATE_FMT = 'd MMM yyyy'
DAY_FMT = 'ddd'
TIME_FMT = 'hh : mm ap'

GREETING_STRINGS = [
    'Happy Deepavali !',
    'Happy New Year !!!',
    'Merry Christmas !',
    'Gōng xǐ fā cái !',
    'Selamat Hari Raya !',
    'Happy Vesak Day !',
    'Selamat Hari Raya Haji !',
    'Majulah Singapura !',
    'Happy Labor Day !',
    'Happy Good Friday !',
    'Thanks for shopping with us!',
]

# Runtime selections can override this default through persisted app data.
GREETING_SELECTED = 'Thanks for shopping with us!'


# -----------------------------------------------------------------------------
# Development / production switchboard
# -----------------------------------------------------------------------------
# Review these flags when switching between development, testing, and production.
# Keep all environment-dependent toggles here so release readiness is easy to audit.

# Login and access: development can bypass login; production should require login.
LOGIN_ON = False  # False bypasses login and uses AUTO_LOGIN_* below.
AUTO_LOGIN_UID = 1  # User id injected when LOGIN_ON is False.
AUTO_LOGIN_USERNAME = 'Developer'  # Username injected when LOGIN_ON is False.
AUTO_LOGIN_IS_ADMIN = True  # Grants admin role to the auto-login user.

# Trial build gate: enable only for time-limited trial executables.
TRIAL_BUILD_ENABLED = False  # True blocks launch after TRIAL_EXPIRY_DATE/build-clock checks.
TRIAL_EXPIRY_DATE = date(2026, 6, 30)
TRIAL_EXPIRED_MESSAGE = 'Testing period expired. Please contact SelvamPOS support.'

# Vegetable scale fallback: use only when weighing scale hardware is not installed/ready.
VEG_KG_MANUAL_GRAMS_FALLBACK = True  # True lets cashier enter KG vegetables as whole grams.

# Printer and cash drawer: enable only when production hardware is configured and tested.
ENABLE_PRINTER_PRINT = False  # True sends receipt text to the network printer.
ENABLE_CASH_DRAWER = False  # True pulses the cash drawer after successful cash payment.

# Customer display launch mode: test mode uses a normal window; production uses target screen.
CUSTOMER_DISPLAY_ENABLED = True  # False skips creating the customer-facing display.
CUSTOMER_DISPLAY_TEST_MODE = True  # True opens customer display as a normal test window.
CUSTOMER_DISPLAY_FULLSCREEN = False  # True makes the customer display fullscreen.
CUSTOMER_DISPLAY_AUTO_DETECT = True  # Ignored while CUSTOMER_DISPLAY_TEST_MODE is True.

# Scanner timing. The key interval identifies scanner-like bursts; the UI
# suppression window only protects Enter/Return from triggering default actions.
SCANNER_KEY_INTERVAL_SECONDS = 0.05
SCANNER_UI_SUPPRESS_SECONDS = 0.90


# -----------------------------------------------------------------------------
# Main UI and dialog presentation
# -----------------------------------------------------------------------------

# Dialog size as a fraction of the main window: (width, height).
DIALOG_RATIOS = {
    'login': (0.25, 0.3),
    'vegetable_entry': (0.5, 0.9),
    'manual_entry': (0.4, 0.3),
    'logout_menu': (0.25, 0.25),
    'admin_menu': (0.45, 0.5),
    'receipt_menu': (0.75, 0.9),
    'report_menu': (0.45, 0.6),
    'greeting_menu': (0.3, 0.3),
    'todo': (0.45, 0.6),
    'product_menu': (0.5, 0.73),
    'vegetable_menu': (0.32, 0.7),
    'hold_sales': (0.4, 0.3),
    'view_hold': (0.5, 0.7),
    'clear_cart': (0.25, 0.25),
    'refund': (0.35, 0.5),
    'vendor': (0.30, 0.5),
    'MaxRowsDialog': (0.25, 0.25),
}

# Product Management tab-specific (width_ratio, height_ratio).
PRODUCT_MENU_TAB_RATIOS = {
    'add': (0.5, 0.75),
    'remove': (0.5, 0.80),
    'update': (0.5, 0.90),
    'category': (0.5, 0.60),
}

REPORT_VIEWER_RATIOS = (0.6, 0.85)

PERSISTENT_DURATION_MS = 0

# StatusLabel message durations
STATUS_LABEL_SHORT_DURATION_MS = 2500
STATUS_LABEL_DURATION_MS = 3500
STATUS_LABEL_LONG_DURATION_MS = 5000

# StatusBar message durations
MAIN_STATUS_SHORT_DURATION_MS = 3000
MAIN_STATUS_DURATION_MS = 4000
MAIN_STATUS_EXTENDED_DURATION_MS = 4500
MAIN_STATUS_ERROR_DURATION_MS = 4000
MAIN_STATUS_LONG_DURATION_MS = 5000

# Transaction table row colors. These are used in the main window and in dialogs.
ROW_COLOR_EVEN = '#add8e6'
ROW_COLOR_ODD = '#ffffe0'
ROW_COLOR_DELETE_HIGHLIGHT = '#ff6b6b'

# Absolute runtime paths work in source and PyInstaller layouts.
ICON_DELETE = os.path.join(ASSETS_DIR, 'icons', 'delete.svg')
ICON_ADMIN = os.path.join(ASSETS_DIR, 'icons', 'admin.svg')
ICON_REPORTS = os.path.join(ASSETS_DIR, 'icons', 'reports.svg')
ICON_VEGETABLE = os.path.join(ASSETS_DIR, 'icons', 'vegetable.svg')
ICON_PRODUCT = os.path.join(ASSETS_DIR, 'icons', 'product.svg')
ICON_GREETING = os.path.join(ASSETS_DIR, 'icons', 'greeting.svg')
ICON_RECEIPT = os.path.join(ASSETS_DIR, 'icons', 'receipt.svg')
ICON_LOGOUT = os.path.join(ASSETS_DIR, 'icons', 'logout.svg')


# -----------------------------------------------------------------------------
# Sales, products, and local feature data
# -----------------------------------------------------------------------------

MAX_TABLE_ROWS = 50

# vegetable-entry
VEG_SLOTS = 16

# todo list: 12 rows, 40 characters max per item.
TODO_ROWS = 12
TODO_ITEM_MAX_LEN = 40

# Product category labels should not exceed 25 characters.
PRODUCT_CATEGORIES = [
    '--Select Category--',
    'Bakery Goods',
    'Beer',
    'Beverages',
    'Breakfast Items',
    'Canned Food',
    'Condiments & Sauce',
    'Cooking Oil',
    'Dairy Products',
    'Egg',
    'F&n',
    'Frozen Food',
    'General Merchandise',
    'Household Products',
    'Ice Cream',
    'Indian Provision',
    'Indian Snacks',
    'Kitchen Essentials',
    'Liquor',
    'Marigold',
    'Noodles',
    'Personal Care',
    'Pet Products',
    'Poojai Items',
    'Rice',
    'Snacks',
    'Telecom',
    'Tobacco',
    'Vegetable',
    'Other',
]
PROTECTED_CATEGORIES = ['Other', '--Select Category--']

# Seeded from PRODUCT_CATEGORIES only when the JSON store does not yet exist.
CATEGORIES_JSON_FILENAME = 'categories.json'
CATEGORIES_JSON_PATH = os.path.join(APPDATA_DIR, CATEGORIES_JSON_FILENAME)
CATEGORIES_JSON_BACKUP_PREFIX = 'categories.json.bak.'
CATEGORIES_JSON_SCHEMA = {
    'type': 'object',
    'properties': {
        'categories': {
            'type': 'array',
            'items': {'type': 'string'},
        }
    },
    'required': ['categories'],
}


# -----------------------------------------------------------------------------
# Validation and input limits
# -----------------------------------------------------------------------------

PRODUCT_CODE_MIN_LEN = 1
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

STRING_MAX_LENGTH = 40
PASSWORD_MIN_LENGTH = 8

EMAIL_REGEX = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
ALPHANUMERIC_REGEX = re.compile(r"^[A-Za-z0-9 \-']+$")
NAME_REGEX = re.compile(r"^[A-Za-z0-9\s.,'&()\-/]+$")

# Field-specific rules retained for consumers that use STRING_CONFIG directly.
STRING_CONFIG = {
    'product_code': {'min_len': 1, 'max_len': 15, 'required': True},
    'product_name': {'min_len': 4, 'max_len': 40, 'required': True},
    'supplier': {'min_len': 3, 'max_len': 15, 'required': False},
    'customer': {'min_len': 3, 'max_len': 25, 'required': True},
    'note': {'min_len': 0, 'max_len': 40, 'required': False},
    'category': {'min_len': 3, 'max_len': 25, 'required': False},
}


# -----------------------------------------------------------------------------
# Receipts and PayNow
# -----------------------------------------------------------------------------

RECEIPT_DEFAULT_WIDTH = 56 # 56 for font a, 60 for font b
RECEIPT_QTY_WIDTH = 9  # Quantity plus unit.
RECEIPT_AMOUNT_WIDTH = 9  # Summary/payment amounts include "$ ".
RECEIPT_ITEM_AMOUNT_WIDTH = 9  # Item price/total columns omit "$ ".
RECEIPT_GAP = 1
RECEIPT_PRINTER_FONT = 'a'  # ESC/POS receipt font: 'a' or 'b'.
RECEIPT_COMPANY_NAME_WIDTH = 2  # ESC/POS width scale for the first receipt line.
RECEIPT_COMPANY_NAME_HEIGHT = 2  # ESC/POS height scale for the first receipt line.

# Lowercase names are retained because qr_generator imports this public API.
merchant_name = 'Anumani Trading Pte Ltd'
merchant_city = 'Singapore'
country_code = 'SG'
currency = 'SGD'
paynow_proxy_type = 'UEN'
paynow_proxy_value = '201940352W'
paynow_proxy_suffix = '888' # The 3-digit voice box bank intermediary (EPOS) code
paynow_editable_amount_indicator = '1'  # Tag 26, Sub-tag 03 = '1'
transaction_id = '20270707103059'        # Tag 04 payload
bill_reference = 'EPOSSPSW74Y0GVMXU2RYWM33'
mcc = '0000'

error_correction = 'H'
box_size = 10
border = 3
expiry_seconds = 600
logo = 'paynow_logo.png'


# -----------------------------------------------------------------------------
# Printer and cash drawer hardware
# -----------------------------------------------------------------------------

PRINTER_IP = '192.168.0.10'
PC_IP = '192.168.0.5'
SUBNET_MASK = '255.255.255.0'
PRINTER_PORT = 9100

CASH_DRAWER_PIN = 2
CASH_DRAWER_TIMEOUT = 5.0


# -----------------------------------------------------------------------------
# Customer display and advertisements
# -----------------------------------------------------------------------------

MAX_ADS = 20
ALLOWED_EXTS = {'.jpg', '.jpeg', '.png'}
REQ_WIDTH = 1280
REQ_HEIGHT = 800
REQ_RATIO = REQ_WIDTH / REQ_HEIGHT
ADS_SIZE_TOLERANCE_PCT = 2.5

CUSTOMER_SCREEN_INDEX = 1
CUSTOMER_SCREEN_WIDTH = 1280 #1536
CUSTOMER_SCREEN_HEIGHT = 800 #900

CUSTOMER_DISPLAY_IDLE_TIMEOUT = 5
CUSTOMER_DISPLAY_IDLE_AD_INTERVAL = 6

CUSTOMER_DISPLAY_DATE_FMT = '%#d %b %Y'
CUSTOMER_DISPLAY_TIME_FMT = TIME_FMT

# Static QR image option for Screen 2; False keeps generated PayNow QR rendering.
CUSTOMER_DISPLAY_USE_STATIC_QR_IMAGE = True
CUSTOMER_DISPLAY_QR_IMAGE_FILENAME = 'eposQR.png'
