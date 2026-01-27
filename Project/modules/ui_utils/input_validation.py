"""Centralized validators. All functions return (ok, err)."""

from config import (
	PRODUCT_CODE_MIN_LEN,
	PRODUCT_CODE_MAX_LEN,
	QUANTITY_MIN_KG,
	QUANTITY_MAX_KG,
	QUANTITY_MIN_UNIT,
	QUANTITY_MAX_UNIT,
	UNIT_PRICE_MIN,
	UNIT_PRICE_MAX,
	TOTAL_PRICE_MIN,
	TOTAL_PRICE_MAX,
	GRAND_TOTAL_MIN,
	GRAND_TOTAL_MAX,
	STRING_MAX_LENGTH,
	PASSWORD_MIN_LENGTH,
	EMAIL_REGEX,
	ALPHANUMERIC_REGEX,
)

def validate_quantity(value, unit_type='unit'):
    if value is None or str(value).strip() == "":
        return False, "Quantity is required"
    try:
        val = float(value)
        if unit_type.lower() == 'kg':
            if val < QUANTITY_MIN_KG:
                return False, f"Min weight is {int(QUANTITY_MIN_KG*1000)}g"
            if val > QUANTITY_MAX_KG:
                return False, f"Max weight is {QUANTITY_MAX_KG}kg"
            return True, ""
        else:
            if not val.is_integer():
                return False, "Quantity must be an integer"
            if val < QUANTITY_MIN_UNIT:
                return False, f"Minimum is {QUANTITY_MIN_UNIT}"
            if val > QUANTITY_MAX_UNIT:
                return False, f"Maximum is {QUANTITY_MAX_UNIT}"
            return True, ""
    except (ValueError, TypeError):
        return False, "Quantity must be a number"


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


def validate_table_quantity(value):
	return validate_quantity(value, unit_type='unit')


def validate_string(value):
	if not isinstance(value, str):
		return False, "Value must be a string"
	length = len(value.strip())
	if length == 0:
		return False, "Field cannot be empty"
	if length > STRING_MAX_LENGTH:
		return False, f"Maximum length is {STRING_MAX_LENGTH} characters"
	return True, ""


def validate_product_name(value):
    ok, err = validate_string(value)
    if not ok:
        return ok, err
    
    s = str(value).strip()
    if not any(c.isalpha() for c in s):
        return False, "Name must contain at least one letter (A-Z)"
        
    return True, ""

def validate_product_name_for_add(value, name_exists_func):

    ok, err = validate_product_name(value)
    if not ok:
        return False, err
    
    name = str(value).strip()
    if name_exists_func and name_exists_func(name):
        return False, "Product name already exists"
        
    return True, ""

def validate_supplier(value):
	if value is None:
		return True, ""
	s = str(value).strip()
	if not s:
		return True, ""
	if not ALPHANUMERIC_REGEX.match(s):
		return False, "Supplier must be alphanumeric"
	if len(s) > STRING_MAX_LENGTH:
		return False, f"Supplier must be at most {STRING_MAX_LENGTH} characters"
	return True, ""


def validate_category(value):
	if value is None:
		return True, ""
	s = str(value).strip()
	if not s:
		return True, ""
	if len(s) > STRING_MAX_LENGTH:
		return False, f"Category must be at most {STRING_MAX_LENGTH} characters"
	return True, ""


def validate_unit(value):
	if value is None:
		return False, "Unit is required"
	s = str(value).strip()
	if not s:
		return False, "Unit is required"
	if s.lower() == "select unit":
		return False, "Unit must be selected"
	return True, ""

#--- 1. selling price/ cost price start ---
def validate_unit_price(value, min_val=UNIT_PRICE_MIN, max_val=UNIT_PRICE_MAX, price_type="Price"):
    
    try:
        val = float(value)
        # Ensure constants are floats to avoid comparison errors
        f_min = float(min_val)
        f_max = float(max_val)

        if val < f_min:
            return False, f"Minimum {price_type.lower()} is {f_min}"
        if val > f_max:
            return False, f"Maximum {price_type.lower()} is {f_max}"
        return True, ""
    except (ValueError, TypeError):
        return False, f"{price_type} must be a number"
	
def validate_selling_price(value, price_type="Selling price"):
    if value is None or str(value).strip() == "":
        return False, f"{price_type} is required"
    return validate_unit_price(value, price_type=price_type)

def validate_cost_price(value, price_type="Cost price"):
    if value is None or str(value).strip() == "":
        return True, ""
    # If not empty, use the same numeric logic
    return validate_unit_price(value, price_type=price_type)

#--- 1. selling price/ cost price end ---
	
def validate_password(value):
	if not isinstance(value, str):
		return False, "Password must be a string"
	if len(value) < PASSWORD_MIN_LENGTH:
		return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
	return True, ""


def validate_email(value):
	if not isinstance(value, str):
		return False, "Email must be a string"
	if not EMAIL_REGEX.match(value):
		return False, "Invalid email format"
	return True, ""


def validate_current_email(value, current_email: str):
	if value is None:
		return False, "Email is required"
	entered = str(value).strip()
	if not entered:
		return False, "Email is required"
	if entered != (current_email or "").strip():
		return False, "Email does not match"
	return True, ""


def validate_current_password(value, current_password: str):
	if value is None:
		return False, "Password is required"
	entered = str(value)
	if entered != (current_password or ""):
		return False, "Password does not match"
	return True, ""


def is_mandatory(value):
	if value is None or str(value).strip() == '':
		return False, "Field is mandatory"
	return True, ""


def validate_required_fields(fields):
	for item in fields or []:
		try:
			label, value = item
		except Exception:
			return False, "Invalid required-fields specification"
		if value is None or str(value).strip() == "":
			return False, f"{label} is required"
	return True, ""


def validate_date_range(from_date, to_date):
	if from_date > to_date:
		return False, 'From date cannot be after To date'
	return True, ''


def exists_in_database(value, db_lookup_func):
	if not db_lookup_func(value):
		return False, "Value does not exist in database"
	return True, ""


def exists_in_memory_cache(value, cache_lookup_func):
	if not cache_lookup_func(value):
		return False, "Value does not exist in memory cache"
	return True, ""

# 2. product code ----------
def validate_product_code_format(value, digits_only=False,
							min_len=PRODUCT_CODE_MIN_LEN,
							max_len=PRODUCT_CODE_MAX_LEN):
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

def product_code_exists(code):
    """
    Shared utility: Checks if a code exists in the memory cache.
    Standardizes the input to UPPERCASE before checking.
    """
    from modules.ui_utils.canonicalization import canonicalize_product_code
    from modules.db_operation.product_cache import PRODUCT_CACHE
    
    target = canonicalize_product_code(code)
    return target in PRODUCT_CACHE


def is_reserved_vegetable_code(code: str) -> bool:
    """
    Checks if a product code falls within the reserved vegetable range (VEG1-VEG16).
    This is used to prevent editing of vegetable items within the standard Product Menu.
    """
    if not code:
        return False
    
    s = str(code).strip().upper()
    # Check if starts with 'VEG' and has a numeric suffix
    if s.startswith('VEG') and len(s) >= 4:
        try:
            # Extract digits after 'VEG'
            suffix = s[3:]
            if suffix.isdigit():
                num = int(suffix)
                return 1 <= num <= 16
        except (ValueError, TypeError):
            return False
    return False

# 2. product code end ----------
