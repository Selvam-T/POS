
import hashlib
from modules.db_operation.db import get_conn

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_user_by_username(username: str):
    """Fetch user record by username. Returns dict or None."""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, password_hash, is_active FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            return {
                'user_id': row[0],
                'username': row[1],
                'password_hash': row[2],
                'is_active': row[3],
            }
        return None
    finally:
        conn.close()

def validate_user_credentials(username: str, password: str) -> dict:
    """Validate username and password. Returns user dict if valid, else None."""
    user = get_user_by_username(username)
    if not user or not user['is_active']:
        return None
    if user['password_hash'] == hash_password(password):
        return user
    return None
