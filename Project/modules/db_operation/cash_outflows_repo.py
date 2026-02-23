"""SQL helpers for `cash_outflows`."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from .db import get_conn, now_iso, transaction


TABLE = "cash_outflows"
ALLOWED_OUTFLOW_TYPES = {"REFUND_OUT", "VENDOR_OUT"}


def ensure_table(*, conn: Optional[sqlite3.Connection] = None) -> None:
    """Create table if missing."""
    sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE} (
      outflow_id INTEGER PRIMARY KEY AUTOINCREMENT,
      outflow_type TEXT NOT NULL,
      amount REAL NOT NULL,
      created_at TEXT NOT NULL,
      cashier_name TEXT,
      note TEXT
    );
    """

    own = conn is None
    c = conn or get_conn()
    try:
        with transaction(c):
            c.execute(sql)
    finally:
        if own:
            c.close()


def add_outflow(
    *,
    outflow_type: str,
    amount: float,
    cashier_name: str = "",
    note: str = "",
    created_at: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    """Insert one outflow row and return its id."""
    typ = str(outflow_type or "").strip().upper()
    if not typ:
        raise ValueError("outflow_type is required")
    if typ not in ALLOWED_OUTFLOW_TYPES:
        raise ValueError(f"Unsupported outflow_type: {typ}")

    amt = float(amount)
    if amt <= 0:
        raise ValueError("amount must be greater than 0")

    sql = f"""
    INSERT INTO {TABLE}
      (outflow_type, amount, created_at, cashier_name, note)
    VALUES
      (?, ?, ?, ?, ?)
    """

    own = conn is None
    c = conn or get_conn()
    try:
        with transaction(c):
            cur = c.execute(
                sql,
                (
                    typ,
                    amt,
                    created_at or now_iso(),
                    str(cashier_name or "").strip(),
                    str(note or "").strip(),
                ),
            )
            return int(cur.lastrowid)
    finally:
        if own:
            c.close()


def list_outflows(
    *,
    date_prefix: Optional[str] = None,
    outflow_type: Optional[str] = None,
    limit: int = 200,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Return outflow rows (newest first)."""
    where = []
    params = []

    if date_prefix:
        where.append("created_at LIKE ?")
        params.append(f"{date_prefix}%")

    if outflow_type:
        where.append("outflow_type = ?")
        params.append(str(outflow_type).strip().upper())

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    sql = f"SELECT * FROM {TABLE}{where_sql} ORDER BY created_at DESC LIMIT ?"
    params.append(int(limit))

    own = conn is None
    c = conn or get_conn()
    try:
        rows = c.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()
