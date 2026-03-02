
import hashlib
import secrets
import string
from modules.db_operation.db import get_conn, now_iso

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
    """Normalize a user record into the `authenticated_user` shape used by UI.

    Args:
        user: dict returned by `authenticate_user` (may have 'user_id' and 'username').
        fallback_uid: optional integer used if `user['user_id']` is None.

    Returns:
        dict with keys: 'user_id', 'username', 'is_admin'.
    """
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
    """Return the recovery_email for a given user_id, or None if not set/found."""
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
    """Generate a secure temporary password, store its hash for the given user_id,
    update the `password_updated_at` timestamp, and return the plaintext password.

    Note: Password hashes are one-way; we store only the SHA-256 hash.
    """
    # Create a reasonably strong, URL-safe password using letters and digits
    alphabet = string.ascii_letters + string.digits
    temp_pwd = ''.join(secrets.choice(alphabet) for _ in range(int(length)))
    pwd_hash = hash_password(temp_pwd)

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password_hash = ?, password_updated_at = ? WHERE user_id = ?",
            (pwd_hash, now_iso(), user_id),
        )
        conn.commit()
        return temp_pwd
    finally:
        conn.close()


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
