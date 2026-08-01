# Product Menu (Product Management Dialog)

Updated: July 2026

This document describes the current Product Menu controller behavior after the refactor to the standardized dialog pipeline.

---

## Purpose

Product Menu is a modal dialog used to manage products via **ADD / REMOVE / UPDATE** operations.
It integrates with:

- Database CRUD (`modules.db_operation`) and the in-memory cache (`PRODUCT_CACHE`)
- Barcode scanning via a temporary `BarcodeManager` override while the dialog is open

Primary implementation:

- Launcher / ADD-REMOVE-UPDATE controller: `modules/menu/product_menu.py`
- Category tab controller: `modules/menu/product_category_tab.py`
- UI: `ui/product_menu.ui`

The Product Menu was refactored in narrow, behavior-preserving steps so the
public launcher remains `launch_product_dialog(...)` in `product_menu.py`.
The extracted controllers are attached to the dialog instance to preserve their
Qt signal/event-filter lifetime for as long as the dialog is open.

---

## Standardized Pipeline (implementation pattern)

Product Menu follows the dialog pipeline used across the app:

1. Build dialog from UI via `build_dialog_from_ui(...)`.
2. Resolve widgets with `require_widgets(...)` (hard fail if required widgets are missing).
3. Configure read-only/display-only fields (`setReadOnly(True)` + `Qt.NoFocus`).
4. Wire relationships + Enter navigation using `FieldCoordinator`.
5. Apply gating using `FocusGate(lock_enabled=True)`.
6. OK/CLEAR/Close handlers validate, reset, or close using tab-specific controller functions.

---

## Entry / Opening Behavior

The constructor supports two optional knobs:

- `initial_mode`: may choose the initial tab (`add`/`remove`/`update`) when allowed.
- `initial_code`: when provided, the dialog always lands on **ADD** and prefills the ADD code.
- `opened_from_missing_scan`: explicitly identifies the barcode-not-found sales
  workflow. It is separate from the sales-table row-count check so an empty sale
  still receives the same restricted ADD workflow.

REMOVE, UPDATE, and CATEGORY are disabled when either:

- the sales table contains one or more rows; or
- Product Menu was opened automatically for a scanned product that was not found.

ADD remains accessible in both cases. Keeping these conditions separate preserves
the active-transaction guard for Product-button launches while making the
barcode-not-found behavior independent of the current sales-table row count.

After a successful ADD in the barcode-not-found workflow, the new product is
inserted into the sales table, Product Menu closes automatically, and the shared
dialog wrapper restores focus to the sales table.

Landing rules:

- Default landing tab is **ADD**.
- Landing focus goes to the active tab’s Product Code field.

---

## Dialog Sizing

Product Menu is one fixed-size frameless dialog. The shared `DialogWrapper`
calculates its size once from `DIALOG_RATIOS['product_menu']`, currently
`(0.45, 0.90)`, and centers it on the main window.

- ADD, REMOVE, UPDATE / VIEW, and CATEGORY use the same dialog dimensions.
- Tab changes clear the outgoing tab through its tab-specific reset helper,
  then perform destination focus and data-refresh work; they do not resize or
  recenter the dialog.
- There is no Product Menu-specific sizing controller, deferred geometry timer,
  per-tab ratio, or Product Menu geometry-warning suppression.
- The CATEGORY list uses an expanding layout policy inside the allocated dialog
  space. This does not change the top-level dialog size.

---

## CLEAR Buttons

Each tab has a tab-local `CLEAR` button between the action button and `CLOSE`.
CLEAR resets only the active tab's form state; it does not close the dialog and does not write to the database.
The same tab-specific reset is applied automatically when leaving a tab, so
returning to it starts from its default state.

- ADD: clears Product Code and all ADD fields, blanks the category combo, clears status, reruns the ADD gate, and returns focus to Product Code.
- REMOVE: clears Product Code, Name Search, mapped display fields, and status,
  re-locks the lookup-gated action button, then returns focus to Product Code.
- UPDATE: clears Product Code, Name Search, mapped edit/display fields, clears the loaded-value snapshot, re-locks editable fields, clears status, and returns focus to Product Code.
- CATEGORY: resets the tab to its default Add mode, clears category inputs/status, clears the selection combo through the Add-mode path, locks OK, and focuses New Category.

The implementation is intentionally tab-specific instead of a generic widget wipe so `FocusGate`, placeholders, combo state, lookup snapshots, and mode-specific locks remain consistent.

