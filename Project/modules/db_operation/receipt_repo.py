"""Receipt repository (read-only + small write helpers)."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from .sqlite_runtime import get_conn, now_iso, transaction


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
        cashier_id_col = _first_existing(cols, "cashier_id")

        select_parts = [
            _select_alias(id_col, "receipt_id", "NULL"),
            _select_alias(key_col, "receipt_no", "''"),
            _select_alias(created_col, "created_at", "''"),
            _select_alias(status_col, "status", "''"),
            _select_alias(cashier_id_col, "cashier_id", "NULL"),
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
        code_col = _first_existing(cols, "product_code")
        name_col = _first_existing(cols, "product_name", "name")
        unit_col = _first_existing(cols, "unit")
        price_col = _first_existing(cols, "unit_price", "price")
        line_total_col = _first_existing(cols, "line_total")
        order_col = _first_existing(cols, "line_no", "id", "item_id")

        select_parts = [
            _select_alias(code_col, "product_code", "''"),
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
        amount_col = _first_existing(cols, "amount")
        tendered_col = _first_existing(cols, "tendered", "tender", "cash_tendered")
        order_col = _first_existing(cols, "created_at", "paid_at", "id", "payment_id")

        select_parts = [
            _select_alias(ptype_col, "payment_type", "''"),
            _select_alias(amount_col, "amount", "0"),
            _select_alias(tendered_col, "tendered", "0"),
        ]

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


def _receipt_cols(conn: sqlite3.Connection) -> Dict[str, Optional[str]]:
    cols = _table_columns(conn, "receipts")
    return {
        "id_col": _first_existing(cols, "id", "receipt_id"),
        "no_col": _first_existing(cols, "receipt_no", "receipt_number"),
        "status_col": _first_existing(cols, "status"),
        "created_col": _first_existing(cols, "created_at"),
        "paid_col": _first_existing(cols, "paid_at"),
        "cancelled_col": _first_existing(cols, "cancelled_at"),
        "note_col": _first_existing(cols, "note", "notes"),
    }


def _receipt_item_cols(conn: sqlite3.Connection) -> Dict[str, Optional[str]]:
    cols = _table_columns(conn, "receipt_items")
    return {
        "link_col": _first_existing(cols, "receipt_id", "receipt_no", "receipt_number"),
        "code_col": _first_existing(cols, "product_code"),
        "name_col": _first_existing(cols, "product_name", "name"),
        "line_total_col": _first_existing(cols, "line_total"),
        "qty_col": _first_existing(cols, "quantity", "qty"),
        "price_col": _first_existing(cols, "unit_price", "price"),
    }


def _date_match_expr(col: str) -> str:
    return f"{col} IS NOT NULL AND date({col}) >= date(?) AND date({col}) <= date(?)"


def search_receipts(
    *,
    status: str = "ALL",
    date_type: str = "ALL",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    receipt_no: str = "",
    product_code: str = "",
    product_name: str = "",
    limit: Optional[int] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Return receipt rows for the receipt-management dialog.

    Date filters use SQLite date() so stored values with either ``T`` or space
    separators compare correctly. ``date_type='ALL'`` checks created, paid, and
    cancelled dates but returns each receipt once.
    """
    own = conn is None
    c = conn or get_conn()
    try:
        # uncomment to test receipt search failure handling
        # raise RuntimeError("Testing receipt search failure") # debug
        rcols = _receipt_cols(c)
        icols = _receipt_item_cols(c)
        no_col = rcols.get("no_col")
        if no_col is None:
            return []

        id_col = rcols.get("id_col")
        status_col = rcols.get("status_col")
        created_col = rcols.get("created_col")
        paid_col = rcols.get("paid_col")
        cancelled_col = rcols.get("cancelled_col")
        note_col = rcols.get("note_col")

        select_parts = [
            _select_alias(id_col, "receipt_id", "NULL"),
            _select_alias(no_col, "receipt_no", "''"),
            _select_alias(status_col, "status", "''"),
            _select_alias(created_col, "created_at", "''"),
            _select_alias(paid_col, "paid_at", "''"),
            _select_alias(cancelled_col, "cancelled_at", "''"),
            _select_alias(note_col, "note", "''"),
        ]

        amount_expr = "0"
        item_link_col = icols.get("link_col")
        line_total_col = icols.get("line_total_col")
        if item_link_col is not None:
            if line_total_col is not None:
                line_expr = f"COALESCE({line_total_col}, 0)"
            else:
                qty_col = icols.get("qty_col")
                price_col = icols.get("price_col")
                if qty_col is not None and price_col is not None:
                    line_expr = f"COALESCE({qty_col}, 0) * COALESCE({price_col}, 0)"
                else:
                    line_expr = "0"

            if item_link_col == "receipt_id" and id_col is not None:
                amount_expr = (
                    f"(SELECT COALESCE(SUM({line_expr}), 0) FROM receipt_items ri "
                    f"WHERE ri.{item_link_col} = receipts.{id_col})"
                )
            else:
                amount_expr = (
                    f"(SELECT COALESCE(SUM({line_expr}), 0) FROM receipt_items ri "
                    f"WHERE ri.{item_link_col} = receipts.{no_col})"
                )
        select_parts.append(f"{amount_expr} AS amount")

        where_parts: List[str] = []
        params: List[Any] = []

        status_clean = str(status or "ALL").strip().upper()
        if status_clean and status_clean != "ALL" and status_col is not None:
            where_parts.append(f"{status_col} = ? COLLATE NOCASE")
            params.append(status_clean)

        date_map = {
            "TRANSACTION": created_col,
            "TRANSACTION DATE": created_col,
            "PAYMENT": paid_col,
            "PAYMENT DATE": paid_col,
            "CANCELLATION": cancelled_col,
            "CANCELLATION DATE": cancelled_col,
            "CANCELLED": cancelled_col,
            "CANCELLED DATE": cancelled_col,
        }
        date_type_clean = str(date_type or "ALL").strip().upper()
        date_cols: List[str] = []
        if date_type_clean == "ALL":
            date_cols = [col for col in (created_col, paid_col, cancelled_col) if col is not None]
        else:
            selected = date_map.get(date_type_clean)
            if selected is not None:
                date_cols = [selected]

        if from_date and to_date and date_cols:
            if len(date_cols) == 1:
                where_parts.append(_date_match_expr(date_cols[0]))
                params.extend([from_date, to_date])
            else:
                where_parts.append("(" + " OR ".join(_date_match_expr(col) for col in date_cols) + ")")
                for _col in date_cols:
                    params.extend([from_date, to_date])

        receipt_no_text = str(receipt_no or "").strip()
        if receipt_no_text:
            where_parts.append(f"{no_col} LIKE ? COLLATE NOCASE")
            params.append(f"%{receipt_no_text}%")

        def _item_exists_clause(item_col: Optional[str], value: str) -> None:
            text = str(value or "").strip()
            if not text or item_col is None or item_link_col is None:
                return
            if item_link_col == "receipt_id" and id_col is not None:
                link_expr = f"ri.{item_link_col} = receipts.{id_col}"
            else:
                link_expr = f"ri.{item_link_col} = receipts.{no_col}"
            where_parts.append(
                f"EXISTS (SELECT 1 FROM receipt_items ri WHERE {link_expr} "
                f"AND ri.{item_col} LIKE ? COLLATE NOCASE)"
            )
            params.append(f"%{text}%")

        _item_exists_clause(icols.get("code_col"), product_code)
        _item_exists_clause(icols.get("name_col"), product_name)

        sql = f"SELECT {', '.join(select_parts)} FROM receipts"
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)

        order_col = created_col or paid_col or cancelled_col or no_col
        if order_col:
            sql += f" ORDER BY {order_col} DESC"
        if no_col:
            sql += f", {no_col} DESC" if " ORDER BY " in sql else f" ORDER BY {no_col} DESC"
        if limit and int(limit) > 0:
            sql += f" LIMIT {int(limit)}"

        rows = c.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def void_unpaid_receipt(
    *,
    receipt_id: Optional[int] = None,
    receipt_no: Optional[str] = None,
    note: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> bool:
    """Mark an UNPAID receipt CANCELLED. PAID receipts are never voided here."""
    if receipt_id is None and not receipt_no:
        raise ValueError("receipt_id or receipt_no is required")

    own = conn is None
    c = conn or get_conn()
    try:
        # uncomment to test receipt void failure handling
        # raise RuntimeError("Testing receipt void failure")
        cols = _receipt_cols(c)
        status_col = cols.get("status_col")
        if status_col is None:
            raise RuntimeError("receipts table missing status column")

        id_col = cols.get("id_col")
        no_col = cols.get("no_col")
        where_parts: List[str] = [f"{status_col} = ? COLLATE NOCASE"]
        params: List[Any] = ["UNPAID"]

        if receipt_id is not None and id_col is not None:
            where_parts.append(f"{id_col} = ?")
            params.append(int(receipt_id))
        elif receipt_no and no_col is not None:
            where_parts.append(f"{no_col} = ? COLLATE NOCASE")
            params.append(str(receipt_no))
        else:
            raise RuntimeError("Unable to resolve receipt identifier for void")

        set_parts = [f"{status_col} = ?"]
        set_params: List[Any] = ["CANCELLED"]

        cancelled_col = cols.get("cancelled_col")
        if cancelled_col is not None:
            set_parts.append(f"{cancelled_col} = ?")
            set_params.append(now_iso())

        note_col = cols.get("note_col")
        if note_col is not None:
            set_parts.append(f"{note_col} = ?")
            set_params.append(str(note or "").strip())

        sql = f"UPDATE receipts SET {', '.join(set_parts)} WHERE {' AND '.join(where_parts)}"
        with transaction(c):
            cur = c.execute(sql, tuple(set_params + params))
        return bool(cur.rowcount)
    finally:
        if own:
            c.close()


def replace_item_category(
    old_category: str,
    new_category: str,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    """Replace category in receipt_items; returns affected row count."""
    sql = """
    UPDATE receipt_items
       SET category = ?
     WHERE category = ? COLLATE NOCASE
    """
    own = conn is None
    c = conn or get_conn()
    try:
        if own:
            with transaction(c):
                cur = c.execute(sql, (new_category, old_category))
                return int(cur.rowcount or 0)
        cur = c.execute(sql, (new_category, old_category))
        return int(cur.rowcount or 0)
    finally:
        if own:
            c.close()
