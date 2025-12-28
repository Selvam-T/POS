# Product Menu Module Documentation

## Overview

The `product_menu` module provides the logic and UI integration for the Product Management panel in the POS system. It supports three main operations via a tabbed interface:
- **ADD**: Add new products to the database.
- **REMOVE**: Remove products from the database. Product name is a QComboBox for search and selection.
- **UPDATE / VIEW**: Update product details. Product name is a QComboBox for search and editing. All widgets use unique, descriptive names per tab for clarity and maintainability.

The module is designed to:
All widgets in `product_menu.ui` now use unique, descriptive names per tab (e.g., `addProductCodeLineEdit`, `removeProductNameComboBox`, `updateStatusLabel`).
REMOVE and UPDATE tabs use a QComboBox for product name, supporting both search and editing (UPDATE).
All layouts, subheaders, and status labels are uniquely named (e.g., `addLayout`, `removeSubHeaderLabel`).
The previous CANCEL button issue is resolved due to unique widget names per tab.
- **Sales-Active Lock**: If the sales table has rows, only the ADD tab is enabled; REMOVE and UPDATE are disabled.
- **Barcode Integration**: Supports barcode scanning to prefill product codes and trigger product lookup.
- **Unit Standardization**: All units normalized to uppercase (KG or EACH) before database write. Input accepts any case (kg, Kg, each, EACH) but stores uppercase.
- **Unit Validation**: Dropdown limited to KG/EACH options. Empty selections default to EACH.
- **Cache Updates**: All add/update operations refresh PRODUCT_CACHE with 3-tuple: `{code: (name, price, unit)}`.
- **Status Feedback**: Provides real-time status messages for validation and operation results.

## Lingering Problem

## Button Naming and Styling Update (Dec 2025)
- All dialog action buttons now use unique, suffix-based object names for clarity and reliable signal wiring:
    - OK/affirmative: ends with `Ok` (e.g., `btnAddOk`, `btnUpdateOk`)
    - Destructive: ends with `Del` (e.g., `btnVegMDel`)
    - Cancel/dismiss: ends with `Cancel` (e.g., `btnAddCancel`, `btnUpdateCancel`)
- QSS styling now uses these suffixes for consistent color, font, and hover/pressed effects.
- The previous issue with CANCEL button wiring is resolved by using unique object names per tab.

## Further Features To Be Implemented
- **Dynamic Tab Enablement:** Refresh tab enable/disable state if sales table contents change while the dialog is open.
- **Unit Tests:** Add automated tests for product CRUD operations and UI event handling.
- **Improved Error Handling:** More granular feedback for database errors and validation failures.
- **Accessibility Enhancements:** Keyboard navigation, focus management, and screen reader support.
- **Bulk Operations:** Support for importing/exporting product lists and batch updates.
- **Audit Logging:** Track product changes for security and compliance.

## References
- `modules/menu/product_menu.py`: Main controller logic.
- `ui/product_menu.ui`: Tabbed dialog UI definition.
- `assets/product_menu.qss`: Dedicated stylesheet.
- `modules/db_operation/database.py`: Product CRUD and cache.

---
*Last updated: December 25, 2025*
