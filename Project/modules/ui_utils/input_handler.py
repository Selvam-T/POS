from __future__ import annotations

from PyQt5.QtWidgets import QCompleter, QLineEdit, QLabel, QComboBox
# Helper to raise error if validation fails
def _raise_if_invalid(result):
    ok, err = result if isinstance(result, (list, tuple)) else (result, None)
    if not ok:
        raise ValueError(err or "Invalid input")
    return True
from PyQt5.QtCore import Qt
from modules.ui_utils import ui_feedback
from modules.ui_utils import input_validation

def handle_product_name_edit(
    name_line: QLineEdit,
    code_line: QLineEdit,
    unit_line: QLineEdit,
    source,
    error_label: QLabel = None,
    source_type: str = 'db',
    name_override: str = None
):
    """
    Handles product name input: maps to code/unit, validates, updates fields, shows error if not found.
    Args:
        name_line: QLineEdit for product name
        code_line: QLineEdit for product code (to update)
        unit_line: QLineEdit for unit (to update)
        source: PRODUCT_CACHE dict or db_lookup_func
        error_label: QLabel for error/status (optional)
        source_type: 'cache' or 'db'
        name_override: If provided, use this as the product name instead of reading from the widget
    """
    name = name_override if name_override is not None else name_line.text().strip()
    if source_type == 'cache':
        from modules.ui_utils.input_handler import map_product_fields_from_cache
        result = map_product_fields_from_cache(product_name=name, product_cache=source)
    elif source_type == 'db':
        from modules.ui_utils.input_handler import map_product_fields_from_db
        result = map_product_fields_from_db(product_name=name, db_lookup_func=source)
    else:
        raise ValueError('Invalid source_type for handle_product_name_edit')
    code = result['product_code'] if result else ''
    unit = ''
    if result:
        if 'record' in result and len(result['record']) > 2:
            unit = result['record'][2]
        else:
            unit = result.get('unit', 'Each')
    # Always update both fields
    if code_line is not None:
        code_line.setText(code)
    if unit_line is not None:
        unit_line.setText(unit)
    # Always set error label
    if error_label:
        from modules.ui_utils import ui_feedback
        if result:
            ui_feedback.set_status_label(error_label, "", ok=True)
        else:
            if name:
                ui_feedback.set_status_label(error_label, "Product name not found.", ok=False)
            else:
                ui_feedback.set_status_label(error_label, "", ok=True)
    return bool(result)

def handle_product_code_edit(
    code_line: QLineEdit,
    name_line: QLineEdit,
    unit_line: QLineEdit,
    source,
    error_label: QLabel = None,
    source_type: str = 'db'
):
    """
    Handles product code input: maps to name/unit, validates, updates fields, shows error if not found.
    Args:
        code_line: QLineEdit for product code
        name_line: QLineEdit for product name (to update)
        unit_line: QLineEdit for unit (to update)
        source: PRODUCT_CACHE dict or db_lookup_func
        error_label: QLabel for error/status (optional)
        source_type: 'cache' or 'db'
    """
    code = code_line.text().strip()
    if source_type == 'cache':
        from modules.ui_utils.input_handler import map_product_fields_from_cache
        result = map_product_fields_from_cache(product_code=code, product_cache=source)
    elif source_type == 'db':
        from modules.ui_utils.input_handler import map_product_fields_from_db
        result = map_product_fields_from_db(product_code=code, db_lookup_func=source)
    else:
        raise ValueError('Invalid source_type for handle_product_code_edit')
    name = result['product_name'] if result else ''
    unit = ''
    if result:
        if 'record' in result and len(result['record']) > 2:
            unit = result['record'][2]
        else:
            unit = result.get('unit', 'Each')
    # Always update both fields
    if name_line is not None:
        name_line.setText(name)
    if unit_line is not None:
        unit_line.setText(unit)
    # Always set error label
    if error_label:
        from modules.ui_utils import ui_feedback
        if result:
            ui_feedback.set_status_label(error_label, "", ok=True)
        else:
            if code:
                ui_feedback.set_status_label(error_label, "Product code not found.", ok=False)
            else:
                ui_feedback.set_status_label(error_label, "", ok=True)
    return bool(result)