---

## Reserved Vegetable Codes (veg01–veg16)

Product Menu enforces the reserved vegetable code range in all relevant paths:

- ADD: entering `veg01` … `veg16` is blocked.
- REMOVE/UPDATE lookup: reserved veg codes are rejected as “Reserved vegetable code”.

This is enforced via `is_reserved_vegetable_code(...)` and the shared `_lookup_product(...)` boundary.

---

## Category Source of Truth

- Categories are stored in SQLite `Category`.
- `Product_list.category_id` is required and references `Category.category_id`.
- `--Select Category--` is UI-only with `userData=None`; real combo items
  carry their integer `category_id`.
- The Category tab is **admin-only**.

### Category tab behavior

- Add validates and inserts a Category row.
- Remove transactionally reassigns products to `Other`, then deletes the row.
- Replace renames in place only when the new label does not already exist.
  Category merging is not available.
- `Other` and `Vegetable` are protected; attempted remove/replace operations
  show an informative warning.
- Category changes refresh `PRODUCT_CACHE` after commit. Receipt snapshots are
  never changed.
- UI behaviour and safeguards:
	- `refresh` populates from SQLite and `clear` removes selection items.
	- Radio buttons that switch Add/Remove/Replace are wired to only trigger their handlers when becoming `checked` (prevents unintended repopulation during programmatic state changes).
	- Widgets (combo, update line edit) are explicitly enabled/disabled per mode instead of relying on implicit UI defaults.
	- Enter key behavior is intercepted in the Category tab: Enter does not auto-close the dialog. `Enter` is routed to an explicit handler which validates the current field and advances focus or requires an explicit press of the `OK` button to commit. The `OK` button is not an auto-default so focus changes won't accidentally trigger a commit.
	- Duplicate Add or Replace labels show an error, return focus to the invalid text field, and select its contents for correction.
	- The `Other` category is preserved and is now shown as its real value when present in the DB (the dialog no longer maps `Other` to a placeholder string in the UPDATE flow).
	- Successful category operations keep the dialog open, show success in the tab status label, and move focus to Close.

### Existing categories list

The CATEGORY tab includes an informational `categoriesListWidget` after the
category-management form, status, and action buttons.

- Data comes from `category_service.list_category_records()`; the UI does not
  query SQLite directly.
- Blank and placeholder values such as `--Select Category--` are excluded.
- Names are deduplicated and sorted case-insensitively A-Z.
- The standard `QListWidget` uses IconMode, left-to-right flow, wrapping,
  static movement, uniform item sizes, and two fixed-width columns.
- Each item is 300 pixels wide. Remaining viewport width is distributed evenly
  across the left gutter, center column gap, and right gutter, including when
  the vertical scrollbar is visible.
- Items are explicitly left/vertically-centered, use compact single-line row
  heights, and provide ample width for the 25-character category limit.
- Item padding is kept narrow and text is not elided.
- Items are numbered after A-Z sorting (`1.`, `2.`, and so on). Numbering is
  presentation-only and is recalculated whenever the list refreshes.
- The vertical scrollbar appears only for overflow; horizontal scrolling is
  disabled.
- The list is display-only. It does not alter the existing Remove/Replace combo
  selection behavior.
- It refreshes when Product Menu opens, whenever CATEGORY becomes active, and
  after successful category add, remove, or replace operations.
- The list expands into the remaining CATEGORY space below the OK, CLEAR, and
  CLOSE action row.


## Category tab — quick summary

- The Category tab UI behavior is implemented by `ProductCategoryTabController`
  in `modules/menu/product_category_tab.py`.
- The Category tab delegates to `modules/ui_utils/category_service.py`.
- Persistence uses `categories_repo` and `products_repo` in SQLite
  transactions.
- Product Menu triggers cache refresh / completer refresh after DB category changes so UI lookups stay current.

### Tests (category features)

- `tests/test_category_db_replace.py`: add, rename, merge rejection, delete, protected
  categories, cache refresh, and receipt snapshots.
- `tests/test_category_ui.py`: admin gating, database-backed category combos,
  fixed Product Menu geometry, category-list sorting/grid/scrolling, CRUD
  refreshes, and UI XML validity.

---

## Markup Calculation

Markup is computed (display-only) from Selling Price and Cost Price:

