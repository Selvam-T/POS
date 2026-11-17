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
- handle_selling_price(line_edit: QLineEdit, price_type: str = "price") -> float
- handle_supplier_input(line_edit: QLineEdit) -> str
- handle_category_input_line(line_edit: QLineEdit) -> str
- handle_category_input_combo(combo_box: QComboBox) -> str
- handle_veg_choose_combo(combo_box: QComboBox) -> str

- calculate_markup_value(sell_text: str, cost_text: str) -> str
	- Returns the markup percentage as a string using the formula ((Sell - Cost) / Cost) * 100. Returns 'NA' if either value is missing or if cost is 0.
- wire_markup_logic(sell_le: QLineEdit, cost_le: QLineEdit, markup_le: QLineEdit)
	- Wires real-time reactive markup updates to price fields. When either the sell or cost field changes, the markup field is updated automatically using calculate_markup_value.

## Notes
- All validation logic is in input_validation.py.
- Only minimal inline comments are present in input_handler.py; see this document for details.
- For error and info message propagation, use ui_feedback.py from the dialog/controller.
