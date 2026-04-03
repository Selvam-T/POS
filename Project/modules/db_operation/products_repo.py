"""SQL-only repository for Product_list."""

import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from .db import get_conn, now_iso, transaction


TABLE = "Product_list"


def add_product(
    product_code: str,
    name: str,
    category: str = "",
    supplier: str = "",
    selling_price: float = 0.0,
    cost_price: float = 0.0,
    unit: str = "EACH",
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    sql = f"""
    INSERT INTO {TABLE}
      (product_code, name, category, supplier, selling_price, cost_price, unit, last_updated)
    VALUES
      (?, ?, ?, ?, ?, ?, ?, ?)
    """
    own = conn is None
    c = conn or get_conn()
    try:
        with transaction(c):
            c.execute(
                sql,
                (
                    product_code,
                    name,
                    category,
                    supplier,
                    float(selling_price),
                    float(cost_price),
                    unit,
                    now_iso(),
                ),
            )
    finally:
        if own:
            c.close()


def update_product(
    product_code: str,
    *,
    name: Optional[str] = None,
    category: Optional[str] = None,
    supplier: Optional[str] = None,
    selling_price: Optional[float] = None,
    cost_price: Optional[float] = None,
    unit: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> bool:
    """Return True if a row was updated."""
    fields: List[str] = []
    params: List[Any] = []

    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if category is not None:
        fields.append("category = ?")
        params.append(category)
    if supplier is not None:
        fields.append("supplier = ?")
        params.append(supplier)
    if selling_price is not None:
        fields.append("selling_price = ?")
        params.append(float(selling_price))
    if cost_price is not None:
        fields.append("cost_price = ?")
        params.append(float(cost_price))
    if unit is not None:
        fields.append("unit = ?")
        params.append(unit)

    fields.append("last_updated = ?")
    params.append(now_iso())

    if not fields:
        return False

    sql = f"""
    UPDATE {TABLE}
       SET {", ".join(fields)}
     WHERE product_code = ? COLLATE NOCASE
    """
    params.append(product_code)

    own = conn is None
    c = conn or get_conn()
    try:
        with transaction(c):
            cur = c.execute(sql, tuple(params))
            return cur.rowcount > 0
    finally:
        if own:
            c.close()


def delete_product(product_code: str, *, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Return True if a row was deleted."""
    sql = f"DELETE FROM {TABLE} WHERE product_code = ? COLLATE NOCASE"
    own = conn is None
    c = conn or get_conn()
    try:
        with transaction(c):
            cur = c.execute(sql, (product_code,))
            return cur.rowcount > 0
    finally:
        if own:
            c.close()


def replace_category(
    old_category: str,
    new_category: str,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    """Replace category for all products; returns affected row count."""
    sql = f"""
    UPDATE {TABLE}
       SET category = ?,
           last_updated = ?
     WHERE category = ? COLLATE NOCASE
    """
    own = conn is None
    c = conn or get_conn()
    try:
        if own:
            with transaction(c):
                cur = c.execute(sql, (new_category, now_iso(), old_category))
                return int(cur.rowcount or 0)
        cur = c.execute(sql, (new_category, now_iso(), old_category))
        return int(cur.rowcount or 0)
    finally:
        if own:
            c.close()


def get_product_full(product_code: str, *, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Return full product row as dict, or None."""
    sql = f"""
    SELECT product_code, name, category, supplier, selling_price, cost_price, unit, last_updated
      FROM {TABLE}
     WHERE product_code = ? COLLATE NOCASE
    """
    own = conn is None
    c = conn or get_conn()
    try:
        row = c.execute(sql, (product_code,)).fetchone()
        return dict(row) if row else None
    finally:
        if own:
            c.close()


def get_product_slim(product_code: str, *, conn: Optional[sqlite3.Connection] = None) -> Optional[Tuple[str, float, str]]:
    """Return (name, selling_price, unit) or None."""
    sql = f"""
    SELECT name, selling_price, unit
      FROM {TABLE}
     WHERE product_code = ? COLLATE NOCASE
    """
    own = conn is None
    c = conn or get_conn()
    try:
        row = c.execute(sql, (product_code,)).fetchone()
        if not row:
            return None
        return (row["name"] or "", float(row["selling_price"] or 0.0), row["unit"] or "")
    finally:
        if own:
            c.close()


def list_products(*, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Return full product rows."""
    sql = f"""
    SELECT product_code, name, category, supplier, selling_price, cost_price, unit, last_updated
      FROM {TABLE}
     ORDER BY name COLLATE NOCASE
    """
    own = conn is None
    c = conn or get_conn()
    try:
        rows = c.execute(sql).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def list_products_slim(*, conn: Optional[sqlite3.Connection] = None) -> List[Tuple[str, str, float, str]]:
    """Return (product_code, name, selling_price, unit) rows."""
    sql = f"""
    SELECT product_code, name, selling_price, unit
      FROM {TABLE}
     ORDER BY name COLLATE NOCASE
    """
    own = conn is None
    c = conn or get_conn()
    try:
        rows = c.execute(sql).fetchall()
        out: List[Tuple[str, str, float, str]] = []
        for r in rows:
            out.append(
                (
                    str(r["product_code"] or ""),
                    str(r["name"] or ""),
                    float(r["selling_price"] or 0.0),
                    str(r["unit"] or ""),
                )
            )
        return out
    finally:
        if own:
            c.close()


def get_product_list_schema_and_rows(*, conn: Optional[sqlite3.Connection] = None) -> Tuple[Optional[str], list, list]:
    """Return (create_table_sql, headers, rows) for Product_list.

    create_table_sql may be None if not found. Rows is a list of sqlite3.Row tuples.
    """
    own = conn is None
    c = conn or get_conn()
    try:
        cur = c.cursor()
        cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND lower(name)=lower(?)",
            ('Product_list',)
        )
        row = cur.fetchone()
        create_sql = row[0] if row and row[0] else None

        cur.execute('SELECT * FROM Product_list ORDER BY name COLLATE NOCASE')
        rows = cur.fetchall()
        headers = [d[0] for d in (cur.description or [])]
        return create_sql, headers, rows
    finally:
        if own:
            c.close()

