"""modules/ui_utils/input_handler.py

Reusable input reading and validation functions for POS dialogs/widgets.
Each handler reads input from a widget, delegates validation to input_validation.py,
and returns the cleaned value or raises ValueError.
"""

from __future__ import annotations

import re

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QComboBox, QLineEdit

from modules.ui_utils import input_validation


def _raise_if_invalid(result):
    """Accepts either (ok, err) from validators or None; raises ValueError on invalid."""
    if result is None:
        return
    if isinstance(result, tuple) and len(result) == 2:
        ok, err = result
        if not ok:
            raise ValueError(err)
        return
    # If a validator returns something unexpected, treat as pass-through.


def handle_product_name_search_LineEdit(line_edit: QLineEdit, name_to_code: dict) -> str:
    """Validate product name from QLineEdit and map to product code using name_to_code."""
    name = line_edit.text().strip()
    try:
        _raise_if_invalid(input_validation.validate_product_name(name))
    except ValueError as ve:
        raise ValueError(f"Invalid product name: {ve}")
    if name not in name_to_code:
        raise ValueError("Product name not found in list. Please select a valid product.")
    return name_to_code[name]


def handle_product_code_input(line_edit: QLineEdit) -> str:
    """Validate and return product code from QLineEdit."""
    code = line_edit.text().strip()
    _raise_if_invalid(input_validation.validate_product_code_format(code))
    return code


def handle_product_name_search(combo_box: QComboBox, search_text: str) -> list:
    """Return product names from QComboBox matching search_text."""
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


# Add more input handlers as needed.
