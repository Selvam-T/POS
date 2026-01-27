# Database Layer (`modules/db_operation`) — Architecture and API

This document explains the database layer layout after the refactor that removed `product_crud.py` usage and split responsibilities into focused modules.

## Goals

- Keep **UI code** free of raw SQL and connection management.
- Keep **DB plumbing** (path/connection/transactions) in one place.
- Keep **SQL** isolated in repository modules.
- Provide a **fast app-wide cache** for barcode lookups.

## Files and Responsibilities

### `modules/db_operation/db.py` (shared plumbing)

Use this for DB path resolution, connections, and transactions.

- `get_db_path()`
  - Priority:
    1) environment variables `POS_DB_PATH` / `DB_PATH`
    2) `config.DB_PATH`
    3) reasonable defaults under the Project folder
- `get_conn(db_path=None, timeout=5.0)`
  - Returns a `sqlite3.Connection` configured with:
    - `row_factory = sqlite3.Row`
    - `PRAGMA foreign_keys = ON`
    - WAL/synchronous pragmas when available
- `now_iso()`
  - Local ISO timestamp (seconds precision)
- `transaction(conn)`
  - Context manager for `BEGIN IMMEDIATE / COMMIT / ROLLBACK`

### `modules/db_operation/products_repo.py` (SQL only)

SQL-only repository for the `Product_list` table.

- `add_product(...)` → inserts a row (raises on errors)
- `update_product(product_code, **fields)` → returns `True` if updated
- `delete_product(product_code)` → returns `True` if deleted
- `get_product_full(product_code)` → returns a dict row or `None`
- `list_products()` / `list_products_slim()` → list rows (used by cache)

Important:
- Keep schema changes localized here.
- This module should not import PyQt.

### `modules/db_operation/product_cache.py` (app-wide cache)

In-memory cache used for fast barcode/product_code lookup.

- `PRODUCT_CACHE: Dict[str, Tuple[str, float, str]]`
  - Shape: `{PRODUCT_CODE: (display_name, selling_price, display_unit)}`
  - Product code canonicalization: always normalized to UPPER CASE (via `canonicalize_product_code()`)
  - Product name and other strings: normalized to CamelCase/Title Case (via `canonicalize_title_text()`)
  - Unit safety: blank/NULL units default to `Each`
  - Legacy DB data may be mixed case or inconsistent, but is always normalized when loaded into PRODUCT_CACHE.
  - User input is normalized at lookup time, so comparison is always in the correct case, regardless of user input or DB legacy data.

- `load_product_cache()` / `refresh_product_cache()`
  - Loads all products from DB via `products_repo.list_products_slim()`

- `get_product_info(product_code)`
  - Cache-only lookup
  - Returns `(found, name, price, unit)`

- Helpers (internal but imported by some UI code):
  - `_norm()` (uppercase normalization)
  - `_to_camel_case()` (display formatting; alias to `canonicalize_title_text()`)

## Public Facade (`modules/db_operation/__init__.py`)

Most of the app should import from `modules.db_operation` only.

Exports:
- Cache:
  - `PRODUCT_CACHE`, `load_product_cache()`, `refresh_product_cache()`, `get_product_info()`
- Product CRUD (compatibility wrappers):
  - `add_product(...) -> (ok: bool, msg: str)`
  - `update_product(...) -> (ok: bool, msg: str)`
  - `delete_product(...) -> (ok: bool, msg: str)`
  - `get_product_full(product_code) -> (found: bool, details: dict)`

`get_product_full()` maps repo fields into the keys used by dialogs:
- `price` comes from `selling_price`
- `cost` comes from `cost_price`
- `unit` defaults to `Each` if blank

## UI-only Helpers

Status bar messaging is **UI-only**:
- Use `modules/ui_utils/ui_feedback.py: show_temp_status()`
- Do not import UI helpers from `modules/db_operation`

## Common Usage Patterns

### Barcode scan / sales table
- `found, name, price, unit = modules.db_operation.get_product_info(barcode)`

### Admin/product dialogs (CRUD)
- `ok, msg = modules.db_operation.add_product(...)`
- `modules.db_operation.refresh_product_cache()` after CRUD (if dialog needs immediate updated lookups)

### Manual entry completer
- Uses `modules.db_operation.PRODUCT_CACHE` to build suggestions.

## Quick Runtime Check

A safe DB-backed smoke check (no GUI):

- Import `modules.db_operation`
- Call `load_product_cache()`
- Call `get_product_info('Veg01')`

If that works, DB path resolution, SQL repo, and cache wiring are correct.
