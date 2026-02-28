"""
Create Tables Script for Anumani POS

This script creates the database schema (tables).
Run this AFTER create_database.py.

Schema:
    Table: Product_list
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

Usage:
    python create_tables.py
"""
import sqlite3
import os
from pathlib import Path


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


def create_tables():
    """Create database tables"""
    print("=" * 70)
    print("Anumani POS - Table Creation")
    print("=" * 70)
    
    config = load_config()
    db_path = config.get('DB_PATH', '../db/Anumani.db')
    table_name = config.get('TABLE_NAME', 'Product_list')
    
    # Make path absolute
    script_dir = Path(__file__).parent
    db_path = (script_dir / db_path).resolve()
    
    # Check if database exists
    if not db_path.exists():
        print(f"\nDatabase not found: {db_path}")
        print("Run create_database.py first!")
        return
    
    print(f"\nDatabase: {db_path}")
    print(f"Table: {table_name}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if table already exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if cursor.fetchone():
            print(f"\n⚠ Table '{table_name}' already exists")
            response = input("Drop and recreate? (y/n): ").strip().lower()
            if response != 'y':
                print("Table creation cancelled.")
                conn.close()
                return
            cursor.execute(f"DROP TABLE {table_name}")
            print(f"✓ Dropped existing table '{table_name}'")
        
        # Create Product_list table
        create_table_sql = f"""
        CREATE TABLE {table_name} (
            product_code TEXT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL,
            category TEXT,
            supplier TEXT,
            selling_price REAL NOT NULL,
            cost_price REAL,
            unit TEXT,
            last_updated TEXT
        )
        """
        
        cursor.execute(create_table_sql)
        conn.commit()
        
        print(f"\n✓ Table '{table_name}' created successfully")
        
        # Show schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        print(f"\nSchema for '{table_name}':")
        print("-" * 70)
        print(f"{'Column':<20} {'Type':<10} {'Nullable':<10} {'Constraint'}")
        print("-" * 70)
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            not_null = 'NOT NULL' if col[3] else 'NULL'
            pk = 'PRIMARY KEY' if col[5] else ''
            print(f"{col_name:<20} {col_type:<10} {not_null:<10} {pk}")
        
        conn.close()
        
        print("\n" + "=" * 70)
        print("Next step: Run import_products.py to import data")
        print("=" * 70)
        
    except sqlite3.Error as e:
        print(f"\n✗ Error creating table: {e}")


if __name__ == "__main__":
    create_tables()
