
# Database Administration for Anumani POS

**Version:** 1.2
**Last Updated:** January 10, 2026


This folder contains all database administration scripts for the Anumani POS system.

**⚠️ These scripts are for DATABASE ADMINISTRATION ONLY**
- Creating database and tables (Product_list, receipts, receipt_items, receipt_payments)
- Schema migrations
- Bulk data imports
- Database verification

**NOT part of the POS application** (which only performs CRUD operations).

---


## 📁 File Structure

```
Database_admin/
├── config/
│   └── .env                    # Database configuration
├── data/
│   └── products.csv           # Product data for import
├── create_database.py         # Step 1: Create database file
├── create_product_list_table.py # Step 2: Create Product_list table
├── import_products.py         # Step 3: Import product data
├── verify_db.py              # Verify database
├── migrate_schema.py         # Schema migration template
├── create_cash_outflows_table.py # Create cash_outflows table
└── README.md                 # This file
```

---

## 🚀 Quick Start - Database Setup


### **Step 1: Create Database**
```bash
python create_database.py
```
Creates the `Anumani.db` file in the `../db/` folder.



### **Step 2: Create Tables**
#### 1. Product_list Table
```bash
python create_product_list_table.py
```
Schema:
| Column        | Type   | Nullable | Constraint      |
|-------------- |--------|----------|----------------|
| product_code  | TEXT   | NOT NULL | PRIMARY KEY (UNIQUE) |
| name          | TEXT   | NOT NULL |                |
| category      | TEXT   | NULL     |                |
| supplier      | TEXT   | NULL     |                |
| selling_price | REAL   | NOT NULL |                |
| cost_price    | REAL   | NULL     |                |
| unit          | TEXT   | NULL     |                |
| last_updated  | TEXT   | NULL     |                |

#### Hold Sales & View Hold Tables
#### 2. Cash Outflows Table
```bash
python create_cash_outflows_table.py
```
Creates:
##### cash_outflows
| Column        | Type     | Nullable | Constraint/Index                                  |
|--------------|----------|----------|---------------------------------------------------|
| outflow_id   | INTEGER  | NOT NULL | PRIMARY KEY AUTOINCREMENT                         |
| outflow_type | TEXT     | NOT NULL | CHECK(outflow_type IN ('REFUND_OUT','VENDOR_OUT'))|
| amount       | REAL     | NOT NULL | CHECK(amount > 0)                                 |
| created_at   | TEXT     | NOT NULL |                                                   |
| cashier_name | TEXT     | NOT NULL |                                                   |
| note         | TEXT     | NULL     | Free text (reason/details)                        |

Indexes:
- Index on created_at
- Index on outflow_type

**Purpose:**
- Tracks all cash leaving the drawer/account that is not reliably tied to receipts or paid sales items.
- REFUND_OUT: Refunds/voids (including manual item-level refunds not recorded against receipt_items)
- VENDOR_OUT: Vendor/supplier payments
- Keeps workflow simple and reporting accurate by not forcing links to receipts/products/vendors (details go in note).

**Reporting:**
- Net cash flow for a period:
	net = total paid sales (cash in) − total cash_outflows (refunds + vendor payments)

