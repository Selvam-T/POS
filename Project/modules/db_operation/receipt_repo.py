"""Receipt read-only repository (SQL only)."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from .db import get_conn


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    try:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(r["name"]) for r in rows}
    except Exception:
        return set()


def _first_existing(columns: set[str], *candidates: str) -> Optional[str]:
    for name in candidates:
        if name in columns:
            return name
    return None


def _select_alias(col: Optional[str], alias: str, default_literal: str) -> str:
    if col is None:
        return f"{default_literal} AS {alias}"
    return f"{col} AS {alias}"


def _get_receipt_id(conn: sqlite3.Connection, receipt_no: str) -> Optional[int]:
    cols = _table_columns(conn, "receipts")
    key_col = _first_existing(cols, "receipt_no", "receipt_number")
    id_col = _first_existing(cols, "id", "receipt_id")
    if key_col is None or id_col is None:
        return None

    sql = f"SELECT {id_col} AS receipt_id FROM receipts WHERE {key_col} = ? COLLATE NOCASE"
    row = conn.execute(sql, (receipt_no,)).fetchone()
    if row and row["receipt_id"] is not None:
        return int(row["receipt_id"])
    return None


def get_receipt_header_by_no(receipt_no: str, *, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Return receipt header fields for the given receipt_no."""
    own = conn is None
    c = conn or get_conn()
    try:
        cols = _table_columns(c, "receipts")
        key_col = _first_existing(cols, "receipt_no", "receipt_number")
        if key_col is None:
            return None

        id_col = _first_existing(cols, "id", "receipt_id")
        created_col = _first_existing(cols, "created_at", "paid_at")
        status_col = _first_existing(cols, "status")

        select_parts = [
            _select_alias(id_col, "receipt_id", "NULL"),
            _select_alias(key_col, "receipt_no", "''"),
            _select_alias(created_col, "created_at", "''"),
            _select_alias(status_col, "status", "''"),
        ]
        sql = f"SELECT {', '.join(select_parts)} FROM receipts WHERE {key_col} = ? COLLATE NOCASE LIMIT 1"
        row = c.execute(sql, (receipt_no,)).fetchone()
        return dict(row) if row else None
    finally:
        if own:
            c.close()


def list_receipt_items_by_no(
    receipt_no: str,
    *,
    receipt_id: Optional[int] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Return receipt items by receipt_no (or receipt_id when required)."""
    own = conn is None
    c = conn or get_conn()
    try:
        cols = _table_columns(c, "receipt_items")
        link_col = _first_existing(cols, "receipt_id", "receipt_no", "receipt_number")
        if link_col is None:
            return []

        qty_col = _first_existing(cols, "quantity", "qty")
        name_col = _first_existing(cols, "product_name", "name")
        unit_col = _first_existing(cols, "unit")
        price_col = _first_existing(cols, "unit_price", "price")
        line_total_col = _first_existing(cols, "line_total")
        order_col = _first_existing(cols, "line_no", "id", "item_id")

        select_parts = [
            _select_alias(qty_col, "qty", "0"),
            _select_alias(name_col, "product_name", "''"),
            _select_alias(unit_col, "unit", "''"),
            _select_alias(price_col, "unit_price", "0"),
            _select_alias(line_total_col, "line_total", "0"),
        ]

        where_val = receipt_no
        if link_col == "receipt_id":
            rid = receipt_id or _get_receipt_id(c, receipt_no)
            if rid is None:
                return []
            where_val = rid

        sql = f"SELECT {', '.join(select_parts)} FROM receipt_items WHERE {link_col} = ?"
        if order_col is not None:
            sql += f" ORDER BY {order_col} ASC"

        rows = c.execute(sql, (where_val,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def list_receipt_payments_by_no(
    receipt_no: str,
    *,
    receipt_id: Optional[int] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Return receipt payments by receipt_no (or receipt_id when required)."""
    own = conn is None
    c = conn or get_conn()
    try:
        cols = _table_columns(c, "receipt_payments")
        link_col = _first_existing(cols, "receipt_id", "receipt_no", "receipt_number")
        if link_col is None:
            return []

        ptype_col = _first_existing(cols, "payment_type", "type")
        # `amount` (allocated) removed — callers now use `tendered` (actual tender values)
        tendered_col = _first_existing(cols, "tendered", "tender", "cash_tendered")
        order_col = _first_existing(cols, "created_at", "paid_at", "id", "payment_id")

        select_parts = [_select_alias(ptype_col, "payment_type", "''"), _select_alias(tendered_col, "tendered", "0")]

        where_val = receipt_no
        if link_col == "receipt_id":
            rid = receipt_id or _get_receipt_id(c, receipt_no)
            if rid is None:
                return []
            where_val = rid

        sql = f"SELECT {', '.join(select_parts)} FROM receipt_payments WHERE {link_col} = ?"
        if order_col is not None:
            sql += f" ORDER BY {order_col} ASC"

        rows = c.execute(sql, (where_val,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()