from PyQt5.QtWidgets import QCompleter, QLineEdit, QLabel
from PyQt5.QtCore import Qt
from modules.ui_utils import ui_feedback

# Shared handler for QLineEdit+QCompleter product name search
def setup_name_search_lineedit(line_edit: QLineEdit, product_names: list, error_label: QLabel = None):
    """
    Sets up QCompleter for a QLineEdit to search product names, with validation and error feedback.
    Args:
        line_edit: QLineEdit widget for product name input
        product_names: List of product names for completion
        error_label: QLabel for error/status feedback (optional)
    """
    completer = QCompleter(product_names)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains)
    completer.setCompletionMode(QCompleter.PopupCompletion)
    line_edit.setCompleter(completer)
    line_edit.setReadOnly(False)
    line_edit.setEnabled(True)
    def validate_name():
        name = line_edit.text().strip()
        try:
            from modules.ui_utils import input_validation
            ok, err = input_validation.validate_product_name(name)
            if not ok:
                if error_label:
                    ui_feedback.set_status_label(error_label, err, ok=False)
                return False
            if error_label:
                ui_feedback.set_status_label(error_label, "", ok=True)
            return True
        except Exception as e:
            if error_label:
                ui_feedback.set_status_label(error_label, str(e), ok=False)
            return False
    line_edit.editingFinished.connect(validate_name)
    return completer

# Helper to map product name to product code using PRODUCT_CACHE
def get_product_code_by_name(product_name, product_cache):
    """
    Given a product name, return the corresponding product code from product_cache.
    Returns product code as string, or None if not found.
    """
    if not product_name or not product_cache:
        return None
    def handle_product_name_edit(
        name_line: QLineEdit,
        code_line: QLineEdit,
        unit_line: QLineEdit,
        source,
        error_label: QLabel = None,
        source_type: str = 'db',
        name_override: str = None
    ):
        """
        Handles product name input: maps to code/unit, validates, updates fields, shows error if not found.
        Args:
            name_line: QLineEdit for product name
            code_line: QLineEdit for product code (to update)
            unit_line: QLineEdit for unit (to update)
            source: PRODUCT_CACHE dict or db_lookup_func
            error_label: QLabel for error/status (optional)
            source_type: 'cache' or 'db'
            name_override: If provided, use this as the product name instead of reading from the widget
        """
        name = name_override if name_override is not None else name_line.text().strip()
        if source_type == 'cache':
            from modules.ui_utils.input_handler import map_product_fields_from_cache
            result = map_product_fields_from_cache(product_name=name, product_cache=source)
        elif source_type == 'db':
            from modules.ui_utils.input_handler import map_product_fields_from_db
            result = map_product_fields_from_db(product_name=name, db_lookup_func=source)
        else:
            raise ValueError('Invalid source_type for handle_product_name_edit')
        code = result['product_code'] if result else ''
        unit = ''
        if result:
            if 'record' in result and len(result['record']) > 2:
                unit = result['record'][2]
            else:
                unit = result.get('unit', 'Each')
        # Always update both fields
        if code_line is not None:
            code_line.setText(code)
        if unit_line is not None:
            unit_line.setText(unit)
        # Always set error label
        if error_label:
            from modules.ui_utils import ui_feedback
            if result:
                ui_feedback.set_status_label(error_label, "", ok=True)
            else:
                if name:
                    ui_feedback.set_status_label(error_label, "Product name not found.", ok=False)
                else:
                    ui_feedback.set_status_label(error_label, "", ok=True)
        return bool(result)

# Utility: search combo box for matches (fixes combo_box not defined error)
def search_combo_box(combo_box: QComboBox, search_text: str):
    search_text = search_text.strip().lower()
    matches = []
    for i in range(combo_box.count()):
        item_text = combo_box.itemText(i).lower()
        if search_text in item_text:
            matches.append(combo_box.itemText(i))
    return matches


def handle_product_name_input(line_edit: QLineEdit) -> str:
    """Validate and return product name from QLineEdit."""
    name = line_edit.text().strip()
    _raise_if_invalid(input_validation.validate_product_name(name))
    return name


