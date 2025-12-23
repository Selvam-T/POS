# Product Menu Module Documentation

## Overview
The `product_menu` module provides the logic and UI integration for the Product Management panel in the POS system. It supports three main operations via a tabbed interface:
- **ADD**: Add new products to the database.
- **REMOVE**: Display-only view for deleting products.
- **UPDATE / VIEW**: Update product details (with some fields read-only).

The module is designed to:
- Enforce uniqueness for both Product Code and Product Name.
- Normalize product names to CamelCase.
- **Standardize units:** Only KG or EACH allowed (case-insensitive input, stored uppercase).
- **Unit validation:** Empty/NULL units default to EACH.
- Hide the Last Updated field in ADD mode.
- Use display-only labels in REMOVE mode for clarity and safety.
- Disable REMOVE and UPDATE tabs if there are active sales (rows in the sales table).
- Apply a dedicated stylesheet (`product_menu.qss`) for consistent UI.
- **PRODUCT_CACHE integration:** Updates cache with (name, price, unit) 3-tuple on add/update.
- Modularize logic for maintainability and future unit testing.

## Key Features
- **Scoped Widget Binding**: Each tab has its own set of widgets (with duplicate object names), requiring dynamic binding and event wiring when the tab changes.
- **Sales-Active Lock**: If the sales table has rows, only the ADD tab is enabled; REMOVE and UPDATE are disabled.
- **Barcode Integration**: Supports barcode scanning to prefill product codes and trigger product lookup.
- **Unit Standardization**: All units normalized to uppercase (KG or EACH) before database write. Input accepts any case (kg, Kg, each, EACH) but stores uppercase.
- **Unit Validation**: Dropdown limited to KG/EACH options. Empty selections default to EACH.
- **Cache Updates**: All add/update operations refresh PRODUCT_CACHE with 3-tuple: `{code: (name, price, unit)}`.
- **Status Feedback**: Provides real-time status messages for validation and operation results.

## Lingering Problem
**CANCEL Button Issue:**
- The CANCEL button works in the ADD tab but does not reliably close the dialog in REMOVE or UPDATE/VIEW tabs. Extensive attempts to rebind signals, forcibly close the dialog, and connect all tab instances have not resolved the issue. The root cause appears to be a PyQt signal/slot or focus quirk when switching tabs with duplicate object names.
- **Workaround:** Users can close the dialog from the ADD tab or by using the window close button (if enabled). Further investigation is needed, possibly involving unique object names per tab or a refactor to avoid duplicate widget names.

## Button Naming and Styling Update (Dec 2025)
- All dialog action buttons now use unique, suffix-based object names for clarity and reliable signal wiring:
    - OK/affirmative: ends with `Ok` (e.g., `btnAddOk`, `btnUpdateOk`)
    - Destructive: ends with `Del` (e.g., `btnVegmenuDel`)
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
*Last updated: November 8, 2025*
