# Product Menu (Product Management Dialog)

Updated: December 30, 2025

This doc replaces the legacy `product_menu.md`. It documents the current **product_menu controller** behavior and the design decisions we agreed on so far.

---

## Purpose

The Product Menu is a modal dialog used to manage the product table via **ADD / REMOVE / UPDATE** operations. It integrates with:

- Database CRUD functions (`modules.db_operation`)
- In-memory cache (`PRODUCT_CACHE`) kept in sync after CRUD
- Barcode scanner routing (`BarcodeManager` override path)
- Sales table flow (re-process scan after a successful ADD when opened from sales)

---

## Entry Routes (2 ways to open)

### Route A — From Menu Frame (admin/product management)
- Opens Product Menu with **ADD / REMOVE / UPDATE tabs enabled**.
- Lands on **ADD tab** by default.
- User can switch tabs freely.

### Route B — From Sales Frame (missing barcode)
Triggered when the cashier scans a barcode that **is not found** in `PRODUCT_CACHE`.
- Product Menu opens in **ADD mode** with the scanned code prefilled.
- **REMOVE / UPDATE tabs are disabled** (business rule).
- After successful ADD, the barcode is re-processed into the sales table so the item appears in the transaction.

---

## Modal + Scanner Behavior (how it works)

### Launcher
Product Menu is launched via:

- `dialog_wrapper.open_dialog_scanner_enabled()`

This launcher uses a **scanner-enabled modal** approach: the dialog installs a **barcode override callback** rather than globally blocking scanner input.

### Barcode routing
- `BarcodeManager` receives a scan string.
- If a modal override is installed, it calls the override.
- The override places the barcode into the currently active tab’s `*ProductCodeLineEdit`.

### Allowed typing while modal is open (whitelist)
Because the app uses modal scanner behavior in multiple places, `BarcodeManager.eventFilter()` whitelists “allowed input widgets” even during modal-block scenarios.
For Product Menu we whitelist:
- ADD: name/cost/sell/supplier line edits
- UPDATE: name/cost/sell/supplier line edits
- REMOVE/UPDATE search combo’s **internal lineEdit** (for typing product-name search)

> Note: scanner input is not the same as “keyboard typing”. Both are key events. If you allow a widget to accept scanner input, it will accept typing too.

---

## Focus Rules

### Landing focus
- Always land on **ADD tab**.
- Focus should land on **ADD ProductCode**.

### Tab-change focus
Whenever user switches tabs:
- Focus lands on that tab’s `*ProductCodeLineEdit`.

### Scan in ADD tab: exists vs not exists
When a barcode is set into `addProductCodeLineEdit`:

- **If code already exists in `PRODUCT_CACHE`:**
  - Show error in ADD status label
  - Keep focus in `addProductCodeLineEdit`
  - Select all text so Backspace clears quickly

- **If code does NOT exist:**
  - Prefill the code
  - Move focus to `addProductNameLineEdit` so user can continue data entry

---

## UI Structure

UI file:
- `ui/product_menu.ui`

Tab widget:
- `tabWidget` (ADD=0, REMOVE=1, UPDATE=2)

Search combos (REMOVE/UPDATE):
- removeSearchComboBox, updateSearchComboBox

Status labels:
- addStatusLabel, removeStatusLabel, updateStatusLabel

Product code line edits:
- addProductCodeLineEdit, removeProductCodeLineEdit, updateProductCodeLineEdit

---

## Field Editability Rules

### ADD tab
Editable + validated:
- ProductCode (keyboard + scanner)
- ProductName
- Category (combo, selection only)
- CostPrice (optional numeric)
- SellingPrice (mandatory numeric)
- Supplier

Not editable:
- Unit: default `EACH` and treated as display-only

### REMOVE tab
Editable:
- Search product name combo (editable typing + completer)
- ProductCode (keyboard + scanner)

