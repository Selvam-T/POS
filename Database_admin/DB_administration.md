# Database Administration

This folder contains company-agnostic scripts used to create a fresh POS SQLite database and import product data.

## Folder Structure

```text
Database_admin/
  config/
    .env
  data/
    imports/
      products.csv
    reports/
      rejected_products.csv
      product_validation_summary.txt
    reference/
      category_target_list.csv
      product_list_clean.xlsx
      product_list_MASTER.xls
  database/
    create_database.py
    reset_database.py
  tables/
    create_category_table.py
    create_product_list_table.py
    create_user_table.py
    create_receipt_tables.py
    create_cash_outflows_table.py
  users/
    initialize_default_users.py
  products/
    import_products.py
    export_products.py
    replace_products.py
  migration/
    migrate_categories_to_table.py
    stage_legacy_products.py
    validate_legacy_products.py
    migrate_legacy_products.py
  audit/
    verify_db_and_product_list.py
    audit_database.py
  legacy/
    old maintenance scripts
  setup_fresh_database.py
```

`admin_lib.py` is the shared helper module used by the admin scripts. It centralizes config loading, database path resolution, CSV reading/writing, SQLite connection setup, and common product-cleaning helpers.

The `data` subfolders have distinct purposes:

- `imports` contains operational CSV input and the default product export used to prepare a later import.
- `reports` contains generated validation summaries and rejected-row reports.
- `reference` contains human-maintained spreadsheets and reference lists; administration scripts do not import these files automatically.

## Configuration

Database settings live in:

```text
Database_admin/config/.env
```

Default database file for the current POS application:

```text
../db/Anumani.db
```

The admin scripts are configurable, but the current POS application expects `Anumani.db`. To use a different company-specific file later, update both Database_admin config and the POS application database config.

```properties
DB_NAME=CustomerName.db
DB_PATH=../db/CustomerName.db
```

## Product CSV

Place the import file here:

```text
Database_admin/data/imports/products.csv
```

Required headers:

```csv
product_code,name,category,supplier,selling_price,cost_price,unit,last_updated
```

Required fields:

```text
product_code
name
selling_price
```

Optional fields:

```text
category
supplier
cost_price
unit
last_updated
```

## Main Setup

Run from `Database_admin`:

```bash
python setup_fresh_database.py
```

If an old development database still exists and should be moved to a timestamped backup first:

```bash
python setup_fresh_database.py --reset
```

The setup script runs these steps in order:

1. Create the configured SQLite database file.
2. Create `users`.
3. Initialize default `admin` and `staff` users.
4. Validate the category master CSV and create `Category`.
5. Create `Product_list` with its required Category foreign key.
6. Create `receipts`, `receipt_items`, and `receipt_payments`.
7. Create `cash_outflows`.
8. Stage `data/imports/products.csv` in memory.
9. Validate and clean staged products in memory.
10. Resolve category names to IDs and migrate products.
11. Run database audit.

If validation fails, the process stops and writes inspection files under `data/reports/`.

```text
data/reports/rejected_products.csv
data/reports/product_validation_summary.txt
```

Fix `data/imports/products.csv`, then rerun `setup_fresh_database.py`.

## Category Table Migration

The controlled migration from the legacy category JSON/text model uses:

```text
Database_admin/data/reference/category_target_list.csv
```

The CSV must have exactly one header:

```csv
category
```

Every data cell must be nonblank and pass the application's category-name
validation. Names must be unique case-insensitively. `Other` and `Vegetable`
are required protected categories. The UI-only `--Select Category--`
placeholder must not appear in the CSV.

Run the read-only preflight first:

```bash
python migration/migrate_categories_to_table.py --preflight
```

Preflight validates the complete CSV and audits every legacy
`Product_list.category`. Blank or NULL product categories are permitted at
this stage because the write phase maps them to `Other`. Any other product
category absent from the validated CSV stops the migration without writes.

After a verified database and JSON backup, run:

```bash
python migration/migrate_categories_to_table.py
```

The write phase uses one transaction to:

1. map blank or NULL `Product_list.category` values to `Other`;
2. create `Category`; and
3. populate it from the validated CSV.

`Category.name` is unique case-insensitively. `Other` and `Vegetable` receive
`is_protected = 1`; all other imported categories receive `0`.

This first migration stage prepares Category and legacy product text for the
foreign-key conversion. It does not change `receipt_items.category`.

After Steps 2–7 have been verified, run the Product_list foreign-key
migration:

```bash
python migration/migrate_product_category_fk.py
```

This migration performs Steps 8–10 in one transaction:

1. adds a temporary `Product_list.category_id`;
2. maps every legacy category name to `Category.category_id`;
3. stops and rolls back if any product is unresolved;
4. rebuilds `Product_list` without the legacy category text column;
5. requires `category_id`; and
6. enforces `ON UPDATE RESTRICT` and `ON DELETE RESTRICT`.

Before dropping the legacy table, the migration compares all retained product
values between the old and rebuilt tables. It also restores the
`idx_product_code_nocase` index and runs SQLite foreign-key verification.

The POS repositories, cache, menus, exports, administration tools, and tests
now use `category_id` plus Category joins. Product CSV exports intentionally
emit readable category names, and imports resolve those names back to IDs.

`receipt_items.category` remains unchanged historical text and never receives
a Category foreign key.

## Rebuilding With A New Product CSV

For development or a full customer database rebuild, replace:

```text
Database_admin/data/imports/products.csv
```

Then run:

```bash
python setup_fresh_database.py --reset
```

This creates a fresh database from the new CSV. Existing transaction data is not preserved:

- receipt tables become empty.
- cash outflows become empty.
- users are reinitialized.
- products are loaded from the new CSV.

