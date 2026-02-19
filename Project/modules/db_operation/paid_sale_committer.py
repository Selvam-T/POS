"""Atomic paid-sale commit service for receipts."""

from __future__ import annotations

from typing import Optional

from modules.db_operation.db import get_conn, transaction, now_iso
from modules.db_operation.receipt_numbers import next_receipt_no
from modules.db_operation.receipt_write_helpers import (
    table_columns,
    first_existing,
    insert_row,
    insert_receipt_items,
    insert_receipt_payments,
)


class PaidSaleCommitter:
    def _insert_receipt_header_paid(self, conn, receipt_no: str, total: float, paid_at: str) -> int:
        cols = table_columns(conn, "receipts")
        values = {}

        key_col = first_existing(cols, "receipt_no", "receipt_number")
        if key_col is not None:
            values[key_col] = receipt_no

        for candidate, value in (
            ("grand_total", total),
            ("total", total),
            ("status", "PAID"),
            ("customer_name", ""),
            ("cashier_name", ""),
            ("notes", ""),
            ("note", ""),
            ("created_at", paid_at),
            ("paid_at", paid_at),
        ):
            if candidate in cols:
                values[candidate] = value

        if key_col is None and "id" not in cols and "receipt_id" not in cols:
            raise RuntimeError("receipts table missing receipt key columns")

        return insert_row(conn, "receipts", values)

    def _mark_receipt_paid(self, conn, active_receipt_id, paid_at: str) -> str:
        cols = table_columns(conn, "receipts")
        id_col = first_existing(cols, "id", "receipt_id")
        no_col = first_existing(cols, "receipt_no", "receipt_number")

        set_parts = []
        params = []
        if "status" in cols:
            set_parts.append("status = ?")
            params.append("PAID")
        if "paid_at" in cols:
            set_parts.append("paid_at = ?")
            params.append(paid_at)
        if not set_parts:
            raise RuntimeError("receipts table has no updatable paid columns")

        where_sql = None
        if id_col is not None and isinstance(active_receipt_id, int):
            where_sql = f"{id_col} = ?"
            params.append(active_receipt_id)
        elif no_col is not None:
            where_sql = f"{no_col} = ? COLLATE NOCASE"
            params.append(str(active_receipt_id))
        elif id_col is not None:
            where_sql = f"{id_col} = ?"
            params.append(active_receipt_id)

        if where_sql is None:
            raise RuntimeError("Cannot resolve receipt identifier for held payment")

        sql = f"UPDATE receipts SET {', '.join(set_parts)} WHERE {where_sql}"
        cur = conn.execute(sql, tuple(params))
        if cur.rowcount <= 0:
            raise RuntimeError("Held receipt not found or already paid")

        if no_col is None:
            return str(active_receipt_id)

        row = conn.execute(
            f"SELECT {no_col} AS receipt_no FROM receipts WHERE {where_sql}",
            tuple(params[-1:]),
        ).fetchone()
        if row and row["receipt_no"]:
            return str(row["receipt_no"])
        return str(active_receipt_id)

    def commit_paid_sale(
        self,
        *,
        active_receipt_id,
        sales_items: list[dict],
        payment_rows: list[tuple[str, float, float]],
        total: float,
        paid_at: Optional[str] = None,
    ) -> str:
        if not sales_items:
            raise RuntimeError("No sale items to pay")
        if not payment_rows:
            raise RuntimeError("No payment entries to save")

        paid_ts = paid_at or now_iso()

        receipt_no = None
        with get_conn() as conn:
            with transaction(conn):
                receipt_db_id = 0
                if active_receipt_id is None:
                    receipt_no = next_receipt_no(conn=conn)
                    receipt_db_id = self._insert_receipt_header_paid(conn, receipt_no, float(total or 0.0), paid_ts)
                    insert_receipt_items(conn, receipt_no, receipt_db_id, sales_items)
                else:
                    receipt_no = self._mark_receipt_paid(conn, active_receipt_id, paid_ts)
                    receipt_db_id = active_receipt_id if isinstance(active_receipt_id, int) else 0

                insert_receipt_payments(conn, receipt_no, receipt_db_id, payment_rows, paid_ts)

        return str(receipt_no)

    # Backward-compatible method name used by existing call sites.
    def commit_payment(
        self,
        *,
        active_receipt_id,
        sales_items: list[dict],
        payment_rows: list[tuple[str, float, float]],
        total: float,
        paid_at: Optional[str] = None,
    ) -> str:
        return self.commit_paid_sale(
            active_receipt_id=active_receipt_id,
            sales_items=sales_items,
            payment_rows=payment_rows,
            total=total,
            paid_at=paid_at,
        )


# Backward-compatible class name for legacy imports.
SaleCommitter = PaidSaleCommitter
