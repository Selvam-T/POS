from __future__ import annotations
from PyQt5.QtWidgets import QCompleter, QLineEdit, QComboBox, QLabel
from PyQt5.QtCore import Qt
from modules.ui_utils import input_validation, ui_feedback
from modules.ui_utils.canonicalization import (
    canonicalize_product_code,
    canonicalize_title_text,
)

# =========================================================
# SECTION 1: INTERNAL HELPERS
# =========================================================

def _raise_if_invalid(result):
    """Helper to raise ValueError on validation failure."""
    ok, err = result if isinstance(result, (list, tuple)) else (result, None)
    if not ok:
        raise ValueError(err or "Invalid input")
    return True


def _to_camel_case(text: str) -> str:
    """Backward-compatible alias."""
    return canonicalize_title_text(text)

# =========================================================
# SECTION 2: PURE GETTERS (EXTRACT + VALIDATE)
# These are used by 'OK' buttons to grab final clean data.
# =========================================================

def handle_product_code_input(line_edit: QLineEdit) -> str:
    code = canonicalize_product_code(line_edit.text())
    _raise_if_invalid(input_validation.validate_product_code_format(code))
    return code


def handle_product_name_input(line_edit: QLineEdit, exclude_code: str = None) -> str:
    name = canonicalize_title_text(line_edit.text())
    #_raise_if_invalid(input_validation.validate_product_name(name))
    _raise_if_invalid(input_validation.validate_product_name(name, exclude_code=exclude_code))
    return name

def handle_selling_price(line_edit: QLineEdit, price_type: str = "price") -> float:
    text = line_edit.text().strip()
    _raise_if_invalid(input_validation.validate_selling_price(text, price_type))
    return float(text)

def handle_cost_price(line_edit: QLineEdit, price_type: str = "price") -> float | None:

    text = (line_edit.text() or '').strip()
    _raise_if_invalid(input_validation.validate_cost_price(text, price_type))
    if not text:
        return None
    return float(text)

def handle_supplier_input(line_edit: QLineEdit) -> str:
    supplier = canonicalize_title_text(line_edit.text())
    _raise_if_invalid(input_validation.validate_supplier(supplier))
    return supplier

def handle_customer_input(line_edit: QLineEdit) -> str:
    customer = canonicalize_title_text(line_edit.text())
    _raise_if_invalid(input_validation.validate_customer(customer))
    return customer

def handle_note_input(line_edit: QLineEdit) -> str:
    note = canonicalize_title_text(line_edit.text())
    _raise_if_invalid(input_validation.validate_note(note))
    return note

def handle_customer_input(line_edit: QLineEdit) -> str:
    customer = canonicalize_title_text(line_edit.text())
    _raise_if_invalid(input_validation.validate_customer(customer))
    return customer

def handle_note_input(line_edit: QLineEdit) -> str:
    note = canonicalize_title_text(line_edit.text())
    _raise_if_invalid(input_validation.validate_note(note))
    return note

def handle_unit_input_combo(combo_box: QComboBox) -> str:
    unit = combo_box.currentText().strip()
    _raise_if_invalid(input_validation.validate_unit(unit))
    return unit

def handle_category_input_combo(combo_box: QComboBox) -> str:
    category = combo_box.currentText().strip()
    _raise_if_invalid(input_validation.validate_category(category))
    return category


def handle_category_input_combo_default_other(combo_box: QComboBox, *, default: str = "") -> str:
    try:
        category = (combo_box.currentText() or '').strip()
    except Exception:
        category = ''
    
    if not category:
        return ""
        
    _raise_if_invalid(input_validation.validate_category(category))
    return category

def handle_quantity_input(line_edit: QLineEdit, unit_type: str = 'unit') -> float:
    text = line_edit.text().strip()
    _raise_if_invalid(input_validation.validate_quantity(text, unit_type=unit_type))
    return float(text)

def handle_currency_input(line_edit: QLineEdit, asset_type: str = 'Amount') -> float:
    text = line_edit.text().strip()
    _raise_if_invalid(input_validation.validate_currency(text, asset_type=asset_type))
    return float(text)

def handle_voucher_input(line_edit: QLineEdit) -> int:
    text = (line_edit.text() or '').strip()
    _raise_if_invalid(input_validation.validate_voucher_amount(text))
    return int(text) if text else 0

def handle_veg_choose_combo(combo_box: QComboBox) -> str:
    """Returns selected vegetable slot (no strict validation)."""
    return combo_box.currentText().strip()

def handle_greeting_combo(combo_box: QComboBox) -> str:
    """Returns selected greeting (no strict validation)."""
    return combo_box.currentText().strip()

def handle_email_input(line_edit: QLineEdit) -> str:
    email = line_edit.text().strip()
    _raise_if_invalid(input_validation.validate_email(email))
    return email

def handle_password_input(line_edit: QLineEdit) -> str:
    password = line_edit.text()
    _raise_if_invalid(input_validation.validate_password(password))
    return password

# =========================================================
# SECTION 3: SEARCH ENGINES (COORDINATOR SUPPORT)
# These are used by the FieldCoordinator to fetch data.
# =========================================================

