# Product Menu (Product Management Dialog)

Updated: January 2026

This document describes the current Product Menu controller behavior after the refactor to the standardized dialog pipeline.

---

## Purpose

Product Menu is a modal dialog used to manage products via **ADD / REMOVE / UPDATE** operations.
It integrates with:

- Database CRUD (`modules.db_operation`) and the in-memory cache (`PRODUCT_CACHE`)
- Barcode scanning via a temporary `BarcodeManager` override while the dialog is open

Primary implementation:

- Controller: `modules/menu/product_menu.py` (`open_dialog_scanner_enabled`)
- UI: `ui/product_menu.ui`

---

## Standardized Pipeline (implementation pattern)

Product Menu follows the dialog pipeline used across the app:

1. Build dialog from UI via `build_dialog_from_ui(...)`.
2. Resolve widgets with `require_widgets(...)` (hard fail if required widgets are missing).
3. Configure read-only/display-only fields (`setReadOnly(True)` + `Qt.NoFocus`).
4. Wire relationships + Enter navigation using `FieldCoordinator`.
5. Apply gating using `FocusGate(lock_enabled=True)`.
6. OK/Cancel handlers validate + write using DB operation functions.

---

## Entry / Opening Behavior

The constructor supports two optional knobs:

- `initial_mode`: may choose the initial tab (`add`/`remove`/`update`) when allowed.
- `initial_code`: when provided, the dialog always lands on **ADD** and prefills the ADD code.

If there is an active sale transaction (`sale_lock=True`):

- REMOVE and UPDATE tabs are disabled.

Landing rules:

- Default landing tab is **ADD**.
- Landing focus goes to the active tab’s Product Code field.

---

## Reserved Vegetable Codes (veg01–veg16)

Product Menu enforces the reserved vegetable code range in all relevant paths:

- ADD: entering `veg01` … `veg16` is blocked.
- REMOVE/UPDATE lookup: reserved veg codes are rejected as “Reserved vegetable code”.

This is enforced via `is_reserved_vegetable_code(...)` and the shared `_lookup_product(...)` boundary.

---

## Category Source of Truth

- Categories are sourced from `config.PRODUCT_CATEGORIES`.
- The first combo item is treated as a UI-provided placeholder (from the `.ui`).
- The controller clears/rebuilds the combo and appends config categories.

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
- length $\ge 4$
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

- If no editable fields changed, the dialog closes without writing.
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
- DB CRUD returns `(ok=False, msg)`: logged to `log/error.log`, shown in dialog status label, and queued as a **post-close** StatusBar error.

### DB success + refresh failure (success-with-warning)

After a successful DB write (ADD/REMOVE/UPDATE), Product Menu refreshes cache/completers best-effort.

- Dialog-local status label shows **success**.
- If refresh fails: a **warning** is queued for the StatusBar and displayed **after the dialog closes**.
- StatusBar precedence rule: warning/error overrides success info.

### Hard-fail (unexpected)

Unexpected exceptions that escape Product Menu are handled by `DialogWrapper`:
- overlay/scanner cleanup is performed
- details are logged to `log/error.log`
- a short StatusBar error hint is shown after cleanup
