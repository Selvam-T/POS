"""Centralized validators. All functions return (ok, err)."""

import re

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
ALPHANUMERIC_REGEX = re.compile(r"^[A-Za-z0-9 ]+$")


def validate_quantity(value, unit_type='unit'):
	if value is None or str(value).strip() == "":
		return False, "Quantity is required"
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


def validate_unit_price(value, min_val=UNIT_PRICE_MIN, max_val=UNIT_PRICE_MAX):
	try:
		val = float(value)
		if val < min_val:
			return False, f"Minimum unit price is {min_val}"
		if val > max_val:
			return False, f"Maximum unit price is {max_val}"
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
	if value is None:
		return False, "Product name is required"
	s = str(value).strip()
	if not s:
		return False, "Product name is required"
	if len(s) > STRING_MAX_LENGTH:
		return False, f"Product name must be at most {STRING_MAX_LENGTH} characters"
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


def validate_price(value, price_type: str = "price"):
	if value is None or str(value).strip() == "":
		return False, f"{price_type} is required"
	return validate_unit_price(value)


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


PRODUCT_CODE_MIN_LEN = 4
PRODUCT_CODE_MAX_LEN = 30


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


def validate_product_code_for_add(value, code_exists_func,
							 digits_only=False,
							 min_len=PRODUCT_CODE_MIN_LEN,
							 max_len=PRODUCT_CODE_MAX_LEN):
	ok, err = validate_product_code_format(value, digits_only=digits_only, min_len=min_len, max_len=max_len)
	if not ok:
		return False, err
	code = str(value).strip()
	if code_exists_func and code_exists_func(code):
		return False, "Product code already exists"
	return True, ""


def validate_product_code_for_lookup(value, code_exists_func,
							 digits_only=False,
							 min_len=PRODUCT_CODE_MIN_LEN,
							 max_len=PRODUCT_CODE_MAX_LEN):
	ok, err = validate_product_code_format(value, digits_only=digits_only, min_len=min_len, max_len=max_len)
	if not ok:
		return False, err
	code = str(value).strip()
	if code_exists_func and not code_exists_func(code):
		return False, "Product not found"
	return True, ""


def validate_cost_price(value, min_val=0.0, max_val=UNIT_PRICE_MAX):
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
	return validate_unit_price(value, min_val=min_val, max_val=max_val)
