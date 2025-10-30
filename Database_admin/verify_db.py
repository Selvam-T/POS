"""
Verify Database Script

Quick verification of database schema and data.

Usage:
    python verify_db.py
"""
import sqlite3
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


def verify_database():
    """Verify database structure and content"""
    print("=" * 70)
    print("Database Verification")
    print("=" * 70)
    
    config = load_config()
    db_path = config.get('DB_PATH', '../db/Anumani.db')
    table_name = config.get('TABLE_NAME', 'Product_list')
    
    # Make path absolute
    script_dir = Path(__file__).parent
    db_path = (script_dir / db_path).resolve()
    
    if not db_path.exists():
        print(f"\n✗ Database not found: {db_path}")
        return
    
    print(f"\nDatabase: {db_path}")
    print(f"Size: {db_path.stat().st_size:,} bytes")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Show schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        if not columns:
            print(f"\n✗ Table '{table_name}' not found")
            conn.close()
            return
        
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
        
        # Show data
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        
        print(f"\nTotal Records: {count}")
        
        if count > 0:
            print(f"\nSample Data (first 5 records):")
            print("-" * 70)
            cursor.execute(f"SELECT product_code, name, selling_price FROM {table_name} LIMIT 5")
            for row in cursor.fetchall():
                print(f"  {row[0]}: {row[1]} - ${row[2]:.2f}")
        
        conn.close()
        
        print("\n" + "=" * 70)
        print("✓ Database verification complete")
        print("=" * 70)
        
    except sqlite3.Error as e:
        print(f"\n✗ Error: {e}")


if __name__ == "__main__":
    verify_database()
