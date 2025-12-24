# Product Menu: UI Component Overview

The Product Menu is a modular dialog within the POS application, providing product management features as part of the overall inventory and sales workflow. It is accessed from the main application and interacts with the database, in-memory cache, and other modules.

## Role in the POS System
- **Purpose:** Allows users to add, remove, and update product records.
- **Integration:** Works with the database layer, product cache, and barcode scanning infrastructure.
- **UI Location:** Defined in `ui/product_menu.ui` and styled via `assets/product_menu.qss`.

## UI Structure (as of Dec 2025)
- **Tabbed Dialog:**
  - **ADD Tab:**
    - For adding new products. All input widgets use unique names (e.g., `addProductCodeLineEdit`).
    - Product code accepts barcode scanner and keyboard input.
    - Product name, category, cost price, selling price, unit (read-only), supplier fields.
    - Status label: `addStatusLabel`.
  - **REMOVE Tab:**
    - For removing products. Product code and product name (QComboBox: `removeProductNameComboBox`) are editable/searchable.
    - Other fields are display-only for confirmation.
    - Status label: `removeStatusLabel`.
  - **UPDATE Tab:**
    - For updating product details. Product code and product name (QComboBox: `updateProductNameComboBox`) are editable/searchable.
    - Other fields become editable after a valid product is selected.
    - Status label: `updateStatusLabel`.

## Widget Naming Convention
- All widgets are uniquely named per tab for clarity and reliable event handling (e.g., `addProductCodeLineEdit`, `removeProductNameComboBox`, `updateStatusLabel`).
- Layouts and subheaders also use unique names (e.g., `addLayout`, `removeSubHeaderLabel`).

## Related Files
- `modules/menu/product_menu.py`: Controller logic (to be documented after implementation).
- `ui/product_menu.ui`: UI definition.
- `assets/product_menu.qss`: Styling.
- `modules/db_operation/database.py`: Database operations.

---
*Last updated: December 25, 2025*
