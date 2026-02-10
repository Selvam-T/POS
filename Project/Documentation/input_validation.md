# Input Validation

This document describes the shared validation rules used by POS dialogs/frames.

## Contract
- All validators in `modules/ui_utils/input_validation.py` return `(True, "")` if valid, or `(False, "error message")` if invalid.
- “Mandatory fields” (which fields are required) is a dialog/controller responsibility.
- UI error display is handled by the caller (QLabel/status bar/etc.).

Import pattern:
```python
from modules.ui_utils import input_validation
```

## Core Rules (Constants)
- Quantity
  - KG: min `0.01`
  - Unit: min `1` and must be integer
  - Max `9999`
- Unit/Selling price: min `0.1`, max `5000`
- String fields: max length `15`
- Password: min length `8`

## Key Validators (by purpose)

### Required fields (dialog-level)
- `validate_required_fields(fields)`
  - Pass only the fields that are required for that dialog, e.g. `[("Product Code", code), ("Selling Price", price)]`.
  - Fields that are defaulted/auto-filled should not be included.

### Product code
- `validate_product_code_format(code, digits_only=False, min_len=4, max_len=30)`
  - Format-only validation (required/non-empty + length, optional digits-only).
  - Use anywhere the user can type/scan a product code (ADD/REMOVE/UPDATE/manual entry).

Flow validators (format + existence rule):
- `validate_product_code_for_add(code, code_exists_func, ...)` → must be valid format AND must **not** already exist.
- `validate_product_code_for_lookup(code, code_exists_func, ...)` → must be valid format AND must **exist**.

### Product name
- `validate_product_name(name)` → required, max length.

### Quantity
- `validate_quantity(value, unit_type='unit')` → required, numeric, min/max, and integer-only for `unit`.
- `validate_table_quantity(value)` → compatibility alias that delegates to `validate_quantity`.

### Prices
- `validate_unit_price(value, min_val=UNIT_PRICE_MIN, max_val=UNIT_PRICE_MAX)` → numeric + min/max.
- `validate_selling_price(value, price_type="price")` → mandatory wrapper around `validate_unit_price`.
- `validate_selling_price(value, ...)` → uses `validate_unit_price` (range enforced).
- `validate_cost_price(value, ...)` → optional (empty allowed) else numeric + range.
<!-- Total/grand total validators were removed because totals are derived from the table rows and are not validated via shared helpers. -->


### Unit / Supplier / Category
- `validate_unit(value)`
  - Placeholder `"Select Unit"` is invalid.
  - If a dialog always sets a valid default unit, it may skip calling this (but validation is cheap safety).
- `validate_supplier(value)`
  - Optional; if provided must be alphanumeric (spaces allowed) and within max length.
- `validate_category(value)`
  - Optional (placeholder/empty allowed); max length enforced if provided.

#### Why validate category if it's a dropdown?
Even though category is usually selected from a non-editable dropdown (QComboBox), validation is still enforced for these reasons:

1. **The "Editable" Safety Net**
   - In PyQt, it's easy to accidentally set the ComboBox to editable in the .ui file. If that happens, users could type arbitrarily long strings. Without validation, this could crash the database (e.g., exceeding VARCHAR limits).
2. **Consistency in the "OK" Handler**
   - The input extraction/validation pattern (Extract → Validate → Return) is consistent for all fields. This avoids special-case logic for categories in dialog handlers.
3. **Database Integrity (The final gate)**
   - The validator acts as a contract between UI and DB, ensuring the string length is always safe, regardless of UI source.

**When could you remove it?**
If you are 100% certain the ComboBox will never be editable and your PRODUCT_CATEGORIES list is pre-validated, you could skip validation. However, keeping it is considered defensive programming: it costs almost nothing and prevents future UI changes from breaking your database.

### Email / Password
- “New” format validators:
  - `validate_email(value)`
  - `validate_password(value)`
- “Current” match validators (for change-email/password flows):
  - `validate_current_email(value, current_email)`
  - `validate_current_password(value, current_password)`

### Misc
- `validate_date_range(from_date, to_date)`
- `exists_in_database(value, db_lookup_func)`
- `exists_in_memory_cache(value, cache_lookup_func)`

## Dialog Notes (high-level)
- Manual entry name search (QLineEdit + QCompleter): treat the field value as a normal string; it may contain a placeholder (ignored) or a selected product name. Required-field logic should be checked at OK-time.
- Product Menu:
  - ADD: product code is a new identifier → validate format + must-not-exist.
  - REMOVE/UPDATE: product code is a lookup key → validate format + must-exist.

---
Update this document when new dialogs or validation rules are added.
