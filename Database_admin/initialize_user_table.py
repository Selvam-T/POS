"""
Initialize users table with default admin and staff accounts.
Run AFTER create_users_table.py
"""

import sqlite3
from pathlib import Path
import hashlib  # simple hash (replace with bcrypt in production)

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

def init_default_users():
    config = load_config()
    db_path = config.get("DB_PATH", "../db/Anumani.db")
    db_path = (Path(__file__).parent / db_path).resolve()

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Simple SHA-256 hash — REPLACE WITH bcrypt/argon2 IN PRODUCTION
    def simple_hash(pw): 
        return hashlib.sha256(pw.encode()).hexdigest()

    users = [
        ('admin', 'admin123', 'thiagarajan.selvam@gmail.com'),
        ('staff', 'staff123', None)
    ]

    for username, password, email in users:
        password_hash = simple_hash(password)
        cursor.execute("""
            INSERT OR IGNORE INTO users 
            (username, password_hash, password_updated_at, recovery_email, is_active)
            VALUES (?, ?, datetime('now'), ?, 1)
        """, (username, password_hash, email))

    conn.commit()
    print("Default users initialized (or already exist): admin, staff")
    conn.close()

if __name__ == "__main__":
    init_default_users()