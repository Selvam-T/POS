"""
Create Database Script for Anumani POS

This script creates the SQLite database file.
Run this ONCE during initial setup.

Usage:
    python create_database.py
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


def create_database():
    """Create the database file"""
    print("=" * 70)
    print("Anumani POS - Database Creation")
    print("=" * 70)
    
    config = load_config()
    db_path = config.get('DB_PATH', '../db/Anumani.db')
    
    # Make path absolute
    script_dir = Path(__file__).parent
    db_path = (script_dir / db_path).resolve()
    
    # Create db directory if it doesn't exist
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if database already exists
    if db_path.exists():
        print(f"\n⚠ Database already exists: {db_path}")
        response = input("Overwrite? (y/n): ").strip().lower()
        if response != 'y':
            print("Database creation cancelled.")
            return
        db_path.unlink()
        print("✓ Deleted existing database")
    
    # Create database
    try:
        conn = sqlite3.connect(str(db_path))
        conn.close()
        print(f"\n✓ Database created: {db_path}")
        print(f"✓ Size: {db_path.stat().st_size} bytes")
        print("\n" + "=" * 70)
        print("Next step: Run create_tables.py to create tables")
        print("=" * 70)
    except Exception as e:
        print(f"\n✗ Error creating database: {e}")


if __name__ == "__main__":
    create_database()
