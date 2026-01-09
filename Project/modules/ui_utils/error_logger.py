import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_PATH = os.path.join(BASE_DIR, 'log', 'error.log')

def log_error(msg):
    """Append error message with timestamp to error.log."""
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} - {msg}\n")
    except Exception:
        pass