def handle_quantity_input(line_edit: QLineEdit) -> float:
    """Validate and return quantity as float from QLineEdit."""
    text = line_edit.text().strip()
    _raise_if_invalid(input_validation.validate_quantity(text))
    return float(text)


def handle_email_input(line_edit: QLineEdit) -> str:
    """Validate and return email from QLineEdit."""
    email = line_edit.text().strip()
    _raise_if_invalid(input_validation.validate_email(email))
    return email


def handle_password_input(line_edit: QLineEdit) -> str:
    """Validate and return password from QLineEdit."""
    password = line_edit.text()
    _raise_if_invalid(input_validation.validate_password(password))
    return password


def handle_unit_input_combo(combo_box: QComboBox) -> str:
    """Validate and return selected unit from QComboBox."""
    unit = combo_box.currentText().strip()
    _raise_if_invalid(input_validation.validate_unit(unit))
    return unit


def handle_price_input(line_edit: QLineEdit, price_type: str = "price") -> float:
    """Validate and return price as float from QLineEdit."""
    text = line_edit.text().strip()
    _raise_if_invalid(input_validation.validate_price(text, price_type))
    return float(text)


def handle_supplier_input(line_edit: QLineEdit) -> str:
    """Validate and return supplier from QLineEdit (optional)."""
    supplier = line_edit.text().strip()
    _raise_if_invalid(input_validation.validate_supplier(supplier))
    return supplier


def handle_category_input_line(line_edit: QLineEdit) -> str:
    """Validate and return category from QLineEdit."""
    category = line_edit.text().strip()
    _raise_if_invalid(input_validation.validate_category(category))
    return category


def handle_category_input_combo(combo_box: QComboBox) -> str:
    """Validate and return selected category from QComboBox."""
    category = combo_box.currentText().strip()
    _raise_if_invalid(input_validation.validate_category(category))
    return category


def handle_veg_choose_combo(combo_box: QComboBox) -> str:
    """Return selected vegetable slot from QComboBox (no validation)."""
    return combo_box.currentText().strip()


def handle_greeting_combo(combo_box: QComboBox) -> str:
    """Return selected greeting from QComboBox (no validation)."""
    return combo_box.currentText().strip()


# Map product fields from PRODUCT_CACHE (for dialogs like manual_entry)
def map_product_fields_from_cache(product_code=None, product_name=None, product_cache=None):
    """
    Given a product_code or product_name, return the full product record from product_cache.
    Returns dict with keys: 'product_code', 'product_name', 'record' (or None if not found).
    """
    if product_cache is None:
        raise ValueError("product_cache is required")
    # Import _norm for normalization
    try:
        from modules.db_operation.database import _norm
    except ImportError:
        def _norm(x): return str(x).strip()
    # Case-insensitive, camel case lookup for product_code
    if product_code:
        norm_code = _norm(product_code)
        for code, rec in product_cache.items():
            if _norm(code) == norm_code:
                return {'product_code': code, 'product_name': rec[0], 'record': rec}
    # Case-insensitive, camel case lookup for product_name
    if product_name:
        norm_name = str(product_name).strip().lower()
        for code, rec in product_cache.items():
            if rec[0] and rec[0].strip().lower() == norm_name:
                return {'product_code': code, 'product_name': rec[0], 'record': rec}
    return None

# Map product fields from database (for dialogs needing full product info)
def map_product_fields_from_db(product_code=None, product_name=None, db_lookup_func=None):
    """
    Given a product_code or product_name, fetch the full product record from the database using db_lookup_func.
    db_lookup_func should accept product_code and return a dict or record with all required fields.
    Returns dict with all product fields, or None if not found.
    """
    if db_lookup_func is None:
        raise ValueError("db_lookup_func is required")
    code = None
    if product_code:
        code = str(product_code).strip()
    elif product_name:
        # You may want to use PRODUCT_CACHE or a DB query to get code from name
        raise NotImplementedError("Mapping product name to code from DB not implemented.")
    if code:
        return db_lookup_func(code)
    return None

def product_name_search_suggestions(search_text, product_cache):
    """
    Return a list of product names from product_cache containing the search_text (case-insensitive).
    """
    if not search_text:
        return []
    search_text = search_text.strip().lower()
    return [rec[0] for rec in product_cache.values() if rec[0] and search_text in rec[0].lower()]

