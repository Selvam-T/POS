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

def drop_cash_outflows():
    config = load_config()
    db_path = config.get('DB_PATH', '../db/Anumani.db')
    db_path = (Path(__file__).parent / db_path).resolve()

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute('DROP TABLE IF EXISTS cash_outflows;')
    conn.commit()
    print("Table dropped: cash_outflows")
    conn.close()

if __name__ == "__main__":
    drop_cash_outflows()