- Both empty → markup empty
- Only one of (sell/cost) present → markup shows `NA`
- Both present and cost $> 0$ → markup is $((sell - cost)/cost) * 100$ shown as `X.Y%`
- Any parse/edge failure → markup empty

Markup recalculates on `textChanged` for sell/cost.

---

## ADD Tab (gated input)

### Focus denial until valid Product Code

ADD input fields are gated behind a valid code using `FocusGate(lock_enabled=True)`.
All product codes are normalized to UPPER CASE, and product names/other strings to CamelCase, both when loaded into PRODUCT_CACHE and when user input is compared. Legacy DB data is normalized at cache load and input time.

Code must be:

- non-empty
- length $\ge 2$
- not a reserved veg code (`veg01`–`veg16`)
- not already present in `PRODUCT_CACHE`

While gated/locked:

- ADD fields are disabled and cannot be edited.
- UI placeholders and UI-provided default texts are hidden (then restored on unlock).
- Category combo is blanked.

When code becomes valid:

- gate unlocks and focus advances into the first ADD field.

### Enter-to-next navigation

ADD uses `FieldCoordinator.add_link(..., swallow_empty=...)` to:

- prevent Enter from closing the dialog
- enforce required fields (swallow Enter on empty)
- jump field-to-field when valid

---

## REMOVE Tab (lookup + read-only display)

REMOVE supports two lookup sources:

- code search: `removeProductCodeLineEdit`
- name search: `removeNameSearchLineEdit` (QCompleter-backed)

Rules:

- The two sources are mutually exclusive: typing in one clears the other and clears the displayed mapped fields.
- Display fields are read-only + `Qt.NoFocus`.
- The REMOVE action starts locked, unlocks only after a successful lookup, and
  re-locks when the tab is cleared or left.

- Note: The `last_updated` display in REMOVE/UPDATE is formatted via
	`modules.date_time.format_datetime()` and appears like `09 Mar 2026  03:45 pm`.
	The database stores the same value as `2026-03-09 15:45:00`; display
	formatting does not change the stored text.

---

## UPDATE Tab (lookup-gated editing + no-op protection)

UPDATE supports two lookup sources:

- code search: `updateProductCodeLineEdit`
- name search: `updateNameSearchLineEdit` (QCompleter-backed)

### Mutual exclusivity

Typing in one source clears the other source and clears stale mapped display fields.

### Lock until lookup succeeds

The editable UPDATE widgets (name/sell/cost/category/supplier/OK) start locked via `FocusGate(lock_enabled=True)`.

- On lookup failure: fields clear, category is blank (no selection), gate remains locked.
- On lookup success: fields populate, category is applied, gate unlocks.

### Update only if changed

After a successful lookup, the loaded values are snapshotted.
When OK is clicked:

- If no editable fields changed, no DB write occurs; the dialog remains open, shows "No changes to update.", and moves focus to Close.
- If fields changed, `update_product(...)` is called.

---

## Name Search (QCompleter) and Sync

Name search uses `input_handler.setup_name_search_lineedit(...)`.
Because QCompleter selection does not always emit the same “user typing” signals, the setup attaches an `on_selected` hook that explicitly triggers coordinator sync.

---

## Barcode Scans While Dialog Is Open

Product Menu installs a temporary barcode override on the host window’s `barcode_manager`.

- The override writes the scanned code into the active tab’s code field.
- It then triggers a lookup sync so mapped fields update immediately.

---

## Error handling: hard-fail vs soft-fail

Product Menu follows the shared policy in `Documentation/error_logging_and_fallback.md`.

### Soft-fail (handled)

- Validation failures: shown only in the dialog status label; dialog remains open.
- DB CRUD returns `(ok=False, msg)`: logged to `logs/error.log`, shown in dialog status label, and queued as a **post-close** StatusBar error.

### DB success + refresh failure (success-with-warning)

After a successful DB write (ADD/REMOVE/UPDATE), Product Menu refreshes cache/completers best-effort.

- Dialog-local status label shows **success**.
- The dialog applies that tab's CLEAR/reset behavior, then remains open, restores the success message, and moves focus to that tab's Close button.
- If refresh fails: a **warning** is queued for the StatusBar and displayed **after the dialog closes**.
- StatusBar precedence rule: warning/error overrides success info.

### Hard-fail (unexpected)

Unexpected exceptions that escape Product Menu are handled by `DialogWrapper`:
- overlay/scanner cleanup is performed
- details are logged to `logs/error.log`
- a short StatusBar error hint is shown after cleanup
