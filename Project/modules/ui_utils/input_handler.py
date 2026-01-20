from __future__ import annotations
from PyQt5.QtWidgets import QCompleter, QLineEdit, QComboBox, QLabel
from PyQt5.QtCore import Qt
from modules.ui_utils import input_validation, ui_feedback

# =========================================================
# SECTION 1: INTERNAL HELPERS
# =========================================================

def _raise_if_invalid(result):
    """Helper to raise ValueError on validation failure."""
    ok, err = result if isinstance(result, (list, tuple)) else (result, None)
    if not ok:
        raise ValueError(err or "Invalid input")
    return True

# =========================================================
# SECTION 2: PURE GETTERS (EXTRACT + VALIDATE)
# These are used by 'OK' buttons to grab final clean data.
# =========================================================

def handle_product_name_input(line_edit: QLineEdit) -> str:
    name = line_edit.text().strip()
    _raise_if_invalid(input_validation.validate_product_name(name))
    return name

def handle_quantity_input(line_edit: QLineEdit, unit_type: str = 'unit') -> float:
    text = line_edit.text().strip()
    _raise_if_invalid(input_validation.validate_quantity(text, unit_type=unit_type))
    return float(text)

def handle_price_input(line_edit: QLineEdit, price_type: str = "price") -> float:
    text = line_edit.text().strip()
    _raise_if_invalid(input_validation.validate_price(text, price_type))
    return float(text)

def handle_email_input(line_edit: QLineEdit) -> str:
    email = line_edit.text().strip()
    _raise_if_invalid(input_validation.validate_email(email))
    return email

def handle_password_input(line_edit: QLineEdit) -> str:
    password = line_edit.text()
    _raise_if_invalid(input_validation.validate_password(password))
    return password

def handle_supplier_input(line_edit: QLineEdit) -> str:
    supplier = line_edit.text().strip()
    _raise_if_invalid(input_validation.validate_supplier(supplier))
    return supplier

def handle_unit_input_combo(combo_box: QComboBox) -> str:
    unit = combo_box.currentText().strip()
    _raise_if_invalid(input_validation.validate_unit(unit))
    return unit

def handle_category_input_combo(combo_box: QComboBox) -> str:
    category = combo_box.currentText().strip()
    _raise_if_invalid(input_validation.validate_category(category))
    return category

def handle_veg_choose_combo(combo_box: QComboBox) -> str:
    """Returns selected vegetable slot (no strict validation)."""
    return combo_box.currentText().strip()

def handle_greeting_combo(combo_box: QComboBox) -> str:
    """Returns selected greeting (no strict validation)."""
    return combo_box.currentText().strip()

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

    # 1. Search by Code
    if source_type == 'code':
        if val_norm in PRODUCT_CACHE:
            rec = PRODUCT_CACHE[val_norm]
            return {
                'code': val_norm,
                'name': rec[0],
                'price': rec[1],
                'unit': rec[2]
            }
            
    # 2. Search by Name
    else:
        search_name = value.strip().lower()
        for code, rec in PRODUCT_CACHE.items():
            if rec[0] and rec[0].strip().lower() == search_name:
                return {
                    'code': code,
                    'name': rec[0],
                    'price': rec[1],
                    'unit': rec[2]
                }
    
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

def setup_name_search_lineedit(line_edit: QLineEdit, product_names: list, *, on_selected=None):
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

        # Manual exact typing + focus-out
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