```bash
python create_receipt_tables.py
```
Creates:
##### 3. receipts
| Column         | Type     | Nullable | Constraint/Index                                  |
|---------------|----------|----------|---------------------------------------------------|
| receipt_id    | INTEGER  | NOT NULL | PRIMARY KEY AUTOINCREMENT                         |
| receipt_no    | TEXT     | NOT NULL | UNIQUE (format: YYYYMMDD-####, max ####=9999)     |
| customer_name | TEXT     | NULL     | Required for Hold; empty for normal paid          |
| cashier_name  | TEXT     | NOT NULL |                                                   |
| status        | TEXT     | NOT NULL | CHECK(status IN ('PAID','UNPAID','CANCELLED'))    |
| grand_total   | REAL     | NOT NULL |                                                   |
| created_at    | TEXT     | NOT NULL | Index optional                                    |
| paid_at       | TEXT     | NULL     | Index optional                                    |
| cancelled_at  | TEXT     | NULL     | Index optional                                    |
| note          | TEXT     | NULL     | Only UNPAID/CANCELLED used by policy              |

Indexes:
- UNIQUE index on receipt_no
- Optional: index on created_at, paid_at, status

##### 4. receipt_items
| Column        | Type     | Nullable | Constraint/Index                                  |
|--------------|----------|----------|---------------------------------------------------|
| item_id      | INTEGER  | NOT NULL | PRIMARY KEY AUTOINCREMENT                         |
| receipt_id   | INTEGER  | NOT NULL | Index, Foreign Key to receipts(receipt_id)        |
| line_no      | INTEGER  | NOT NULL | UNIQUE(receipt_id, line_no)                       |
| product_code | TEXT     | NOT NULL |                                                   |
| product_name | TEXT     | NOT NULL |                                                   |
| category     | TEXT     | NULL     |                                                   |
| qty          | REAL     | NOT NULL |                                                   |
| unit         | TEXT     | NOT NULL |                                                   |
| unit_price   | REAL     | NOT NULL |                                                   |
| line_total   | REAL     | NOT NULL |                                                   |

Indexes:
- UNIQUE(receipt_id, line_no)
- Index on receipt_id

##### 5. receipt_payments
| Column        | Type     | Nullable | Constraint/Index                                  |
|--------------|----------|----------|---------------------------------------------------|
| payment_id   | INTEGER  | NOT NULL | PRIMARY KEY AUTOINCREMENT                         |
| receipt_id   | INTEGER  | NOT NULL | Index, Foreign Key to receipts(receipt_id)        |
| payment_type | TEXT     | NOT NULL | CHECK(payment_type IN ('NETS','CASH','PAYNOW','OTHER')) |
| amount       | REAL     | NOT NULL | CHECK(amount > 0)                                 |
| created_at   | TEXT     | NOT NULL |                                                   |

Indexes:
- Index on receipt_id


---

## How to Query Tables and Columns from Command Line

To list all tables in your database, use:

```bash
sqlite3 "C:\Users\SELVAM\OneDrive\Desktop\POS\db\Anumani.db" "SELECT name FROM sqlite_master WHERE type='table';"
```

To list all columns in a specific table (e.g., receipts), use:

```bash
sqlite3 "C:\Users\SELVAM\OneDrive\Desktop\POS\db\Anumani.db" "PRAGMA table_info(receipts);"
```

Replace receipts with any table name to see its columns.

---


## What is sqlite_sequence?

sqlite_sequence is an internal table automatically created by SQLite when you use AUTOINCREMENT on any INTEGER PRIMARY KEY column. It keeps track of the last used value for AUTOINCREMENT fields in your tables (like receipt_id, item_id, payment_id). You do not need to manage or modify it; SQLite uses it to ensure unique values for those columns.

### Columns in sqlite_sequence

| Column | Type | Description |
|--------|------|-------------|
| name   | TEXT | The name of the table with an AUTOINCREMENT column |
| seq    | INTEGER | The last used AUTOINCREMENT value for that table |

If you query PRAGMA table_info(sqlite_sequence); you will see:
| cid | name | type | notnull | dflt_value | pk |
|-----|------|------|---------|------------|----|
| 0   | name |      | 0       |            | 0  |
| 1   | seq  |      | 0       |            | 0  |

If sqlite_sequence is empty, it means no rows have been inserted into any AUTOINCREMENT table yet, so SQLite has not recorded any values. The table will populate automatically as you add rows to tables with AUTOINCREMENT columns.


### **Step 3: Import Products**

First, place your `products.csv` file in the `data/` folder with this format:
```csv
product_code,name,category,supplier,selling_price,cost_price,unit,last_updated
PROD001,Product Name,Category,Supplier,99.99,50.00,kg,2025-01-01 00:00:00
```


All string fields (product_code, name, category, supplier, unit) are automatically normalized to Camel Case during import. Numeric fields (selling_price, cost_price) are not case sensitive and are imported as-is.

Then run:
```bash
python import_products.py
```

To overwrite existing products:
```bash
python import_products.py --overwrite
```

---


## 🔍 Verification

Check database status:
```bash
python verify_db.py
```

Shows:
- Database schema
- Total record count
- Sample data

---


## 🔄 Schema Migration

For schema changes (rename columns, add columns, etc.):

1. Edit `migrate_schema.py` with your migration logic
2. Run: `python migrate_schema.py`

⚠️ **Always backup your database before migrations!**

---


## ⚙️ Configuration

All settings are in `config/.env`:

```properties
DB_PATH=../db/Anumani.db          # Database location
TABLE_NAME=Product_list           # Main table name
CSV_FILE_PATH=data/products.csv   # CSV import file
```

---


## 📋 CSV Format Requirements


Your `products.csv` must have these columns. Only `product_code` is unique (primary key); all other fields can have duplicates. String fields are normalized to Camel Case on import:

| Column | Required | Type | Example |
|--------|----------|------|---------|
| product_code | ✅ Yes | TEXT | PROD001 |
| name | ✅ Yes | TEXT | Apple |
| selling_price | ✅ Yes | REAL | 99.99 |
| category | ❌ No | TEXT | Fruits |
| supplier | ❌ No | TEXT | ABC Ltd |
| cost_price | ❌ No | REAL | 50.00 |
| unit | ❌ No | TEXT | kg |
| last_updated | ❌ No | TEXT | 2025-01-01 00:00:00 |

---


## 🎯 Usage Notes

### **First-Time Setup**
1. Run `create_database.py`
2. Run `create_product_list_table.py`
3. Place `products.csv` in `data/` folder
4. Run `import_products.py`
5. Verify with `verify_db.py`

### **Adding More Products**
1. Update `data/products.csv`
2. Run `import_products.py` (skips existing)
3. Or `import_products.py --overwrite` (updates existing)

### **Schema Changes**
1. **Backup database first!**
2. Edit `migrate_schema.py`
3. Run migration
4. Verify with `verify_db.py`

---

## 🔗 Related

- **POS Application**: `../Project/` - Uses this database (CRUD only)
- **Database File**: `../db/Anumani.db` - Shared database
- **Exports**: `../exports/` - Export location (if needed)

---

## ⚠️ Important

- ✅ This folder = Database administration (DDL)
- ✅ POS application = Data operations (DML/CRUD)
- ✅ Always backup before migrations
- ✅ Never run admin scripts from POS application

---

# Database Admin Notes

## Product Name Uniqueness Constraint

The `Product_list` table enforces uniqueness of product names at the database level using a unique index with case-insensitive collation. This ensures that no two products can have the same name, regardless of letter case.

### SQL Schema

The relevant constraint is present in the live database and can be verified with:

```sql
PRAGMA index_list('Product_list');
PRAGMA index_info('uq_product_name_nocase');
```

The unique index is:

```sql
CREATE UNIQUE INDEX uq_product_name_nocase ON Product_list(name COLLATE NOCASE);
```

This means that attempts to insert or update a product with a name that already exists (case-insensitive) will result in a database error (sqlite3.IntegrityError).

### Application Behavior

- When adding or updating a product, the application checks for this constraint and provides a clear error message if a duplicate name is detected.
- The error message is displayed to the user via the status label in the UI.

### Example

Attempting to add two products with names 'Apple' and 'apple' will fail on the second insert or update, as the names are considered identical by the database.

---

For more details, see the `Product_list` table schema and the application logic in `modules/db_operation/database.py`.

---

**Version:** 1.2  
**Last Updated:** January 10, 2026
