# input_handler.py Documentation

## Purpose
Reusable input handling functions for dialogs and widgets in the POS system. This module centralizes input reading and delegates validation to input_validation.py, reducing duplication and improving maintainability.

## Usage
- Each function reads input from a widget (QLineEdit or QComboBox) and calls the corresponding validation function in input_validation.py.
- If validation fails, an exception is raised by input_validation.py.
- Message propagation and error display are handled by the dialog/controller, not by input_handler.py.

## Functions
- handle_product_code_input(line_edit: QLineEdit) -> str
- handle_product_name_search(combo_box: QComboBox, search_text: str) -> list
- handle_product_name_input(line_edit: QLineEdit) -> str
- handle_quantity_input(line_edit: QLineEdit) -> float
- handle_email_input(line_edit: QLineEdit) -> str
- handle_password_input(line_edit: QLineEdit) -> str
- handle_unit_input_combo(combo_box: QComboBox) -> str
- handle_price_input(line_edit: QLineEdit, price_type: str = "price") -> float
- handle_supplier_input(line_edit: QLineEdit) -> str
- handle_category_input_line(line_edit: QLineEdit) -> str
- handle_category_input_combo(combo_box: QComboBox) -> str
- handle_veg_choose_combo(combo_box: QComboBox) -> str
- handle_greeting_combo(combo_box: QComboBox) -> str

## Notes
- All validation logic is in input_validation.py.
- Only minimal inline comments are present in input_handler.py; see this document for details.
- For error and info message propagation, use ui_feedback.py from the dialog/controller.
