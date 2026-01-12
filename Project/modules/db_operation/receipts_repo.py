"""
Receipts repository (SQL only).

Location: Project/modules/db_operation/receipts_repo.py

IMPORTANT:
This file is a scaffold. Update table/column names to match your schema.

Suggested tables (edit if yours differ):
- receipts
- receipt_items
- receipt_payments

This repo intentionally depends only on db.py (+ receipt_numbers.py optionally).
"""

import sqlite3
from typing import Any, Dict, List, Optional

from .db import get_conn, now_iso, transaction


# ---- Adjust these names if your schema uses different ones ----
RECEIPTS_TABLE = "receipts"
ITEMS_TABLE = "receipt_items"
PAYMENTS_TABLE = "receipt_payments"


def create_receipt(
    receipt_no: str,
    *,
    status: str = "UNPAID",
    customer_name: str = "",
    cashier_name: str = "",
    notes: str = "",
    created_at: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """
    Create a receipt header row.

    Expected minimal columns (adjust SQL if needed):
      receipt_no, status, customer_name, cashier_name, notes, created_at
    """
    sql = f"""
    INSERT INTO {RECEIPTS_TABLE}
      (receipt_no, status, customer_name, cashier_name, notes, created_at)
    VALUES
      (?, ?, ?, ?, ?, ?)
    """
    own = conn is None
    c = conn or get_conn()
    try:
        with transaction(c):
            c.execute(
                sql,
                (
                    receipt_no,
                    status,
                    customer_name,
                    cashier_name,
                    notes,
                    created_at or now_iso(),
                ),
            )
    finally:
        if own:
            c.close()


def add_receipt_item(
    receipt_no: str,
    *,
    product_code: str,
    product_name: str,
    qty: float,
    unit_price: float,
    unit: str,
    line_total: float,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """
    Insert an item line.

    Expected minimal columns (adjust SQL if needed):
      receipt_no, product_code, product_name, qty, unit_price, unit, line_total
    """
    sql = f"""
    INSERT INTO {ITEMS_TABLE}
      (receipt_no, product_code, product_name, qty, unit_price, unit, line_total)
    VALUES
      (?, ?, ?, ?, ?, ?, ?)
    """
    own = conn is None
    c = conn or get_conn()
    try:
        with transaction(c):
            c.execute(
                sql,
                (
                    receipt_no,
                    product_code,
                    product_name,
                    float(qty),
                    float(unit_price),
                    unit,
                    float(line_total),
                ),
            )
    finally:
        if own:
            c.close()


def add_payment(
    receipt_no: str,
    *,
    payment_type: str,
    amount: float,
    paid_at: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """
    Insert a payment record.

    Expected minimal columns (adjust SQL if needed):
      receipt_no, payment_type, amount, paid_at
    """
    sql = f"""
    INSERT INTO {PAYMENTS_TABLE}
      (receipt_no, payment_type, amount, paid_at)
    VALUES
      (?, ?, ?, ?)
    """
    own = conn is None
    c = conn or get_conn()
    try:
        with transaction(c):
            c.execute(sql, (receipt_no, payment_type, float(amount), paid_at or now_iso()))
    finally:
        if own:
            c.close()


def mark_receipt_paid(receipt_no: str, *, paid_at: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> bool:
    """
    Update receipt status to PAID and set paid_at.

    Expected columns in receipts table:
      status, paid_at
    """
    sql = f"""
    UPDATE {RECEIPTS_TABLE}
       SET status = 'PAID',
           paid_at = ?
     WHERE receipt_no = ? COLLATE NOCASE
    """
    own = conn is None
    c = conn or get_conn()
    try:
        with transaction(c):
            cur = c.execute(sql, (paid_at or now_iso(), receipt_no))
            return cur.rowcount > 0
    finally:
        if own:
            c.close()


def get_receipt_header(receipt_no: str, *, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    sql = f"SELECT * FROM {RECEIPTS_TABLE} WHERE receipt_no = ? COLLATE NOCASE"
    own = conn is None
    c = conn or get_conn()
    try:
        row = c.execute(sql, (receipt_no,)).fetchone()
        return dict(row) if row else None
    finally:
        if own:
            c.close()


def list_receipt_items(receipt_no: str, *, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    sql = f"SELECT * FROM {ITEMS_TABLE} WHERE receipt_no = ? COLLATE NOCASE"
    own = conn is None
    c = conn or get_conn()
    try:
        rows = c.execute(sql, (receipt_no,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()
