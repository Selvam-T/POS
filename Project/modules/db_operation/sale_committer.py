"""Atomic payment commit service for receipts.

This module contains database write logic for finalizing payments. It keeps
multi-table CRUD in one transaction and is intentionally UI-agnostic.
"""

from __future__ import annotations

from typing import Optional

from modules.db_operation.db import get_conn, transaction, now_iso
from modules.db_operation.receipt_numbers import next_receipt_no


class SaleCommitter:
    @staticmethod
    def _table_columns(conn, table_name: str) -> set[str]:
        try:
            rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            return {str(r["name"]) for r in rows}
        except Exception:
            return set()

    @staticmethod
    def _first_existing(columns: set[str], *candidates: str):
        for name in candidates:
            if name in columns:
                return name
        return None

    @staticmethod
    def _insert_row(conn, table_name: str, values: dict) -> int:
        cols = list(values.keys())
        placeholders = ", ".join("?" for _ in cols)
        col_sql = ", ".join(cols)
        sql = f"INSERT INTO {table_name} ({col_sql}) VALUES ({placeholders})"
        cur = conn.execute(sql, tuple(values[c] for c in cols))
        return int(cur.lastrowid or 0)

    def _insert_receipt_header_paid(self, conn, receipt_no: str, total: float, paid_at: str) -> int:
        cols = self._table_columns(conn, "receipts")
        values = {}

        key_col = self._first_existing(cols, "receipt_no", "receipt_number")
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

        return self._insert_row(conn, "receipts", values)

    def _mark_receipt_paid(self, conn, active_receipt_id, paid_at: str) -> str:
        cols = self._table_columns(conn, "receipts")
        id_col = self._first_existing(cols, "id", "receipt_id")
        no_col = self._first_existing(cols, "receipt_no", "receipt_number")

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

    def _insert_receipt_items(self, conn, receipt_no: str, receipt_db_id: int, items: list[dict]) -> None:
        cols = self._table_columns(conn, "receipt_items")
        link_col = self._first_existing(cols, "receipt_id", "receipt_no", "receipt_number")
        if link_col is None:
            raise RuntimeError("receipt_items table missing receipt link column")

        for idx, item in enumerate(items, start=1):
            values = {}
            if link_col == "receipt_id" and receipt_db_id:
                values[link_col] = receipt_db_id
            else:
                values[link_col] = receipt_no

            if "line_no" in cols:
                values["line_no"] = idx
            if "product_code" in cols:
                values["product_code"] = item.get("product_code", "")

            name_col = self._first_existing(cols, "name", "product_name")
            if name_col is not None:
                values[name_col] = item.get("name", "")

            if "category" in cols:
                values["category"] = item.get("category", "")

            qty_col = self._first_existing(cols, "quantity", "qty")
            if qty_col is not None:
                values[qty_col] = float(item.get("quantity", 0.0) or 0.0)

            if "unit" in cols:
                values["unit"] = item.get("unit", "")

            price_col = self._first_existing(cols, "price", "unit_price")
            if price_col is not None:
                values[price_col] = float(item.get("price", 0.0) or 0.0)

            if "line_total" in cols:
                values["line_total"] = float(item.get("line_total", 0.0) or 0.0)

            self._insert_row(conn, "receipt_items", values)

    def _insert_receipt_payments(
        self,
        conn,
        receipt_no: str,
        receipt_db_id: int,
        payment_rows: list[tuple[str, float, float]],
        paid_at: str,
    ) -> None:
        cols = self._table_columns(conn, "receipt_payments")
        link_col = self._first_existing(cols, "receipt_id", "receipt_no", "receipt_number")
        if link_col is None:
            raise RuntimeError("receipt_payments table missing receipt link column")

        time_col = self._first_existing(cols, "created_at", "paid_at")

        for ptype, amount, tendered in payment_rows:
            values = {}
            if link_col == "receipt_id" and receipt_db_id:
                values[link_col] = receipt_db_id
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

            self._insert_row(conn, "receipt_payments", values)

    def commit_payment(
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
                    self._insert_receipt_items(conn, receipt_no, receipt_db_id, sales_items)
                else:
                    receipt_no = self._mark_receipt_paid(conn, active_receipt_id, paid_ts)
                    receipt_db_id = active_receipt_id if isinstance(active_receipt_id, int) else 0

                self._insert_receipt_payments(conn, receipt_no, receipt_db_id, payment_rows, paid_ts)

        return str(receipt_no)