Display-only (readOnly + NoFocus for consistent UI):
- ProductName
- Category
- CostPrice
- SellingPrice
- Unit
- Supplier
- LastUpdated

### UPDATE tab
Editable:
- Search product name combo (editable typing + completer)
- ProductCode (keyboard + scanner)
- ProductName
- Category (combo selection)
- CostPrice
- SellingPrice
- Supplier

Display-only:
- Unit: default `EACH`
- LastUpdated: display-only (set by DB and reflected in UI)

---

## Mandatory Fields & Validation

Validation is performed in the controller using:

- `from modules.ui_utils import input_validation`

Rules:
- In all tabs, **ProductCode** is mandatory.
- If **ProductName** and **SellingPrice** are editable in the tab, they are mandatory too.
  - (REMOVE tab displays name/price as read-only, so those are not validated there.)

Status/error propagation:
- `input_validation` returns True/False (+ error text).
- The controller sets the tab’s `*StatusLabel` to show errors.

---

## Status Label Feedback (Red/Green)

Status labels are updated via:

- `from modules.ui_utils import ui_feedback`

Convention:
- Success → green message
- Error → red message
- Clear → empty message

This is implemented in `ui_feedback.py` so every modal dialog can reuse the same behavior.

---

## Search Combo Behavior (REMOVE / UPDATE)

Combobox role:
- Editable selection of product names for search.
- Typing triggers QCompleter suggestions:
  - case-insensitive
  - substring matching

Dropdown source:
- unique + sorted product names extracted from `PRODUCT_CACHE`

Selection behavior:
- If user selects a product name from the combobox:
  - controller writes corresponding code into `*ProductCodeLineEdit`
  - controller populates the rest of the fields from `get_product_full(code)`

Scan/manual code entry behavior:
- If `*ProductCodeLineEdit` matches a product code:
  - controller populates the rest of the fields
  - controller does **not** back-fill the search combobox selection (placeholder remains)

---

## Data Sources & Population

### Primary source for lookups
- `PRODUCT_CACHE` is considered authoritative during runtime.
- Full record for display is loaded using:
  - `get_product_full(code)`

### When fields are populated
- REMOVE/UPDATE: when code is set/changed (scan or manual), loaders populate other fields.
- REMOVE/UPDATE: when a search selection is made, code is set and loaders run.

---

## CRUD Operations

### ADD
When OK is clicked and mandatory fields pass:
1. Create record in DB (`add_product(...)`) including `last_updated` timestamp formatted as `yyyy-MM-dd HH:mm:ss`
2. Refresh in-memory cache (`refresh_product_cache()`)
3. Show green confirmation in ADD status label
4. Close dialog

Sales-frame route special case:
- After ADD succeeds, the controller immediately calls:
  - `modules.table.handle_barcode_scanned(...)`
  so the newly-added product appears in the transaction.

### REMOVE
When OK is clicked:
1. Delete record in DB (`delete_product(code)`)
2. Refresh cache (`refresh_product_cache()`)
3. Show green confirmation
4. Close dialog

### UPDATE
When OK is clicked:
1. Update record in DB (`update_product(...)`)
2. Refresh cache (`refresh_product_cache()`)
3. Update UI last_updated display (DB is responsible for persistence)
4. Show green confirmation
5. Close dialog

---

## Related Files

- `modules/menu/product_menu.py` (controller)
- `ui/product_menu.ui` (layout + widget names)
- `assets/menu.qss` (dialog styling)
- `modules/db_operation/*` (CRUD + cache)
- `modules/table.py` (sales table scan handler)
- `modules/devices/barcode_manager.py` (override routing, modal blocking, whitelist)
- `modules/ui_utils/input_validation.py` (validation helpers)
- `modules/ui_utils/ui_feedback.py` (status label red/green helpers)

---

## Known Issues (tracking)
- REMOVE/UPDATE search dropdown population is under investigation and may not appear even when cache is non-empty.
  We parked this issue to revisit later.
