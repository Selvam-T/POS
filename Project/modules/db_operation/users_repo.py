
import hashlib
import secrets
import string
from modules.db_operation.db import get_conn, now_iso

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def _store_password_hash(user_id: int, pwd_hash: str) -> None:
    """Store password hash and update timestamp."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password_hash = ?, password_updated_at = ? WHERE user_id = ?",
            (pwd_hash, now_iso(), user_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_password(user_id: int, new_password: str) -> None:
    """Set a new password for `user_id` (hash + timestamp)."""
    pwd_hash = hash_password(new_password)
    _store_password_hash(user_id, pwd_hash)


def verify_password(user_id: int, password: str, require_active: bool = False) -> bool:
    """Return True if plaintext password matches stored hash (optional active check)."""
    user = get_user_by_id(user_id)
    if not user:
        return False
    if require_active and not user.get('is_active'):
        return False
    return bool(user.get('password_hash') == hash_password(password))

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

def get_user_id_by_username(username: str) -> int | None:
    """Fetch user_id by username. Returns the integer user_id or None if not found."""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            return int(row[0])
        return None
    finally:
        conn.close()


def get_username_by_id(user_id: int) -> str | None:
    """Fetch username by user_id. Returns the username or None if not found."""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row[0] is not None:
            return str(row[0])
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


def authenticate_user(username: str, password: str) -> dict | None:
    """Higher-level authentication API used by UI code.

    Returns a normalized user dict (or None). Keeps DB/auth logic centralized.
    """
    # Keep behavior identical to validate_user_credentials but present a
    # clean dict without exposing password_hash to callers.
    user = validate_user_credentials(username, password)
    if not user:
        return None
    return {
        'user_id': int(user.get('user_id')) if user.get('user_id') is not None else None,
        'username': str(user.get('username') or username),
        'is_active': user.get('is_active', False),
    }


def build_authenticated_user(user: dict, fallback_uid=None) -> dict:
    """Normalize user dict for UI; returns `user_id`, `username`, `is_admin`."""
    uid = user.get('user_id')
    if uid is None:
        uid = fallback_uid

    username = str(user.get('username') or '').strip()
    return {
        'user_id': int(uid) if uid is not None else None,
        'username': username,
        'is_admin': username.lower() == 'admin',
    }


def get_recovery_email(user_id: int) -> str | None:
    """Return recovery email for `user_id`, or None."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT recovery_email FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            return row[0]
        return None
    finally:
        conn.close()

def generate_temporary_password_for_user(user_id: int, length: int = 12) -> str:
    """Generate a temporary password, store its hash, update timestamp, and return it."""
    # Create a random password using letters and digits
    alphabet = string.ascii_letters + string.digits
    temp_pwd = ''.join(secrets.choice(alphabet) for _ in range(int(length)))
    pwd_hash = hash_password(temp_pwd)

    # Use centralized helper to persist the password hash and timestamp
    _store_password_hash(user_id, pwd_hash)
    return temp_pwd

def get_user_by_id(user_id: int):
    """Fetch user record by user_id. Returns dict or None."""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, password_hash, is_active FROM users WHERE user_id = ?", (user_id,))
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
