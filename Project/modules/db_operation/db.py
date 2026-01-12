"""
Shared SQLite DB plumbing for the POS project.

Location: Project/modules/db_operation/db.py

Design goals:
- One place for DB path resolution
- One place for sqlite connection defaults + PRAGMAs
- Simple timestamp helper
- Transaction context manager for consistent BEGIN/COMMIT/ROLLBACK
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional


def _project_root() -> Path:
    """
    Resolve Project/ root based on this file location:
      Project/modules/db_operation/db.py -> parents[2] == Project/
    """
    return Path(__file__).resolve().parents[2]


def get_db_path() -> str:
    """
    Resolve the sqlite DB path using (highest priority first):
    1) env: POS_DB_PATH, DB_PATH
    2) config.py: DB_PATH (absolute or relative to Project/)
    3) common defaults (tries to find an existing file first)
       - Project/db/pos.db
       - POS/db/pos.db (Project/.. /db/pos.db)
       - Project/db.sqlite3
       - Project/pos.db
    """
    # 1) env vars
    env_path = os.environ.get("POS_DB_PATH") or os.environ.get("DB_PATH")
    if env_path:
        p = Path(env_path)
        if not p.is_absolute():
            p = _project_root() / p
        return str(p.resolve())

    # 2) config.py (Project/config.py)
    try:
        import config as app_config  # type: ignore
        cfg_path = getattr(app_config, "DB_PATH", None)
        if cfg_path:
            p = Path(str(cfg_path))
            if not p.is_absolute():
                p = _project_root() / p
            return str(p.resolve())
    except Exception:
        pass

    # 3) heuristic defaults (prefer existing files)
    proj = _project_root()
    candidates = [
        proj / "db" / "pos.db",
        proj.parent / "db" / "pos.db",
        proj / "db.sqlite3",
        proj / "pos.db",
    ]
    for c in candidates:
        if c.exists():
            return str(c.resolve())

    # if none exist, pick the first "reasonable" default (Project/db/pos.db)
    return str((proj / "db" / "pos.db").resolve())


def get_conn(db_path: Optional[str] = None, timeout: float = 5.0) -> sqlite3.Connection:
    """
    Open a sqlite3 connection with sensible defaults.
    - Enables foreign keys
    - Returns sqlite3.Row rows (dict-like)
    """
    path = db_path or get_db_path()
    conn = sqlite3.connect(path, timeout=timeout)
    conn.row_factory = sqlite3.Row

    # PRAGMAs
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        # Optional performance PRAGMAs (safe defaults)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
    except Exception:
        # Some environments may disallow certain PRAGMAs; ignore safely
        pass

    return conn


def now_iso() -> str:
    """Local timestamp in ISO-8601, seconds precision (e.g. 2026-01-12T15:03:10)."""
    return datetime.now().isoformat(timespec="seconds")


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """
    Transaction wrapper:
      with transaction(conn):
          ...
    Uses BEGIN IMMEDIATE for stronger write safety in a POS setting.
    """
    try:
        conn.execute("BEGIN IMMEDIATE;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
