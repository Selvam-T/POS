# Database Administration

This folder contains company-agnostic scripts used to create a fresh POS SQLite database and import product data.

## Folder Structure

```text
Database_admin/
  config/
    .env
  data/
    products.csv
  database/
    create_database.py
    reset_database.py
  tables/
    create_product_list_table.py
    create_user_table.py
    create_receipt_tables.py
    create_cash_outflows_table.py
  users/
    initialize_default_users.py
  products/
    import_products.py
    export_products.py
  migration/
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
Database_admin/data/products.csv
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
4. Create `Product_list`.
5. Create `receipts`, `receipt_items`, and `receipt_payments`.
6. Create `cash_outflows`.
7. Stage `data/products.csv`.
8. Validate and clean staged products.
9. Migrate valid products into `Product_list`.
10. Run database audit.

If validation fails, the process stops and writes reports under `data/`.

```text
data/staged_products.csv
data/cleaned_products.csv
data/rejected_products.csv
data/product_validation_summary.txt
```

Fix `data/products.csv`, then rerun `setup_fresh_database.py`.

## Product Rules

Database rules:

- `product_code` is `TEXT`, not integer.
- `product_code` is the primary key.
- blank `product_code` is rejected.
- duplicate `product_code` is rejected.
- duplicate product names are allowed in the database.
- `Product_list.name` must not have a unique index.

Migration cleaning:

- blank category becomes `Other`.
- blank unit becomes `Each`.
- blank supplier stays blank.
- blank cost price stays blank.
- blank last updated gets a migration timestamp.
- invalid or blank selling price rejects the row.

Application rule:

- the POS application may still block users from creating new duplicate product names.
- existing migrated duplicate names are not removed by the database.

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

## Post-Setup POS Checks

After setup, run the POS application and check:

- POS starts without database errors.
- `PRODUCT_CACHE` loads.
- product code/barcode lookup works.
- duplicate product names do not break cache loading.
- Product Menu still blocks new duplicate names through application validation.
- paid receipts save.
- `receipt_items` save.
- receipt history retrieves.
- hold/cancel flows work.
- cash outflows save and report correctly.
