# Product Management: Design, Behavior, and Integration

This document summarizes the Product Management feature (product_menu.ui / open_product_panel) and how it integrates with Sales scanning, the in-memory cache, and the database.

## Goals
- Provide a focused UI to ADD, REMOVE, and UPDATE products.
- Keep the interaction simple and safe (clear modes, validation, no accidental deletes).
- Ensure newly added/updated products are immediately usable by the Sales flow (scanner and sales table) without restarting the app.

## UI and Modes
- Dialog: `ui/product_menu.ui` loaded by `MainLoader.open_product_panel`.
- Mode buttons: ADD, REMOVE, UPDATE.
- The dialog starts hidden (neutral state). The form and sub-header become visible only after a mode is chosen.
- Sub-header reflects the selected mode (Add New Product / Remove Product / Update Product).

### Field enablement and behavior
- Last updated is always read-only/disabled; it’s set automatically on ADD/UPDATE.
- In REMOVE and UPDATE:
  - Only the Product Code field is enabled initially.
  - After a valid code is entered/found, fields are populated.
  - UPDATE enables all fields for editing; REMOVE keeps them disabled.
- In ADD:
  - All fields are enabled.
  - Required fields: Product Code, Product Name, Selling Price.
  - Unit is a dropdown with: pcs, kg.

### Mode locking
- Once a mode is selected, the mode buttons are disabled (locked) so the user completes or cancels.
- Modes unlock after OK (ADD/DELETE/UPDATE) or CANCEL.

### Sales-in-progress restrictions
- When the Sales table has one or more items listed, the Product dialog restricts actions to ADD only.
- REMOVE and UPDATE/View buttons are disabled to prevent changing or deleting products that are already listed in the current sale.
- Finish or cancel the ongoing sale to enable REMOVE/UPDATE/View again.
  - If the dialog is opened programmatically with an initial mode of REMOVE/UPDATE while a sale is active, it automatically starts in ADD mode.

### Enter key behavior
- Pressing Enter in Product Code during REMOVE/UPDATE:
  - Performs lookup, locks the mode (if not already), then advances focus like Tab on the next event loop tick (prevents accidental submit on the same Enter).
- Pressing Enter in fields generally moves to the next widget (acts like Tab) instead of clicking OK.
- The OK button is not default unless it has focus.

### Status label and auto-close
- A status label shows success/error messages above the action buttons.
- On success, the dialog auto-closes after ~1 second.

## Database and Cache
- DB file path is centralized in `config.py` as `DB_PATH`. The DB resides at `../db/Anumani.db` relative to the Project folder.
- The Product cache is an in-memory slim mapping: `{ product_code -> (name, selling_price) }`.
- Cache keys are normalized (uppercase + trimmed) to avoid case/whitespace mismatches.
- CRUD operations update the cache immediately:
  - ADD: Inserts normalized key with name and price.
  - UPDATE: Merges updated fields into the normalized entry.
  - DELETE: Removes all case variants of the code.
- Additionally, after ADD/UPDATE/DELETE in the dialog, we call a cache refresh to ensure absolute consistency.

### Full vs slim lookups
- `get_product_info(code)` returns from the in-memory cache (name + price) for speed (scanner, sales table).
- `get_product_full(code)` hits SQLite for full row data (used in UPDATE/REMOVE population).

## Scanning Flow Integration
- Global scan handler: `MainLoader.on_barcode_scanned(barcode)`
  - Normalizes the scanned text (strip whitespace).
  - If a modal overrides barcode handling (e.g., Product dialog open), the override captures the scan—populating Product Code and, for UPDATE/REMOVE, performing the lookup. No Manual Entry auto-open occurs here.
  - Otherwise, it looks up the product in the in-memory cache:
    - If found → add (or increment) in `salesTable` using `handle_barcode_scanned`.
    - If not found → open Product Management in ADD mode with Product Code prefilled.

### After ADD from a scanned-not-found flow
- When the user successfully ADDs the product from the Product dialog that was opened due to an unknown scan:
  - The cache is refreshed.
  - The product is added to the sales table automatically (as if it was scanned again).

### Scanner input behavior and focus rules
- While the Product dialog is open, scans are accepted only when `productCodeLineEdit` is focused; otherwise scans are ignored and any stray character is cleaned up.
- Enter on line edits behaves like Tab to advance focus; action buttons are not default unless focused.
- For the full cross-application routing rules and protections (modal block, overlay, Enter suppression), see Documentation/scanner_input_infocus.md.

## Manual Entry Dialog Policy
- Manual Entry (`ui/manual_entry.ui`) is only opened by its explicit button in the Sales frame.
- We intentionally removed auto-opening Manual Entry on unknown scans to simplify the flow and avoid conflicting contexts.

## Why this design
- Performance: A slim, normalized in-memory cache keeps scans and sales updates fast and reliable.
- Safety and clarity: Mode locking prevents accidental mode switching; Enter behaves predictably and avoids accidental destructive actions.
- Seamless sales workflow: Unknown scans guide users into ADD, then return them to Sales with the item added—no restart required.
- Single source of truth for DB path in `config.py` reduces “which DB file?” confusion.

## Developer Notes
- Files of interest:
  - `main.py` – dialog wiring, scan routing, cache refresh, and sales table integration.
  - `modules/db_operation/database.py` – DB access and product cache management.
  - `modules/sales/salesTable.py` – sales table row add/increment logic.
  - `ui/product_menu.ui` – dialog layout.
  - `config.py` – `DB_PATH`, formats, icons.
- Error prints are minimized in production; most user feedback goes through the status bar or dialog status label.