Do not use `--reset` casually on a production database. Production product updates should use a safer update/import process that preserves receipts and operational history.

## Replacing Only Product_list

`products/replace_products.py` is the guarded production-catalog workflow. It requires explicit database and CSV paths and does not use the configured default database implicitly.

Always work on a complete copy of the closed production database. Validate first:

```powershell
python products/replace_products.py `
  --db "C:\path\to\Anumani_working_YYYYMMDD.db" `
  --csv "C:\path\to\products_cleaned.csv" `
  --report-dir "C:\path\to\validation_reports" `
  --check-only
```

Review `rejected_products.csv` and `product_validation_summary.txt`. Replacement is blocked if validation rejects any row.

After validation and independent backup confirmation, run the replacement with the exact confirmation phrase:

```powershell
python products/replace_products.py `
  --db "C:\path\to\Anumani_working_YYYYMMDD.db" `
  --csv "C:\path\to\products_cleaned.csv" `
  --report-dir "C:\path\to\validation_reports" `
  --confirm REPLACE-PRODUCT-LIST
```

The command:

1. validates the complete CSV before opening a write transaction.
2. opens the explicitly named existing database.
3. verifies the database uses the `Category` and `Product_list.category_id`
   foreign-key schema.
4. records all non-`Product_list` table row counts.
5. begins one immediate transaction.
6. resolves every CSV category name to an existing `Category.category_id`.
7. deletes only `Product_list` rows.
8. inserts the complete validated catalog using the resolved category IDs.
9. ensures `uq_product_name_nocase` exists as a unique `NOCASE` index.
10. verifies required fields, row count, and duplicate groups.
11. verifies that unrelated table row counts did not change.
12. commits only after every check succeeds; otherwise it rolls back.

This command does not create a missing database and does not reset users, receipts, payments, receipt counters, or cash outflows. Row-count preservation is an additional guard; the pre-migration backup remains the authoritative rollback.

After replacement, run the full audit against the same explicit working-copy path:

```powershell
python audit/verify_db_and_product_list.py `
  --db "C:\path\to\Anumani_working_YYYYMMDD.db"
```

## Product Rules

### Approved Product Identity Policy

The approved target policy is:

- `product_code` is the permanent product identity and the key used for database updates.
- `product_code` is `TEXT`, not integer.
- `product_code` is the primary key.
- blank or duplicate product codes are rejected.
- one-character product codes are allowed because some customer products have no barcode and are retrieved by short shortcut codes.
- `Product_list.name` is required and must not be `NULL`, empty, or whitespace-only.
- product names must be unique using a trimmed, case-insensitive comparison.
- the database, CSV migration validator, and POS application must enforce the same product-name policy.

The database target combines separate constraints:

- `NOT NULL` prevents a null product name.
- `CHECK(trim(name) <> '')` prevents an empty or whitespace-only product name.
- the unique `uq_product_name_nocase` index prevents case-insensitive duplicate product names.
- CSV and application inputs must be trimmed before storage so leading or trailing whitespace cannot bypass the intended policy.

`product_code`, not `name`, remains the row identity. Product-name uniqueness is required because the current name-search interfaces use a displayed name to resolve a product.

### Migration Policy

Before changing `Product_list`, migration must validate the complete CSV:

- duplicate product codes are rejected case-insensitively.
- duplicate product names are rejected after trimming and case-insensitive normalization.
- blank product codes and blank product names are rejected.
- blank category becomes `Other`.
- blank unit becomes `Each`.
- blank supplier stays blank.
- blank cost price stays blank.
- blank last updated gets a migration timestamp.
- invalid or blank selling price rejects the row.

Migration is all-or-nothing. If any row is rejected, the validator must produce the rejection report and abort before deleting or inserting product rows. It must not silently retain the first duplicate and discard later occurrences.

Production catalog replacement must operate on a complete backup copy of the production database, replace only `Product_list` inside one transaction, preserve all other tables, and roll back on failure. A full fresh-database reset is not part of the product-only production workflow.

### Application Policy

- Product Add rejects a name already assigned to another product.
- Product Update permits the current product to retain its own name.
- Product Update rejects changing a name to one assigned to another product.
- `PRODUCT_CACHE` remains keyed by normalized `product_code`.
- name completers continue to display a stable unique list.

### Phase 2 Implementation Status

The schema creator, CSV migration validator, database audit, product-only replacement command, automated tests, and this administration guide implement the approved policy. The active production database is not changed by the repository update; it must still go through the separately controlled catalog-cleaning, working-copy replacement, audit, application test, deployment, and rollback phases.

## Receipt Counters

`receipt_counters` is created by the POS application at runtime in:

```text
Project/modules/db_operation/receipt_numbers.py
```

`Database_admin` does not preload receipt counters.

## Legacy Scripts

Old migration/drop helper scripts were moved to:

```text
legacy/
```

Fresh database setup should use corrected create scripts and `setup_fresh_database.py`, not legacy migration scripts.

For development only, to clear receipt test transactions and reset receipt numbering:

```bash
python tables/reset_receipt_history.py
```

This clears:

```text
receipts
receipt_items
receipt_payments
receipt_counters
```

It does not clear `Product_list`, `users`, or `cash_outflows`.

## Post-Setup POS Checks

After setup, run the POS application and check:

- POS starts without database errors.
- `PRODUCT_CACHE` loads.
- product code/barcode lookup works.
- the product audit reports no duplicate product names.
- the database rejects a case-insensitive duplicate product name.
- Product Menu blocks adding or renaming a product to a duplicate name.
- Product Menu allows a product to retain its own unique name while other fields are updated.
- paid receipts save.
- `receipt_items` save.
- receipt history retrieves.
- hold/cancel flows work.
- cash outflows save and report correctly.
