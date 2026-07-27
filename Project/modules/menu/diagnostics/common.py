"""Shared primitives for read-only POS diagnostic checks."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


def timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def quote_identifier(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def read_only_connection(database_path: str) -> sqlite3.Connection:
    """Open an SQLite connection that cannot write to the database."""
    uri = f"{Path(database_path).resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, timeout=5.0, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
