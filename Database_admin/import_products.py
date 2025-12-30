"""
Import Products from CSV to Database

This script imports product data from CSV file into the Product_list table.
Run this AFTER create_tables.py.

CSV Format:
    product_code,name,category,supplier,selling_price,cost_price,unit,last_updated

Usage:
    python import_products.py
    python import_products.py --overwrite  (to overwrite existing records)
"""

import sqlite3
import csv
import os
import sys
from pathlib import Path
from datetime import datetime

# Camel case normalization (copied from export_products.py)
def to_camel_case(text: str) -> str:
    if text is None:
        return ''
    s = str(text).strip()
    if not s:
        return ''
    for sep in ['\t', '\n', '_', '-']:
        s = s.replace(sep, ' ')
    parts = [p for p in s.split(' ') if p]
    return ' '.join(w[:1].upper() + w[1:].lower() if w else '' for w in parts)


def load_config():
    """Load configuration from .env file"""
    config = {}
    env_path = Path(__file__).parent / 'config' / '.env'
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
    
    return config


def import_products(overwrite=False):
    """Import products from CSV file"""
    print("=" * 70)
    print("Anumani POS - Product Import")
    print("=" * 70)
    
    config = load_config()
    db_path = config.get('DB_PATH', '../db/Anumani.db')
    table_name = config.get('TABLE_NAME', 'Product_list')
    csv_path = config.get('CSV_FILE_PATH', 'data/products.csv')
    
    # Make paths absolute
    script_dir = Path(__file__).parent
    db_path = (script_dir / db_path).resolve()
    csv_path = (script_dir / csv_path).resolve()
    
    # Check if database exists
    if not db_path.exists():
        print(f"\n✗ Database not found: {db_path}")
        print("Run create_database.py first!")
        return
    
    # Check if CSV exists
    if not csv_path.exists():
        print(f"\n✗ CSV file not found: {csv_path}")
        print("Please place your products.csv file in the data/ folder")
        return
    
    print(f"\nDatabase: {db_path}")
    print(f"CSV File: {csv_path}")
    print(f"Mode: {'Overwrite existing' if overwrite else 'Skip existing'}")
    
    successful = 0
    skipped = 0
    errors = []
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            print(f"\n✗ Table '{table_name}' not found")
            print("Run create_tables.py first!")
            conn.close()
            return
        
        print("\n" + "-" * 70)
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Get required fields and normalize to camel case for strings
                    product_code = to_camel_case(row.get('product_code', '').strip())
                    name = to_camel_case(row.get('name', '').strip())
                    selling_price_str = row.get('selling_price', '').strip()

                    # Validate required fields
                    if not product_code:
                        errors.append(f"Row {row_num}: product_code is empty")
                        continue
                    if not name:
                        errors.append(f"Row {row_num}: name is empty")
                        continue
                    if not selling_price_str:
                        errors.append(f"Row {row_num}: selling_price is empty")
                        continue

                    try:
                        selling_price = float(selling_price_str)
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid selling_price '{selling_price_str}'")
                        continue

                    # Get optional fields and normalize to camel case for strings
                    category = to_camel_case(row.get('category', '').strip()) or None
                    supplier = to_camel_case(row.get('supplier', '').strip()) or None
                    cost_price_str = row.get('cost_price', '').strip()
                    cost_price = float(cost_price_str) if cost_price_str else None
                    unit = to_camel_case(row.get('unit', '').strip()) or None
                    last_updated = row.get('last_updated', '').strip() or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Check if product exists
                    cursor.execute(f"SELECT 1 FROM {table_name} WHERE product_code = ?", (product_code,))
                    exists = cursor.fetchone()
                    
                    if exists:
                        if overwrite:
                            # Update existing
                            cursor.execute(f"""
                                UPDATE {table_name}
                                SET name = ?, category = ?, supplier = ?, selling_price = ?,
                                    cost_price = ?, unit = ?, last_updated = ?
                                WHERE product_code = ?
                            """, (name, category, supplier, selling_price, cost_price, unit, last_updated, product_code))
                            successful += 1
                            print(f"↻ Updated: {product_code} - {name}")
                        else:
                            # Skip existing
                            skipped += 1
                            print(f"⊗ Skipped: {product_code} - {name}")
                    else:
                        # Insert new
                        cursor.execute(f"""
                            INSERT INTO {table_name}
                            (product_code, name, category, supplier, selling_price, cost_price, unit, last_updated)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (product_code, name, category, supplier, selling_price, cost_price, unit, last_updated))
                        successful += 1
                        print(f"✓ Imported: {product_code} - {name}")
                
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
        
        conn.commit()
        
        print("-" * 70)
        print(f"\nImport Summary:")
        print(f"  Successful: {successful}")
        print(f"  Skipped: {skipped}")
        print(f"  Errors: {len(errors)}")
        
        if errors:
            print(f"\nErrors (first 10):")
            for error in errors[:10]:
                print(f"  - {error}")
        
        # Show total count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total = cursor.fetchone()[0]
        print(f"\nTotal products in database: {total}")
        
        conn.close()
        
        print("\n" + "=" * 70)
        print("Import complete!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")


if __name__ == "__main__":
    overwrite = '--overwrite' in sys.argv
    import_products(overwrite)
