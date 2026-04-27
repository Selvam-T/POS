"""Report-specific data access and aggregation helpers.

This module owns cross-table report aggregations. It is intentionally separate
from per-table CRUD repos so reporting logic stays localized and testable.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from .db import get_conn, now_iso


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


def _to_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _safe_period(params: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    period_from = params.get("from") or params.get("from_date") or params.get("start")
    period_to = params.get("to") or params.get("to_date") or params.get("end")
    return (
        str(period_from) if period_from not in (None, "") else None,
        str(period_to) if period_to not in (None, "") else None,
    )


def _resolve_generated_by(conn: sqlite3.Connection, params: Dict[str, Any]) -> Optional[str]:
    user_id = params.get("user_id")
    username = params.get("username")
    if username:
        return str(username)
    if user_id is None:
        return None
    users_cols = _table_columns(conn, "users")
    if not users_cols:
        return str(user_id)
    username_col = _first_existing(users_cols, "username")
    user_id_col = _first_existing(users_cols, "user_id", "id")
    if username_col is None or user_id_col is None:
        return str(user_id)
    try:
        row = conn.execute(
            f"SELECT {username_col} AS username FROM users WHERE {user_id_col} = ? LIMIT 1",
            (user_id,),
        ).fetchone()
        if row and row["username"]:
            return str(row["username"])
    except Exception:
        pass
    return str(user_id)


def _receipt_filter_clause(
    *,
    status_col: Optional[str],
    paid_col: Optional[str],
    period_from: Optional[str],
    period_to: Optional[str],
    status: str,
) -> Tuple[str, List[Any]]:
    where_parts: List[str] = []
    params: List[Any] = []

    if status_col is not None:
        where_parts.append(f"{status_col} = ? COLLATE NOCASE")
        params.append(status)

    if paid_col is not None and period_from is not None and period_to is not None:
        where_parts.append(f"{paid_col} >= ? AND {paid_col} <= ?")
        params.extend([period_from, period_to])

    if not where_parts:
        return "", params
    return " WHERE " + " AND ".join(where_parts), params


def _collect_paid_receipts(
    conn: sqlite3.Connection,
    *,
    period_from: Optional[str],
    period_to: Optional[str],
) -> Tuple[List[Dict[str, Any]], List[Any], List[str], float]:
    cols = _table_columns(conn, "receipts")
    if not cols:
        return [], [], [], 0.0

    id_col = _first_existing(cols, "receipt_id", "id")
    no_col = _first_existing(cols, "receipt_no", "receipt_number")
    total_col = _first_existing(cols, "grand_total", "total")
    status_col = _first_existing(cols, "status")
    paid_col = _first_existing(cols, "paid_at", "created_at")

    select_parts = []
    if id_col is not None:
        select_parts.append(f"{id_col} AS receipt_id")
    else:
        select_parts.append("NULL AS receipt_id")
    if no_col is not None:
        select_parts.append(f"{no_col} AS receipt_no")
    else:
        select_parts.append("'' AS receipt_no")
    if total_col is not None:
        select_parts.append(f"{total_col} AS total")
    else:
        select_parts.append("0 AS total")

    where_sql, where_params = _receipt_filter_clause(
        status_col=status_col,
        paid_col=paid_col,
        period_from=period_from,
        period_to=period_to,
        status="PAID",
    )
    sql = f"SELECT {', '.join(select_parts)} FROM receipts{where_sql}"
    rows = conn.execute(sql, tuple(where_params)).fetchall()

    paid_rows = [dict(r) for r in rows]
    receipt_ids: List[Any] = [r["receipt_id"] for r in paid_rows if r.get("receipt_id") is not None]
    receipt_nos: List[str] = [str(r.get("receipt_no") or "") for r in paid_rows if r.get("receipt_no")]
    gross_sales = sum(_to_float(r.get("total")) for r in paid_rows)
    return paid_rows, receipt_ids, receipt_nos, gross_sales


def _fetch_payment_breakdown(
    conn: sqlite3.Connection,
    *,
    receipt_ids: List[Any],
    receipt_nos: List[str],
) -> List[Dict[str, Any]]:
    cols = _table_columns(conn, "receipt_payments")
    if not cols:
        return []

    link_col = _first_existing(cols, "receipt_id", "receipt_no", "receipt_number")
    ptype_col = _first_existing(cols, "payment_type", "type")
    amount_col = _first_existing(cols, "amount")
    if link_col is None or ptype_col is None or amount_col is None:
        return []

    if link_col == "receipt_id":
        keys = [rid for rid in receipt_ids if rid is not None]
    else:
        keys = [rno for rno in receipt_nos if rno]
    if not keys:
        return []

    placeholders = ",".join("?" for _ in keys)
    sql = (
        f"SELECT {ptype_col} AS method, SUM(COALESCE({amount_col}, 0)) AS amount "
        f"FROM receipt_payments WHERE {link_col} IN ({placeholders}) "
        f"GROUP BY {ptype_col} ORDER BY amount DESC"
    )
    rows = conn.execute(sql, tuple(keys)).fetchall()
    return [{"method": str(r["method"] or ""), "amount": _to_float(r["amount"])} for r in rows]


def _fetch_product_aggregates(
    conn: sqlite3.Connection,
    *,
    receipt_ids: List[Any],
    receipt_nos: List[str],
) -> List[Dict[str, Any]]:
    cols = _table_columns(conn, "receipt_items")
    if not cols:
        return []

    link_col = _first_existing(cols, "receipt_id", "receipt_no", "receipt_number")
    category_col = _first_existing(cols, "category")
    name_col = _first_existing(cols, "product_name", "name")
    qty_col = _first_existing(cols, "quantity", "qty")
    unit_col = _first_existing(cols, "unit")
    line_total_col = _first_existing(cols, "line_total")
    price_col = _first_existing(cols, "unit_price", "price")
    if link_col is None or name_col is None or qty_col is None:
        return []

    if link_col == "receipt_id":
        keys = [rid for rid in receipt_ids if rid is not None]
    else:
        keys = [rno for rno in receipt_nos if rno]
    if not keys:
        return []

    placeholders = ",".join("?" for _ in keys)
    category_expr = category_col if category_col is not None else "''"
    unit_expr = unit_col if unit_col is not None else "''"
    line_sales_expr = line_total_col if line_total_col is not None else f"COALESCE({qty_col}, 0) * COALESCE({price_col or '0'}, 0)"

    sql = (
        f"SELECT {category_expr} AS category_name, "
        f"{name_col} AS product_name, "
        f"{unit_expr} AS unit, "
        f"SUM(COALESCE({qty_col}, 0)) AS qty_sold, "
        f"SUM(COALESCE({line_sales_expr}, 0)) AS line_sales "
        f"FROM receipt_items "
        f"WHERE {link_col} IN ({placeholders}) "
        f"GROUP BY {category_expr}, {name_col}, {unit_expr} "
        f"ORDER BY line_sales DESC"
    )
    rows = conn.execute(sql, tuple(keys)).fetchall()

    out: List[Dict[str, Any]] = []
    for r in rows:
        qty = _to_float(r["qty_sold"])
        sales = _to_float(r["line_sales"])
        out.append(
            {
                "category_name": str(r["category_name"] or "Uncategorized"),
                "product_name": str(r["product_name"] or ""),
                "unit": str(r["unit"] or ""),
                "qty_sold": qty,
                "line_sales": sales,
                "unit_price": (sales / qty) if qty > 0 else 0.0,
            }
        )
    return out


def _build_category_breakdown(product_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for row in product_rows:
        cat = str(row.get("category_name") or "Uncategorized")
        entry = grouped.get(cat)
        if entry is None:
            entry = {"category_name": cat, "category_total": 0.0, "products": []}
            grouped[cat] = entry
        entry["category_total"] = _to_float(entry["category_total"]) + _to_float(row.get("line_sales"))
        entry["products"].append(
            {
                "product_name": row.get("product_name", ""),
                "unit_price": _to_float(row.get("unit_price")),
                "qty_sold": _to_float(row.get("qty_sold")),
                "unit": row.get("unit", ""),
                "line_sales": _to_float(row.get("line_sales")),
            }
        )

    categories = list(grouped.values())
    for cat in categories:
        cat["products"].sort(key=lambda p: _to_float(p.get("line_sales")), reverse=True)
    categories.sort(key=lambda c: _to_float(c.get("category_total")), reverse=True)
    return categories


def _build_top_products(product_rows: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    top = sorted(product_rows, key=lambda r: _to_float(r.get("line_sales")), reverse=True)[: int(limit)]
    out: List[Dict[str, Any]] = []
    for idx, row in enumerate(top, start=1):
        out.append(
            {
                "rank": idx,
                "product_name": row.get("product_name", ""),
                "qty_sold": _to_float(row.get("qty_sold")),
                "unit": row.get("unit", ""),
                "line_sales": _to_float(row.get("line_sales")),
            }
        )
    return out


def _fetch_outflows(
    conn: sqlite3.Connection,
    *,
    period_from: Optional[str],
    period_to: Optional[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    cols = _table_columns(conn, "cash_outflows")
    if not cols:
        return [], {}

    id_col = _first_existing(cols, "outflows_id", "id")
    type_col = _first_existing(cols, "outflows_type", "outflow_type")
    amount_col = _first_existing(cols, "amount")
    created_col = _first_existing(cols, "created_at")
    note_col = _first_existing(cols, "note", "notes")
    cashier_col = _first_existing(cols, "cashier_id")

    if type_col is None or amount_col is None:
        return [], {}

    users_cols = _table_columns(conn, "users")
    user_id_col = _first_existing(users_cols, "user_id", "id")
    username_col = _first_existing(users_cols, "username")

    select_parts = [
        (f"o.{id_col}" if id_col else "NULL") + " AS outflow_id",
        f"o.{type_col} AS outflow_type",
        f"COALESCE(o.{amount_col}, 0) AS amount",
        (f"o.{created_col}" if created_col else "''") + " AS created_at",
        (f"o.{note_col}" if note_col else "''") + " AS note",
        (f"o.{cashier_col}" if cashier_col else "NULL") + " AS cashier_id",
    ]
    join_sql = ""
    if cashier_col and user_id_col and username_col:
        select_parts.append(f"u.{username_col} AS cashier")
        join_sql = f" LEFT JOIN users u ON o.{cashier_col} = u.{user_id_col}"
    else:
        select_parts.append("'' AS cashier")

    where_parts = []
    params: List[Any] = []
    if created_col is not None and period_from is not None and period_to is not None:
        where_parts.append(f"o.{created_col} >= ? AND o.{created_col} <= ?")
        params.extend([period_from, period_to])

    where_sql = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
    order_sql = f" ORDER BY o.{created_col} ASC" if created_col else ""
    sql = f"SELECT {', '.join(select_parts)} FROM cash_outflows o{join_sql}{where_sql}{order_sql}"
    rows = conn.execute(sql, tuple(params)).fetchall()

    outflows: List[Dict[str, Any]] = []
    subtotals: Dict[str, float] = defaultdict(float)
    for row in rows:
        d = dict(row)
        typ = str(d.get("outflow_type") or "")
        amt = _to_float(d.get("amount"))
        outflows.append(
            {
                "outflow_id": d.get("outflow_id"),
                "outflow_type": typ,
                "created_at": d.get("created_at") or "",
                "cashier": d.get("cashier") or "",
                "cashier_id": d.get("cashier_id"),
                "amount": amt,
                "note": d.get("note") or "",
            }
        )
        if typ:
            subtotals[typ] += amt

    return outflows, dict(subtotals)


def _fetch_excluded_receipts(
    conn: sqlite3.Connection,
    *,
    period_from: Optional[str],
    period_to: Optional[str],
) -> Dict[str, Any]:
    cols = _table_columns(conn, "receipts")
    if not cols:
        return {
            "unpaid_receipts_count": 0,
            "unpaid_receipts_total": 0.0,
            "cancelled_receipts_count": 0,
            "cancelled_receipts_total": 0.0,
            "receipts": [],
        }

    no_col = _first_existing(cols, "receipt_no", "receipt_number")
    status_col = _first_existing(cols, "status")
    customer_col = _first_existing(cols, "customer_name")
    total_col = _first_existing(cols, "grand_total", "total")
    note_col = _first_existing(cols, "note", "notes")
    created_col = _first_existing(cols, "created_at")
    if status_col is None:
        return {
            "unpaid_receipts_count": 0,
            "unpaid_receipts_total": 0.0,
            "cancelled_receipts_count": 0,
            "cancelled_receipts_total": 0.0,
            "receipts": [],
        }

    select_parts = [
        (no_col if no_col else "''") + " AS receipt_no",
        f"{status_col} AS status",
        (customer_col if customer_col else "''") + " AS customer_name",
        (total_col if total_col else "0") + " AS value",
        (note_col if note_col else "''") + " AS note",
    ]
    where_parts = [f"{status_col} IN ('UNPAID', 'CANCELLED')"]
    params: List[Any] = []
    if created_col is not None and period_from is not None and period_to is not None:
        where_parts.append(f"{created_col} >= ? AND {created_col} <= ?")
        params.extend([period_from, period_to])

    sql = (
        f"SELECT {', '.join(select_parts)} FROM receipts "
        f"WHERE {' AND '.join(where_parts)} ORDER BY receipt_no ASC"
    )
    rows = conn.execute(sql, tuple(params)).fetchall()

    excluded_rows = []
    unpaid_count = 0
    unpaid_total = 0.0
    cancelled_count = 0
    cancelled_total = 0.0
    for row in rows:
        d = dict(row)
        status = str(d.get("status") or "").upper()
        value = _to_float(d.get("value"))
        if status == "UNPAID":
            unpaid_count += 1
            unpaid_total += value
        elif status == "CANCELLED":
            cancelled_count += 1
            cancelled_total += value

        excluded_rows.append(
            {
                "receipt_no": d.get("receipt_no") or "",
                "status": status,
                "customer_name": d.get("customer_name") or "",
                "value": value,
                "note": d.get("note") or "",
            }
        )

    return {
        "unpaid_receipts_count": unpaid_count,
        "unpaid_receipts_total": unpaid_total,
        "cancelled_receipts_count": cancelled_count,
        "cancelled_receipts_total": cancelled_total,
        "receipts": excluded_rows,
    }


def detailed_report(
    params: Dict[str, Any],
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Return the structured Detailed Sales Report.

    Rules implemented:
    - Sales counted only for `receipts.status = 'PAID'` and within paid_at range.
    - Outflows counted by `cash_outflows.created_at` range.
    - Excluded section includes UNPAID/CANCELLED receipts in range.
    """
    period_from, period_to = _safe_period(params)
    own = conn is None
    c = conn or get_conn()
    try:
        paid_rows, paid_ids, paid_nos, gross_sales = _collect_paid_receipts(
            c,
            period_from=period_from,
            period_to=period_to,
        )

        payment_breakdown = _fetch_payment_breakdown(c, receipt_ids=paid_ids, receipt_nos=paid_nos)
        product_rows = _fetch_product_aggregates(c, receipt_ids=paid_ids, receipt_nos=paid_nos)
        categories = _build_category_breakdown(product_rows)
        top_products = _build_top_products(product_rows, limit=10)

        outflows, outflow_subtotals = _fetch_outflows(c, period_from=period_from, period_to=period_to)
        refund_total = _to_float(outflow_subtotals.get("REFUND_OUT"))
        vendor_total = _to_float(outflow_subtotals.get("VENDOR_OUT"))
        net_after_outflows = gross_sales - refund_total - vendor_total

        excluded = _fetch_excluded_receipts(c, period_from=period_from, period_to=period_to)

        return {
            "header": {
                "period_from": period_from,
                "period_to": period_to,
                "generated_at": now_iso(),
                "generated_by": _resolve_generated_by(c, params),
            },
            "sales_summary": {
                "paid_receipt_count": len(paid_rows),
                "gross_sales": _to_float(gross_sales),
                "less_refund_outflow": refund_total,
                "less_vendor_outflow": vendor_total,
                "net_after_outflows": _to_float(net_after_outflows),
            },
            "payment_breakdown": payment_breakdown,
            "categories": categories,
            "top_products": top_products,
            "cash_outflows": outflows,
            "outflow_subtotals": outflow_subtotals,
            "excluded": excluded,
        }
    finally:
        if own:
            c.close()
