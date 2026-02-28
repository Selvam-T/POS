"""
Create Users Table Script for Anumani POS

Creates the 'users' table in the SQLite database.

Run this AFTER create_database.py.

Usage:
    python create_users_table.py
"""
import sqlite3
from pathlib import Path


def load_config():
    config = {}
    env_path = Path(__file__).parent / "config" / ".env"
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


def create_users_table(drop_existing=True):
    config = load_config()
    db_path = config.get("DB_PATH", "../db/Anumani.db")
    script_dir = Path(__file__).parent
    db_path = (script_dir / db_path).resolve()

    if not db_path.exists():
        print(f"\nDatabase not found: {db_path}")
        print("Run create_database.py first!")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    if drop_existing:
        cursor.execute("DROP TABLE IF EXISTS users;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id             INTEGER PRIMARY KEY AUTOINCREMENT,
            username            TEXT    NOT NULL UNIQUE,
            password_hash       TEXT    NOT NULL,
            password_updated_at TEXT    NOT NULL,
            recovery_email      TEXT,
            is_active           INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1))
        );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")

    conn.commit()
    if drop_existing:
        print("Table dropped and recreated: users")
    else:
        print("Table ensured: users")
    conn.close()


if __name__ == "__main__":
    create_users_table(drop_existing=True)