"""Atomic held-sale commit service for receipts (UNPAID, no payment rows)."""

from __future__ import annotations

from typing import Optional

from modules.db_operation.db import get_conn, transaction, now_iso
from modules.db_operation.receipt_numbers import next_receipt_no
from modules.db_operation.receipt_write_helpers import (
    table_columns,
    first_existing,
    insert_row,
    column_notnull,
    insert_receipt_items,
)


class HeldSaleCommitter:
    def _line_total(self, item: dict) -> float:
        try:
            if item.get("line_total") is not None:
                return float(item.get("line_total") or 0.0)
            qty = float(item.get("quantity") or 0.0)
            price = float(item.get("price") or 0.0)
            return float(qty * price)
        except Exception:
            return 0.0

    def _insert_unpaid_receipt(
        self,
        conn,
        *,
        receipt_no: str,
        customer_name: str,
        note: Optional[str],
        sales_items: list[dict],
        cashier_name: str = "",
    ) -> int:
        cols = table_columns(conn, "receipts")
        values = {}

        key_col = first_existing(cols, "receipt_no", "receipt_number")
        if key_col is not None:
            values[key_col] = receipt_no

        note_col = first_existing(cols, "note", "notes")
        total_val = float(sum(self._line_total(i) for i in (sales_items or [])))
        created_at = now_iso()

        for candidate, value in (
            ("status", "UNPAID"),
            ("customer_name", customer_name),
            ("cashier_name", str(cashier_name or "")),
            ("grand_total", total_val),
            ("total", total_val),
            ("created_at", created_at),
            ("paid_at", None),
        ):
            if candidate in cols:
                values[candidate] = value

        if note_col is not None:
            if note:
                values[note_col] = note
            else:
                values[note_col] = "" if column_notnull(conn, "receipts", note_col) else None

        if key_col is None and "id" not in cols and "receipt_id" not in cols:
            raise RuntimeError("receipts table missing receipt key columns")

        return insert_row(conn, "receipts", values)

    def commit_hold_sale(
        self,
        *,
        customer_name: str,
        note: Optional[str],
        sales_items: list[dict],
        cashier_name: str = "",
    ) -> str:
        if not sales_items:
            raise RuntimeError("No sale items to hold")

        with get_conn() as conn:
            with transaction(conn):
                receipt_no = next_receipt_no(conn=conn)
                receipt_db_id = self._insert_unpaid_receipt(
                    conn,
                    receipt_no=receipt_no,
                    customer_name=customer_name,
                    note=note,
                    sales_items=sales_items,
                    cashier_name=cashier_name,
                )
                insert_receipt_items(conn, receipt_no, receipt_db_id, sales_items)

        return str(receipt_no)
