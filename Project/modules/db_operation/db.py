"""Shared SQLite DB helpers."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional


def _project_root() -> Path:
    """Return the Project root path."""
    return Path(__file__).resolve().parents[2]


def get_db_path() -> str:
    """Resolve SQLite DB path from env, config, then defaults."""
    env_path = os.environ.get("POS_DB_PATH") or os.environ.get("DB_PATH")
    if env_path:
        p = Path(env_path)
        if not p.is_absolute():
            p = _project_root() / p
        return str(p.resolve())

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

    return str((proj / "db" / "pos.db").resolve())


def get_conn(db_path: Optional[str] = None, timeout: float = 5.0) -> sqlite3.Connection:
    """Open a sqlite3 connection with default PRAGMAs."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(path, timeout=timeout)
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
    except Exception:
        pass

    return conn


def now_iso() -> str:
    """Return local ISO timestamp with seconds precision."""
    return datetime.now().isoformat(timespec="seconds")


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Context manager for BEGIN IMMEDIATE / COMMIT / ROLLBACK."""
    try:
        conn.execute("BEGIN IMMEDIATE;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
