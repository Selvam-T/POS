"""Shared write helpers for receipt-related database operations."""

from __future__ import annotations


def table_columns(conn, table_name: str) -> set[str]:
    try:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(r["name"]) for r in rows}
    except Exception:
        return set()


def first_existing(columns: set[str], *candidates: str):
    for name in candidates:
        if name in columns:
            return name
    return None


def insert_row(conn, table_name: str, values: dict) -> int:
    cols = list(values.keys())
    placeholders = ", ".join("?" for _ in cols)
    col_sql = ", ".join(cols)
    sql = f"INSERT INTO {table_name} ({col_sql}) VALUES ({placeholders})"
    cur = conn.execute(sql, tuple(values[c] for c in cols))
    return int(cur.lastrowid or 0)


def column_notnull(conn, table_name: str, column_name: str) -> bool:
    try:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        for row in rows:
            if str(row["name"]) == str(column_name):
                return bool(row["notnull"])
    except Exception:
        pass
    return False


def resolve_receipt_id_by_no(conn, receipt_no: str) -> int:
    cols = table_columns(conn, "receipts")
    id_col = first_existing(cols, "id", "receipt_id")
    no_col = first_existing(cols, "receipt_no", "receipt_number")
    if id_col is None or no_col is None:
        return 0
    try:
        row = conn.execute(
            f"SELECT {id_col} AS rid FROM receipts WHERE {no_col} = ? COLLATE NOCASE LIMIT 1",
            (str(receipt_no),),
        ).fetchone()
        if row and row["rid"] is not None:
            return int(row["rid"])
    except Exception:
        return 0
    return 0


def insert_receipt_items(conn, receipt_no: str, receipt_db_id: int, items: list[dict]) -> None:
    cols = table_columns(conn, "receipt_items")
    link_col = first_existing(cols, "receipt_id", "receipt_no", "receipt_number")
    if link_col is None:
        raise RuntimeError("receipt_items table missing receipt link column")

    resolved_receipt_id = int(receipt_db_id or 0)
    if link_col == "receipt_id" and resolved_receipt_id <= 0:
        resolved_receipt_id = resolve_receipt_id_by_no(conn, receipt_no)
    if link_col == "receipt_id" and resolved_receipt_id <= 0:
        raise RuntimeError("Unable to resolve receipt_id for receipt_items insert")

    for idx, item in enumerate(items, start=1):
        values = {}
        if link_col == "receipt_id":
            values[link_col] = resolved_receipt_id
        else:
            values[link_col] = receipt_no

        if "line_no" in cols:
            values["line_no"] = idx
        if "product_code" in cols:
            values["product_code"] = item.get("product_code", "")

        name_col = first_existing(cols, "name", "product_name")
        if name_col is not None:
            values[name_col] = item.get("name", "")

        if "category" in cols:
            values["category"] = item.get("category", "")

        qty_col = first_existing(cols, "quantity", "qty")
        if qty_col is not None:
            values[qty_col] = float(item.get("quantity", 0.0) or 0.0)

        if "unit" in cols:
            values["unit"] = item.get("unit", "")

        price_col = first_existing(cols, "price", "unit_price")
        if price_col is not None:
            values[price_col] = float(item.get("price", 0.0) or 0.0)

        if "line_total" in cols:
            values["line_total"] = float(item.get("line_total", 0.0) or 0.0)

        insert_row(conn, "receipt_items", values)


def insert_receipt_payments(
    conn,
    receipt_no: str,
    receipt_db_id: int,
    payment_rows: list[tuple[str, float, float]],
    paid_at: str,
) -> None:
    cols = table_columns(conn, "receipt_payments")
    link_col = first_existing(cols, "receipt_id", "receipt_no", "receipt_number")
    if link_col is None:
        raise RuntimeError("receipt_payments table missing receipt link column")

    time_col = first_existing(cols, "created_at", "paid_at")

    resolved_receipt_id = int(receipt_db_id or 0)
    if link_col == "receipt_id" and resolved_receipt_id <= 0:
        resolved_receipt_id = resolve_receipt_id_by_no(conn, receipt_no)
    if link_col == "receipt_id" and resolved_receipt_id <= 0:
        raise RuntimeError("Unable to resolve receipt_id for receipt_payments insert")

    for ptype, amount, tendered in payment_rows:
        values = {}
        if link_col == "receipt_id":
            values[link_col] = resolved_receipt_id
        else:
            values[link_col] = receipt_no

        if "payment_type" in cols:
            values["payment_type"] = ptype
        if "amount" in cols:
            values["amount"] = float(amount)
        if "tendered" in cols:
            values["tendered"] = float(tendered)
        if time_col is not None:
            values[time_col] = paid_at

        insert_row(conn, "receipt_payments", values)
