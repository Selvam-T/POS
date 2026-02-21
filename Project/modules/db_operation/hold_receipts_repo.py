"""SQL helpers for View Hold receipts (UNPAID list/search/void)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .db import get_conn, transaction, now_iso
from .receipt_write_helpers import table_columns, first_existing, column_notnull


def _select_alias(col: Optional[str], alias: str, default_literal: str) -> str:
    if col is None:
        return f"{default_literal} AS {alias}"
    return f"{col} AS {alias}"


def _receipt_cols(conn) -> Dict[str, Optional[str]]:
    cols = table_columns(conn, "receipts")
    return {
        "id_col": first_existing(cols, "id", "receipt_id"),
        "no_col": first_existing(cols, "receipt_no", "receipt_number"),
        "status_col": first_existing(cols, "status"),
        "customer_col": first_existing(cols, "customer_name"),
        "total_col": first_existing(cols, "grand_total", "total"),
        "created_col": first_existing(cols, "created_at", "paid_at"),
        "note_col": first_existing(cols, "note", "notes"),
        "cancelled_col": first_existing(cols, "cancelled_at"),
    }


def _order_clause(cols: Dict[str, Optional[str]]) -> str:
    created_col = cols.get("created_col")
    no_col = cols.get("no_col")
    parts = []
    if created_col:
        parts.append(f"{created_col} DESC")
    if no_col:
        parts.append(f"{no_col} DESC")
    if not parts:
        return ""
    return " ORDER BY " + ", ".join(parts)


def list_unpaid_receipts(*, conn=None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    own = conn is None
    c = conn or get_conn()
    try:
        cols = _receipt_cols(c)
        no_col = cols.get("no_col")
        status_col = cols.get("status_col")
        if no_col is None or status_col is None:
            return []

        select_parts = [
            _select_alias(cols.get("id_col"), "receipt_id", "NULL"),
            _select_alias(no_col, "receipt_no", "''"),
            _select_alias(cols.get("customer_col"), "customer_name", "''"),
            _select_alias(cols.get("total_col"), "grand_total", "0"),
            _select_alias(cols.get("created_col"), "created_at", "''"),
            _select_alias(cols.get("note_col"), "note", "''"),
            _select_alias(status_col, "status", "''"),
        ]

        sql = (
            f"SELECT {', '.join(select_parts)} "
            f"FROM receipts WHERE {status_col} = ? COLLATE NOCASE"
        )
        sql += _order_clause(cols)
        if limit and int(limit) > 0:
            sql += f" LIMIT {int(limit)}"

        rows = c.execute(sql, ("UNPAID",)).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def search_unpaid_receipts_by_customer(
    customer_query: str,
    *,
    conn=None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    query = (customer_query or "").strip()
    if not query:
        return list_unpaid_receipts(conn=conn, limit=limit)

    own = conn is None
    c = conn or get_conn()
    try:
        cols = _receipt_cols(c)
        no_col = cols.get("no_col")
        status_col = cols.get("status_col")
        customer_col = cols.get("customer_col")
        if no_col is None or status_col is None or customer_col is None:
            return []

        select_parts = [
            _select_alias(cols.get("id_col"), "receipt_id", "NULL"),
            _select_alias(no_col, "receipt_no", "''"),
            _select_alias(customer_col, "customer_name", "''"),
            _select_alias(cols.get("total_col"), "grand_total", "0"),
            _select_alias(cols.get("created_col"), "created_at", "''"),
            _select_alias(cols.get("note_col"), "note", "''"),
            _select_alias(status_col, "status", "''"),
        ]

        sql = (
            f"SELECT {', '.join(select_parts)} "
            f"FROM receipts WHERE {status_col} = ? COLLATE NOCASE "
            f"AND {customer_col} LIKE ? COLLATE NOCASE"
        )
        sql += _order_clause(cols)
        if limit and int(limit) > 0:
            sql += f" LIMIT {int(limit)}"

        rows = c.execute(sql, ("UNPAID", f"%{query}%")).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def void_receipt(
    *,
    receipt_id: Optional[int] = None,
    receipt_no: Optional[str] = None,
    note: Optional[str] = None,
    conn=None,
) -> bool:
    if receipt_id is None and not receipt_no:
        raise ValueError("receipt_id or receipt_no is required")

    own = conn is None
    c = conn or get_conn()
    try:
        cols = _receipt_cols(c)
        status_col = cols.get("status_col")
        if status_col is None:
            raise RuntimeError("receipts table missing status column")

        id_col = cols.get("id_col")
        no_col = cols.get("no_col")
        where_sql = None
        params = []

        if receipt_id is not None and id_col is not None:
            where_sql = f"{id_col} = ?"
            params.append(int(receipt_id))
        elif receipt_no and no_col is not None:
            where_sql = f"{no_col} = ? COLLATE NOCASE"
            params.append(str(receipt_no))

        if where_sql is None:
            raise RuntimeError("Unable to resolve receipt identifier for void")

        set_parts = [f"{status_col} = ?"]
        set_params: List[Any] = ["CANCELLED"]

        cancelled_col = cols.get("cancelled_col")
        if cancelled_col is not None:
            set_parts.append(f"{cancelled_col} = ?")
            set_params.append(now_iso())

        note_col = cols.get("note_col")
        if note_col is not None:
            note_text = (note or "").strip()
            if note_text:
                note_val: Any = note_text
            else:
                note_val = "" if column_notnull(c, "receipts", note_col) else None
            set_parts.append(f"{note_col} = ?")
            set_params.append(note_val)

        sql = f"UPDATE receipts SET {', '.join(set_parts)} WHERE {where_sql}"
        with transaction(c):
            cur = c.execute(sql, tuple(set_params + params))
        return cur.rowcount > 0
    finally:
        if own:
            c.close()
