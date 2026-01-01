"""
input_handler.py
===============
Reusable input handling functions for dialogs and widgets in the POS system.

This module provides shared functions for accepting, validating, and applying inputs from widgets such as QLineEdit and QComboBox. The goal is to centralize input logic for product code, product name search, product name input, quantity, email, password, unit, cost price, selling price, supplier, category, vegetable slot selection, and greeting selection, reducing duplication across dialogs.

References:
- product_menu controller
- sales Table
- vegetable_menu controller

Functions:
- handle_product_code_input(line_edit: QLineEdit) -> str
    Accepts and validates product code input from a QLineEdit widget.
- handle_product_name_search(combo_box: QComboBox, search_text: str) -> list
    Handles product name search using a QComboBox and search text.
- handle_product_name_input(line_edit: QLineEdit) -> str
    Accepts and validates product name input from a QLineEdit widget.
- handle_quantity_input(line_edit: QLineEdit) -> float
    Accepts and validates quantity input from a QLineEdit widget.
- handle_email_input(line_edit: QLineEdit) -> str
    Accepts and validates email input from a QLineEdit widget.
- handle_password_input(line_edit: QLineEdit) -> str
    Accepts and validates password input from a QLineEdit widget.
- handle_unit_input_combo(combo_box: QComboBox) -> str
    Accepts and validates unit input from a QComboBox widget (must not be placeholder).
- handle_price_input(line_edit: QLineEdit, price_type: str = "price") -> float
    Accepts and validates cost or selling price input from a QLineEdit widget.
- handle_supplier_input(line_edit: QLineEdit) -> str
    Accepts supplier input from a QLineEdit widget (optional, can be empty).
- handle_category_input_line(line_edit: QLineEdit) -> str
    Accepts and validates category input from a QLineEdit widget.
- handle_category_input_combo(combo_box: QComboBox) -> str
    Accepts and validates category input from a QComboBox widget (must not be default).
- handle_veg_choose_combo(combo_box: QComboBox) -> str
    Returns the selected vegetable slot string from vegMChooseComboBox (no validation, placeholder permitted).
- handle_greeting_combo(combo_box: QComboBox) -> str
    Returns the selected greeting string from greeting_menu QComboBox (no validation, placeholder permitted).

Usage:
Import and use these functions in dialogs to avoid duplicating input logic. Dialogs/controllers should handle any logic for placeholder/default selections where permitted.
"""


from PyQt5.QtWidgets import QLineEdit, QComboBox
from PyQt5.QtCore import Qt
import re


def handle_product_code_input(line_edit: QLineEdit) -> str:
    """
    Reads and validates product code input from a QLineEdit widget.
    Returns the cleaned product code string if valid, else raises ValueError.
    """
    code = line_edit.text().strip()
    if not code:
        raise ValueError("Product code cannot be empty.")
    # Add more validation rules as needed (e.g., length, format)
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
    if not name:
        raise ValueError("Product name cannot be empty.")
    # Add more validation rules as needed (e.g., allowed characters)
    return name


def handle_quantity_input(line_edit: QLineEdit) -> float:
    """
    Reads and validates quantity input from a QLineEdit widget.
    Returns the quantity as a float if valid, else raises ValueError.
    """
    text = line_edit.text().strip()
    if not text:
        raise ValueError("Quantity cannot be empty.")
    try:
        quantity = float(text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        raise ValueError("Invalid quantity. Must be a positive number.")
    return quantity


def handle_email_input(line_edit: QLineEdit) -> str:
    """
    Reads and validates email input from a QLineEdit widget.
    Returns the email string if valid, else raises ValueError.
    """
    email = line_edit.text().strip()
    if not email:
        raise ValueError("Email cannot be empty.")
    # Simple regex for email validation
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(email_regex, email):
        raise ValueError("Invalid email address.")
    return email


def handle_password_input(line_edit: QLineEdit) -> str:
    """
    Reads and validates password input from a QLineEdit widget.
    Returns the password string if valid, else raises ValueError.
    """
    password = line_edit.text()
    if not password:
        raise ValueError("Password cannot be empty.")
    # Add more password rules as needed (length, complexity)
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")
    return password


def handle_unit_input_combo(combo_box: QComboBox) -> str:
    """
    Reads unit input from a QComboBox widget.
    Returns the selected unit string if valid (not default/placeholder), else raises ValueError.
    """
    unit = combo_box.currentText().strip()
    if not unit or unit.lower() == "select unit":
        raise ValueError("Unit must be selected.")
    return unit


def handle_price_input(line_edit: QLineEdit, price_type: str = "price") -> float:
    """
    Reads and validates cost or selling price input from a QLineEdit widget.
    Returns the price as a float if valid, else raises ValueError.
    """
    text = line_edit.text().strip()
    if not text:
        raise ValueError(f"{price_type.capitalize()} cannot be empty.")
    try:
        price = float(text)
        if price < 0:
            raise ValueError
    except ValueError:
        raise ValueError(f"Invalid {price_type}. Must be a non-negative number.")
    return price


def handle_supplier_input(line_edit: QLineEdit) -> str:
    """
    Reads and validates supplier input from a QLineEdit widget.
    Returns the supplier string (optional, can be empty).
    """
    supplier = line_edit.text().strip()
    return supplier


def handle_category_input_line(line_edit: QLineEdit) -> str:
    """
    Reads and validates category input from a QLineEdit widget.
    Returns the category string if valid, else raises ValueError.
    """
    category = line_edit.text().strip()
    if not category:
        raise ValueError("Category cannot be empty.")
    return category


def handle_category_input_combo(combo_box: QComboBox) -> str:
    """
    Reads category input from a QComboBox widget.
    Returns the selected category string if valid (not default/placeholder), else raises ValueError.
    """
    category = combo_box.currentText().strip()
    if not category or category.lower() == "other":  # Assuming 'Other' is default
        raise ValueError("Category must be selected.")
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
