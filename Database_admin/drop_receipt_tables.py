import sqlite3
from pathlib import Path

def load_config():
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

def drop_receipt_tables():
    config = load_config()
    db_path = config.get('DB_PATH', '../db/Anumani.db')
    script_dir = Path(__file__).parent
    db_path = (script_dir / db_path).resolve()
    if not db_path.exists():
        print(f"\n✗ Database not found: {db_path}")
        return
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS receipt_payments;')
    cursor.execute('DROP TABLE IF EXISTS receipt_items;')
    cursor.execute('DROP TABLE IF EXISTS receipts;')
    conn.commit()
    print("✓ Tables dropped: receipts, receipt_items, receipt_payments")
    conn.close()

if __name__ == "__main__":
    drop_receipt_tables()