# Robust handler for product name edit (mapping, validation, error feedback, updates code/unit fields)

# Dual-source handler for product name edit (cache or DB)
def handle_product_name_edit(
    name_line: QLineEdit,
    code_line: QLineEdit,
    unit_line: QLineEdit,
    source,
    error_label: QLabel = None,
    source_type: str = 'db',
    name_override: str = None
):
    """
    def handle_product_code_edit(code_line: QLineEdit, name_line: QLineEdit, unit_line: QLineEdit, source, error_label: QLabel = None, source_type: str = 'db'):
    Handles product name input: maps to code/unit, validates, updates fields, shows error if not found.
    Args:
        name_line: QLineEdit for product name
        code_line: QLineEdit for product code (to update)
        unit_line: QLineEdit for unit (to update)
        source: PRODUCT_CACHE dict or db_lookup_func
        error_label: QLabel for error/status (optional)
        source_type: 'cache' or 'db'
        name_override: If provided, use this as the product name instead of reading from the widget
    """
    name = name_override if name_override is not None else name_line.text().strip()
    if source_type == 'cache':
        from modules.ui_utils.input_handler import map_product_fields_from_cache
        result = map_product_fields_from_cache(product_name=name, product_cache=source)
    elif source_type == 'db':
        from modules.ui_utils.input_handler import map_product_fields_from_db
        result = map_product_fields_from_db(product_name=name, db_lookup_func=source)
    else:
        raise ValueError('Invalid source_type for handle_product_name_edit')
    code = result['product_code'] if result else ''
    unit = ''
    if result:
        if 'record' in result and len(result['record']) > 2:
            unit = result['record'][2]
        else:
            unit = result.get('unit', 'Each')
    # Always update both fields
    if code_line is not None:
        code_line.setText(code)
    if unit_line is not None:
        unit_line.setText(unit)
    # Always set error label
    if error_label:
        from modules.ui_utils import ui_feedback
        if result:
            ui_feedback.set_status_label(error_label, "", ok=True)
        else:
            if name:
                ui_feedback.set_status_label(error_label, "Product name not found.", ok=False)
            else:
                ui_feedback.set_status_label(error_label, "", ok=True)
    return bool(result)

# Dual-source handler for product code edit (cache or DB)
def handle_product_code_edit(code_line: QLineEdit, name_line: QLineEdit, unit_line: QLineEdit, source, error_label: QLabel = None, source_type: str = 'db'):
    """
    Handles product code input: maps to name/unit, validates, updates fields, shows error if not found.
    Args:
        code_line: QLineEdit for product code
        name_line: QLineEdit for product name (to update)
        unit_line: QLineEdit for unit (to update)
        source: PRODUCT_CACHE dict or db_lookup_func
        error_label: QLabel for error/status (optional)
        source_type: 'cache' or 'db'
    """
    code = code_line.text().strip()
    if source_type == 'cache':
        from modules.ui_utils.input_handler import map_product_fields_from_cache
        result = map_product_fields_from_cache(product_code=code, product_cache=source)
    elif source_type == 'db':
        from modules.ui_utils.input_handler import map_product_fields_from_db
        result = map_product_fields_from_db(product_code=code, db_lookup_func=source)
    else:
        raise ValueError('Invalid source_type for handle_product_code_edit')
    if result:
        name = result['product_name']
        unit = result['record'][2] if 'record' in result and len(result['record']) > 2 else result.get('unit', 'Each')
        if name_line is not None:
            name_line.setText(name)
        if unit_line is not None:
            unit_line.setText(unit)
        if error_label:
            from modules.ui_utils import ui_feedback
            ui_feedback.set_status_label(error_label, "", ok=True)
        return True
    else:
        if name_line is not None:
            name_line.setText("")
        if unit_line is not None:
            unit_line.setText("")
        if error_label:
            from modules.ui_utils import ui_feedback
            if code:
                ui_feedback.set_status_label(error_label, "Product code not found.", ok=False)
            else:
                ui_feedback.set_status_label(error_label, "", ok=True)
        return False