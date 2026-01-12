"""
Cash movements repository (SQL only).

Location: Project/modules/db_operation/cash_movements_repo.py

Design per your POS decision:
- cash_movements is independent of receipts
- tracks cash in/out (refunds, vendor payouts, misc adjustments)

Suggested table (you can migrate to your exact schema later):
  cash_movements(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movement_type TEXT NOT NULL,    -- IN | OUT
    amount REAL NOT NULL,
    reason TEXT,
    related_receipt_no TEXT,        -- optional
    created_at TEXT NOT NULL,
    meta_json TEXT                  -- optional JSON blob
  )
"""

import json
import sqlite3
from typing import Any, Dict, List, Optional

from .db import get_conn, now_iso, transaction


TABLE = "cash_movements"


def ensure_table(*, conn: Optional[sqlite3.Connection] = None) -> None:
    """
    Call once during app startup / migration.
    Safe: CREATE TABLE IF NOT EXISTS.
    """
    sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE} (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      movement_type TEXT NOT NULL,
      amount REAL NOT NULL,
      reason TEXT,
      related_receipt_no TEXT,
      created_at TEXT NOT NULL,
      meta_json TEXT
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


def add_movement(
    *,
    movement_type: str,   # "IN" or "OUT"
    amount: float,
    reason: str = "",
    related_receipt_no: str = "",
    meta: Optional[Dict[str, Any]] = None,
    created_at: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    """
    Returns inserted row id.
    """
    sql = f"""
    INSERT INTO {TABLE}
      (movement_type, amount, reason, related_receipt_no, created_at, meta_json)
    VALUES
      (?, ?, ?, ?, ?, ?)
    """
    meta_json = json.dumps(meta or {}, ensure_ascii=False) if meta is not None else None

    own = conn is None
    c = conn or get_conn()
    try:
        with transaction(c):
            cur = c.execute(
                sql,
                (
                    movement_type,
                    float(amount),
                    reason,
                    related_receipt_no or None,
                    created_at or now_iso(),
                    meta_json,
                ),
            )
            return int(cur.lastrowid)
    finally:
        if own:
            c.close()


def list_movements(
    *,
    date_prefix: Optional[str] = None,
    movement_type: Optional[str] = None,
    limit: int = 200,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """
    Simple query helper.
    - date_prefix: '2026-01-12' to filter created_at LIKE '2026-01-12%'
    """
    where = []
    params = []

    if date_prefix:
        where.append("created_at LIKE ?")
        params.append(f"{date_prefix}%")

    if movement_type:
        where.append("movement_type = ?")
        params.append(movement_type)

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
