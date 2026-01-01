"""
input_validation.py
Centralized validation functions for POS dialogs and frames.

- All validation logic for user input fields is implemented here.
- Each function returns (True, "") if valid, or (False, error_message) if invalid.
- For error message propagation, call ui_feedback from within this module as needed.
- Controllers/dialogs should use these functions via input_handler.py for all input validation.

Validation functions include:
- validate_quantity(value, unit_type='unit')
- validate_unit_price(value)
- validate_total_price(value)
- validate_product_code(value)
- validate_product_name(value)
- validate_email(value)
- validate_password(value)
- validate_supplier(value)
- validate_category(value)
- validate_price(value, price_type)
- validate_unit(value)

See each function for parameter and return details.
"""

import re

# Numeric validation constants
QUANTITY_MIN_KG = 0.01
QUANTITY_MIN_UNIT = 1
QUANTITY_MAX = 9999
UNIT_PRICE_MIN = 0.1
UNIT_PRICE_MAX = 5000
TOTAL_PRICE_MIN = 0
TOTAL_PRICE_MAX = 10000
GRAND_TOTAL_MIN = 0
GRAND_TOTAL_MAX = 100000
STRING_MAX_LENGTH = 15
PASSWORD_MIN_LENGTH = 8

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

# Numeric field validation
def validate_quantity(value, unit_type='unit'):
    """Validate quantity for unit or KG."""
    try:
        val = float(value)
        if unit_type == 'kg':
            if val < QUANTITY_MIN_KG:
                return False, f"Minimum quantity is {QUANTITY_MIN_KG}"
            if val > QUANTITY_MAX:
                return False, f"Maximum quantity is {QUANTITY_MAX}"
            return True, ""
        else:
            if not val.is_integer():
                return False, "Quantity must be an integer"
            if val < QUANTITY_MIN_UNIT:
                return False, f"Minimum quantity is {QUANTITY_MIN_UNIT}"
            if val > QUANTITY_MAX:
                return False, f"Maximum quantity is {QUANTITY_MAX}"
            return True, ""
    except (ValueError, TypeError):
        return False, "Quantity must be a number"

def validate_unit_price(value):
    try:
        val = float(value)
        if val < UNIT_PRICE_MIN:
            return False, f"Minimum unit price is {UNIT_PRICE_MIN}"
        if val > UNIT_PRICE_MAX:
            return False, f"Maximum unit price is {UNIT_PRICE_MAX}"
        return True, ""
    except (ValueError, TypeError):
        return False, "Unit price must be a number"

def validate_total_price(value):
    try:
        val = float(value)
        if val < TOTAL_PRICE_MIN:
            return False, f"Minimum total price is {TOTAL_PRICE_MIN}"
        if val > TOTAL_PRICE_MAX:
            return False, f"Maximum total price is {TOTAL_PRICE_MAX}"
        return True, ""
    except (ValueError, TypeError):
        return False, "Total price must be a number"

def validate_grand_total(value):
    try:
        val = float(value)
        if val < GRAND_TOTAL_MIN:
            return False, f"Minimum grand total is {GRAND_TOTAL_MIN}"
        if val > GRAND_TOTAL_MAX:
            return False, f"Maximum grand total is {GRAND_TOTAL_MAX}"
        return True, ""
    except (ValueError, TypeError):
        return False, "Grand total must be a number"

# String field validation
def validate_string(value):
    if not isinstance(value, str):
        return False, "Value must be a string"
    length = len(value.strip())
    if length == 0:
        return False, "Field cannot be empty"
    if length > STRING_MAX_LENGTH:
        return False, f"Maximum length is {STRING_MAX_LENGTH} characters"
    return True, ""

# Password validation
def validate_password(value):
    if not isinstance(value, str):
        return False, "Password must be a string"
    if len(value) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
    return True, ""

# Email validation
def validate_email(value):
    if not isinstance(value, str):
        return False, "Email must be a string"
    if not EMAIL_REGEX.match(value):
        return False, "Invalid email format"
    return True, ""

# Mandatory field check (for dialog action)
def is_mandatory(value):
    if value is None or str(value).strip() == '':
        return False, "Field is mandatory"
    return True, ""

# Date/time validation (for reports)
def validate_date_range(from_date, to_date):
    if from_date > to_date:
        return False, 'From date cannot be after To date'
    return True, ''

# Database existence check (stub, to be implemented)
def exists_in_database(value, db_lookup_func):
    """Check if value exists in database using provided lookup function."""
    if not db_lookup_func(value):
        return False, "Value does not exist in database"
    return True, ""

def exists_in_memory_cache(value, cache_lookup_func):
    """Check if value exists in an in-memory cache using provided lookup function."""
    if not cache_lookup_func(value):
        return False, "Value does not exist in memory cache"
    return True, ""

def validate_table_quantity(value):
    """Quantity in table cells must not be empty or zero. Returns (is_valid, error_message)."""
    try:
        val = float(value)
        if val < 1:
            return False, "Minimum qty is 1, delete row if you don't want item."
        return True, ""
    except (ValueError, TypeError):
        return False, "Minimum qty is 1, delete row if you don't want item."

# Error propagation (to be handled in UI integration)
# Functions here return True/False; error messages should be handled by the caller.

# Add more validation functions as needed for integration.


# --- Product / inventory specific validation (optional helpers) ---

PRODUCT_CODE_MIN_LEN = 4
PRODUCT_CODE_MAX_LEN = 30

def validate_product_code(value, digits_only=True,
                          min_len=PRODUCT_CODE_MIN_LEN,
                          max_len=PRODUCT_CODE_MAX_LEN):
    """
    Validate a product code string.
    Returns (is_valid, error_message).
    """
    if value is None:
        return False, "Product code is required"
    s = str(value).strip()
    if not s:
        return False, "Product code is required"
    if len(s) < min_len:
        return False, f"Product code must be at least {min_len} characters"
    if len(s) > max_len:
        return False, f"Product code must be at most {max_len} characters"
    if digits_only and not s.isdigit():
        return False, "Product code must contain digits only"
    return True, ""

def validate_cost_price(value, min_val=0.0, max_val=UNIT_PRICE_MAX):
    """
    Validate cost price (allow 0). Returns (is_valid, error_message).
    """
    if value is None or str(value).strip() == "":
        return True, ""  # optional field
    try:
        val = float(value)
        if val < min_val:
            return False, f"Minimum cost price is {min_val}"
        if val > max_val:
            return False, f"Maximum cost price is {max_val}"
        return True, ""
    except (ValueError, TypeError):
        return False, "Cost price must be a number"

def validate_selling_price(value, min_val=UNIT_PRICE_MIN, max_val=UNIT_PRICE_MAX):
    """
    Validate selling price. Returns (is_valid, error_message).
    """
    return validate_unit_price(value, min_val=min_val, max_val=max_val)
