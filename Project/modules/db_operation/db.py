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


def _resolve_db_file(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = _project_root() / path
    return path.resolve()


def _require_db_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(
            f"Database file not found: {path}. "
            "Set POS_DB_PATH only when an explicit database override is required."
        )
    return str(path)


def get_db_path() -> str:
    """Return the configured external database path, which must already exist."""
    env_path = os.environ.get("POS_DB_PATH")
    if env_path:
        return _require_db_file(_resolve_db_file(env_path))

    try:
        import config as app_config  # type: ignore
    except Exception as exc:
        raise RuntimeError("Unable to import config.DB_PATH") from exc

    cfg_path = getattr(app_config, "DB_PATH", None)
    if not cfg_path:
        raise RuntimeError("config.DB_PATH is not configured")
    return _require_db_file(_resolve_db_file(str(cfg_path)))


def get_conn(db_path: Optional[str] = None, timeout: float = 5.0) -> sqlite3.Connection:
    """Open a sqlite3 connection with default PRAGMAs."""
    path = (
        _require_db_file(_resolve_db_file(str(db_path)))
        if db_path is not None
        else get_db_path()
    )
    db_uri = f"{Path(path).as_uri()}?mode=rw"
    conn = sqlite3.connect(db_uri, timeout=timeout, uri=True)
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
