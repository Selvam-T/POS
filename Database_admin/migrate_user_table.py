import sqlite3
from pathlib import Path

def load_config():
    """Reads the database path from the .env file."""
    config = {}
    env_path = Path(__file__).parent / "config" / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
    return config

def migrate_must_change_password():
    # 1. Setup Database Path
    config = load_config()
    db_path_raw = config.get("DB_PATH", "../db/Anumani.db")
    script_dir = Path(__file__).parent
    db_path = (script_dir / db_path_raw).resolve()

    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 2. Check if the column already exists to prevent errors
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]

        if "must_change_password" not in columns:
            print("Migration: Adding 'must_change_password' column...")
            
            # 3. Add the column. 
            # DEFAULT 0 automatically initializes all existing rows to 0.
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0
            """)
            
            conn.commit()
            print("Successfully added 'must_change_password' and initialized existing rows to 0.")
        else:
            print("Skip: 'must_change_password' column already exists.")

    except sqlite3.Error as e:
        print(f"Database error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_must_change_password()