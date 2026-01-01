"""
input_handler.py
Reusable input reading functions for POS dialogs/widgets. Delegates validation to input_validation.py.
"""

from PyQt5.QtWidgets import QLineEdit, QComboBox
from PyQt5.QtCore import Qt
import re
from modules.ui_utils import input_validation


def handle_product_code_input(line_edit: QLineEdit) -> str:
    """
    Reads and validates product code input from a QLineEdit widget.
    Returns the cleaned product code string if valid, else raises ValueError.
    """
    code = line_edit.text().strip()
    input_validation.validate_product_code(code)
    return code


def handle_product_name_search(combo_box: QComboBox, search_text: str) -> list:
    """
    Filters and returns matching product names from QComboBox based on search_text.
    Returns a list of matching items.
    """
    search_text = search_text.strip().lower()
    matches = []
    for i in range(combo_box.count()):
        item_text = combo_box.itemText(i).lower()
        if search_text in item_text:
            matches.append(combo_box.itemText(i))
    return matches


def handle_product_name_input(line_edit: QLineEdit) -> str:
    """
    Reads and validates product name input from a QLineEdit widget.
    Returns the cleaned product name string if valid, else raises ValueError.
    """
    name = line_edit.text().strip()
    input_validation.validate_product_name(name)
    return name


def handle_quantity_input(line_edit: QLineEdit) -> float:
    """
    Reads and validates quantity input from a QLineEdit widget.
    Returns the quantity as a float if valid, else raises ValueError.
    """
    text = line_edit.text().strip()
    input_validation.validate_quantity(text)
    return float(text)


def handle_email_input(line_edit: QLineEdit) -> str:
    """
    Reads and validates email input from a QLineEdit widget.
    Returns the email string if valid, else raises ValueError.
    """
    email = line_edit.text().strip()
    input_validation.validate_email(email)
    return email


def handle_password_input(line_edit: QLineEdit) -> str:
    """
    Reads and validates password input from a QLineEdit widget.
    Returns the password string if valid, else raises ValueError.
    """
    password = line_edit.text()
    input_validation.validate_password(password)
    return password


def handle_unit_input_combo(combo_box: QComboBox) -> str:
    """
    Reads unit input from a QComboBox widget.
    Returns the selected unit string if valid (not default/placeholder), else raises ValueError.
    """
    unit = combo_box.currentText().strip()
    input_validation.validate_unit(unit)
    return unit


def handle_price_input(line_edit: QLineEdit, price_type: str = "price") -> float:
    """
    Reads and validates cost or selling price input from a QLineEdit widget.
    Returns the price as a float if valid, else raises ValueError.
    """
    text = line_edit.text().strip()
    input_validation.validate_price(text, price_type)
    return float(text)


def handle_supplier_input(line_edit: QLineEdit) -> str:
    """
    Reads and validates supplier input from a QLineEdit widget.
    Returns the supplier string (optional, can be empty).
    """
    supplier = line_edit.text().strip()
    input_validation.validate_supplier(supplier)
    return supplier


def handle_category_input_line(line_edit: QLineEdit) -> str:
    """
    Reads and validates category input from a QLineEdit widget.
    Returns the category string if valid, else raises ValueError.
    """
    category = line_edit.text().strip()
    input_validation.validate_category(category)
    return category


def handle_category_input_combo(combo_box: QComboBox) -> str:
    """
    Reads category input from a QComboBox widget.
    Returns the selected category string if valid (not default/placeholder), else raises ValueError.
    """
    category = combo_box.currentText().strip()
    input_validation.validate_category(category)
    return category


def handle_veg_choose_combo(combo_box: QComboBox) -> str:
    """
    Reads vegetable slot selection from vegMChooseComboBox.
    Returns the selected slot string (including placeholder if selected).
    No validation is performed; dialog/controller should handle logic for placeholder/default selection.
    """
    return combo_box.currentText().strip()


def handle_greeting_combo(combo_box: QComboBox) -> str:
    """
    Reads greeting selection from greeting_menu QComboBox.
    Returns the selected greeting string (no placeholder validation).
    """
    return combo_box.currentText().strip()


# Additional reusable input handlers can be added here for other widgets and dialogs.
