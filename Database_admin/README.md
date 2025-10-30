# Database Administration for Anumani POS

This folder contains all database administration scripts for the Anumani POS system.

**⚠️ These scripts are for DATABASE ADMINISTRATION ONLY**
- Creating database and tables
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
├── create_tables.py           # Step 2: Create tables
├── import_products.py         # Step 3: Import product data
├── verify_db.py              # Verify database
├── migrate_schema.py         # Schema migration template
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
```bash
python create_tables.py
```
Creates the `Product_list` table with the following schema:

```
┌──────────────────┬──────────┬──────────┬─────────────────┐
│ Column           │ Type     │ Nullable │ Constraint      │
├──────────────────┼──────────┼──────────┼─────────────────┤
│ product_code     │ TEXT     │ NOT NULL │ PRIMARY KEY     │
│ name             │ TEXT     │ NOT NULL │                 │
│ category         │ TEXT     │ NULL     │                 │
│ supplier         │ TEXT     │ NULL     │                 │
│ selling_price    │ REAL     │ NOT NULL │                 │
│ cost_price       │ REAL     │ NULL     │                 │
│ unit             │ TEXT     │ NULL     │                 │
│ last_updated     │ TEXT     │ NULL     │                 │
└──────────────────┴──────────┴──────────┴─────────────────┘
```

### **Step 3: Import Products**

First, place your `products.csv` file in the `data/` folder with this format:
```csv
product_code,name,category,supplier,selling_price,cost_price,unit,last_updated
PROD001,Product Name,Category,Supplier,99.99,50.00,kg,2025-01-01 00:00:00
```

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

Your `products.csv` must have these columns:

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
2. Run `create_tables.py`
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

**Version:** 1.0  
**Last Updated:** October 30, 2025
