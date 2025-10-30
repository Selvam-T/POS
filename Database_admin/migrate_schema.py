"""
Database Schema Migration Script

Template for database schema changes (ALTER TABLE, rename columns, etc.)

Usage:
    python migrate_schema.py
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


def migrate_schema():
    """
    Perform schema migration
    
    Customize this function for your specific migration needs.
    """
    print("=" * 70)
    print("Database Schema Migration")
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
    print(f"Table: {table_name}")
    print("\n⚠ This is a template migration script.")
    print("Customize the migrate_schema() function for your specific needs.")
    print("\nExample migrations:")
    print("  - Rename columns")
    print("  - Add new columns")
    print("  - Change data types")
    print("  - Add constraints")
    
    # Example: Show current schema
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        print(f"\nCurrent schema:")
        print("-" * 70)
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"\n✗ Error: {e}")


if __name__ == "__main__":
    migrate_schema()
