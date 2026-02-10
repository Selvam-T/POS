"""Centralized validators. All functions return (ok, err)."""

from config import (
	QUANTITY_MIN_KG,
	QUANTITY_MAX_KG,
	QUANTITY_MIN_UNIT,
	QUANTITY_MAX_UNIT,
	UNIT_PRICE_MIN,
	UNIT_PRICE_MAX,
	PAID_MIN,
	PAID_MAX,
	STRING_MAX_LENGTH,
	PASSWORD_MIN_LENGTH,
	EMAIL_REGEX,
	ALPHANUMERIC_REGEX,
	STRING_CONFIG,
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

# --- Generalized string validator using STRING_CONFIG
def _validate_config_string(value, field_key, display_name):
    """Internal helper to enforce STRING_CONFIG rules."""
    config = STRING_CONFIG.get(field_key)
    s = str(value or "").strip()
    
    # 1. Required Check
    if not s:
        if config['required']:
            return False, f"{display_name} is required"
        return True, "" # Valid if optional and empty

    # 2. Length Checks
    if len(s) < config['min_len']:
        return False, f"{display_name} must be at least {config['min_len']} characters"
    if len(s) > config['max_len']:
        return False, f"{display_name} must be at most {config['max_len']} characters"
        
    return True, ""

# --- end of _validate_config_string

# 1. product code ----------

def validate_product_code_format(value):
    # 1. Enforce Config (Required, Min 4, Max 14)
    ok, err = _validate_config_string(value, 'product_code', "Product code")
    if not ok: return False, err
    
    # 2. Specific Rule: Product codes are usually Alphanumeric
    if not ALPHANUMERIC_REGEX.match(str(value).strip()):
        return False, "Product code contains invalid characters"
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

# 1. product code end ----------

# 2. product name ----------

def product_name_exists(name: str, exclude_code: str = None) -> bool:
    """
    Utility: Checks if a name is already taken in the cache.
    """
    from modules.ui_utils.canonicalization import canonicalize_title_text
    from modules.db_operation.product_cache import PRODUCT_CACHE
    
    target = canonicalize_title_text(name)
    
    for code, rec in (PRODUCT_CACHE or {}).items():
        if rec[0] == target:
            # If we are in UPDATE mode, don't count the current product as a duplicate
            if exclude_code and code == exclude_code:
                continue
            return True
    return False

def validate_product_name(value: str, exclude_code: str = None):
    ok, err = _validate_config_string(value, 'product_name', "Product name")
    if not ok:
        return False, err
    
    # Requirement: Must contain at least one letter (A-Z)
    if not any(c.isalpha() for c in str(value)):
        return False, "Product name must contain at least one letter"
	
    if product_name_exists(value, exclude_code=exclude_code):
        return False, "Product name already exists"
	
    return True, ""

# 2. product name end ----------

#--- 3. selling price/ cost price start ---
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

#--- 3. selling price/ cost price end ---

#--- 4. category start ---

def validate_category(value):
    # Standard check: Required, Min 4, Max 25 (handles combo placeholder as empty)
    return _validate_config_string(value, 'category', "Category")

#--- 4. category end ---

#--- 5. unit start ---

def validate_unit(value):
	if value is None:
		return False, "Unit is required"
	s = str(value).strip()
	if not s:
		return False, "Unit is required"
	if s.lower() == "select unit":
		return False, "Unit must be selected"
	return True, ""

#--- 5. unit end ---

#--- 6. supplier start ---

def validate_supplier(value):
    ok, err = _validate_config_string(value, 'supplier', "Supplier")
    if not ok:
        return False, err
    
    # Requirement: If provided, must match Alphanumeric Regex
    s = str(value or "").strip()
    if s and not ALPHANUMERIC_REGEX.match(s):
        return False, "Only Alphanumeric characters are allowed"
    return True, ""	
#--- 6. supplier end ---

#--- 7. tender amount start ---
def validate_tender_amount(value, price_type="Tender amount"):
    if value is None or str(value).strip() == "":
        return True, ""
    # If not empty, use the same numeric logic
    return validate_unit_price(value, min_val=PAID_MIN, max_val=PAID_MAX, price_type=price_type)
#--- 7. tender amount end ---