def get_coordinator_lookup(value: str, source_type: str = 'code') -> dict | None:
    """
    Standardized lookup engine for the FieldCoordinator.
    Maps Cache/DB records into a clean dictionary.
    """
    from modules.db_operation.product_cache import PRODUCT_CACHE, _norm, load_product_cache

    # Ensure cache is populated (one-time DB hit only if cache is empty).
    if not PRODUCT_CACHE:
        try:
            load_product_cache()
        except Exception:
            return None
    
    val_norm = _norm(value)
    if not val_norm:
        return None

    # Helper to map the cache record to a clean dictionary
    def _map(code, rec):
        return {
            'code': code,
            'name': rec[0],
            'price': rec[1],
            'unit': rec[2] if rec[2] else "", # Ensure empty if null/empty in DB
            'cost': rec[3] if len(rec) > 3 else "" # Added support for Cost Price
        }
    
    # 1. Search by Code
    if source_type == 'code':
        # Gateway B: Standardize the input before searching
        key = canonicalize_product_code(value) 
        if key in PRODUCT_CACHE:
            rec = PRODUCT_CACHE[key]
            return {'code': key, 'name': rec[0], 'price': rec[1], 'unit': rec[2]}
            
    # 2. Search by Name
    else:
        # Gateway B: Standardize the input before searching
        target_name = canonicalize_title_text(value)
        for code, rec in PRODUCT_CACHE.items():
            # Standardized Target vs Standardized Cache Item
            if rec[0] == target_name:
                return {'code': code, 'name': rec[0], 'price': rec[1], 'unit': rec[2]}
    
    return None

def product_name_search_suggestions(search_text: str) -> list:
    """Returns list of product names for QCompleter."""
    from modules.db_operation.product_cache import PRODUCT_CACHE
    if not search_text:
        return []
    st = search_text.strip().lower()
    return [rec[0] for rec in PRODUCT_CACHE.values() if rec[0] and st in rec[0].lower()]

# =========================================================
# SECTION 4: UI HELPERS
# =========================================================

def setup_name_search_lineedit(
    line_edit: QLineEdit,
    product_names: list,
    *,
    on_selected=None,
    trigger_on_finish: bool = True,
):
    """Initializes QCompleter on a LineEdit.

    Args:
        line_edit: QLineEdit to attach the completer.
        product_names: list of names.
        on_selected: optional callback invoked when the user selects a completer
            option (or finishes editing). This is useful to trigger downstream
            mapping/sync logic (e.g., FieldCoordinator) because QCompleter sets
            text programmatically (textChanged) and does not emit textEdited.

            Supported call signatures:
              - on_selected(text: str, line_edit: QLineEdit)
              - on_selected(text: str)
              - on_selected()

    Returns:
        The QCompleter instance.
    """
    completer = QCompleter(product_names)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains)
    completer.setCompletionMode(QCompleter.PopupCompletion)
    line_edit.setCompleter(completer)

    if callable(on_selected):
        def _call(text: str = ""):
            try:
                on_selected(text, line_edit)
                return
            except TypeError:
                pass
            try:
                on_selected(text)
                return
            except TypeError:
                pass
            try:
                on_selected()
            except Exception:
                pass

        # Completer selection
        try:
            completer.activated[str].connect(lambda text: _call(text))
        except Exception:
            try:
                completer.activated.connect(lambda _=None: _call(line_edit.text() or ""))
            except Exception:
                pass

        # Manual exact typing + focus-out (optional; some dialogs want explicit commit only)
        if trigger_on_finish:
            try:
                line_edit.editingFinished.connect(lambda: _call(line_edit.text() or ""))
            except Exception:
                pass

    return completer

def search_combo_box(combo_box: QComboBox, search_text: str) -> list:
    """Filters QComboBox items by text."""
    st = search_text.strip().lower()
    return [combo_box.itemText(i) for i in range(combo_box.count()) 
            if st in combo_box.itemText(i).lower()]

def calculate_markup_widgets(sell_le, cost_le, markup_le) -> None:
    try:
        if not sell_le or not cost_le or not markup_le:
            return

        sell_txt = sell_le.text().strip()
        cost_txt = cost_le.text().strip()
        
        # 1. BOTH EMPTY (Startup/Locked state) -> Clear the widget
        if not sell_txt and not cost_txt:
            markup_le.setText("")
            return

        # 2. EITHER MISSING (User is typing or data is partial) -> Display NA
        if not sell_txt or not cost_txt:
            markup_le.setText("NA")
            return

        # 3. BOTH PRESENT -> Calculate percentage
        sell, cost = float(sell_txt), float(cost_txt)
        if cost > 0:
            markup_le.setText(f"{((sell - cost) / cost * 100):.1f}%")
        else:
            markup_le.setText("NA")
            
    except Exception:
        markup_le.setText("") # Graceful fail for invalid numeric input

def wire_markup_logic(sell_le, cost_le, markup_le) -> None:
    """Standardizes signal connections for markup."""
    def _recalc():
        calculate_markup_widgets(sell_le, cost_le, markup_le)
    
    # Connect to changes
    sell_le.textChanged.connect(_recalc)
    cost_le.textChanged.connect(_recalc)
    _recalc() # Initial run