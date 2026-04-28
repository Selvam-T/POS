"""Reports_repo is the data layer. 
   It runs the SQL/aggregation logic and returns structured report data.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from ..date_time.formatters import parse_to_datetime
from .db import get_conn, now_iso
from . import products_repo, receipt_repo


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


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _hour_slot_label(timestamp_value: Any) -> Optional[Tuple[int, str]]:
    try:
        if timestamp_value is None:
            return None
        text = str(timestamp_value).strip().replace('Z', '+00:00')
        parsed = datetime.fromisoformat(text)
        hour = int(parsed.hour)
        next_hour = (hour + 1) % 24
        return hour, f"{hour:02d}:00 - {next_hour:02d}:00"
    except Exception:
        return None


def _aggregate_product_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        product_name = str(row.get('product_name') or '')
        unit = str(row.get('unit') or '')
        key = (product_name, unit)
        entry = grouped.get(key)
        if entry is None:
            entry = {
                'product_name': product_name,
                'unit': unit,
                'qty_sold': 0.0,
                'line_sales': 0.0,
            }
            grouped[key] = entry
        entry['qty_sold'] = _to_float(entry['qty_sold']) + _to_float(row.get('qty_sold'))
        entry['line_sales'] = _to_float(entry['line_sales']) + _to_float(row.get('line_sales'))

    out = list(grouped.values())
    out.sort(key=lambda r: (_to_float(r.get('line_sales')), _to_float(r.get('qty_sold'))), reverse=True)
    return out


def _top_n_products(rows: List[Dict[str, Any]], *, limit: int, sort_key: str) -> List[Dict[str, Any]]:
    aggregated = _aggregate_product_rows(rows)
    if sort_key == 'qty_sold':
        aggregated.sort(key=lambda r: (_to_float(r.get('qty_sold')), _to_float(r.get('line_sales'))), reverse=True)
    else:
        aggregated.sort(key=lambda r: (_to_float(r.get('line_sales')), _to_float(r.get('qty_sold'))), reverse=True)

    out: List[Dict[str, Any]] = []
    for idx, row in enumerate(aggregated[: int(limit)], start=1):
        out.append(
            {
                'rank': idx,
                'product_name': row.get('product_name', ''),
                'qty_sold': _to_float(row.get('qty_sold')),
                'unit': row.get('unit', ''),
                'line_sales': _to_float(row.get('line_sales')),
            }
        )
    return out


def _format_hour_slot(hour: int) -> str:
    next_hour = (hour + 1) % 24
    return f"{hour:02d}:00 - {next_hour:02d}:00"


def _fetch_paid_receipt_rows(
    conn: sqlite3.Connection,
    *,
    period_from: Optional[str],
    period_to: Optional[str],
) -> List[Dict[str, Any]]:
    cols = _table_columns(conn, 'receipts')
    if not cols:
        return []

    id_col = _first_existing(cols, 'receipt_id', 'id')
    no_col = _first_existing(cols, 'receipt_no', 'receipt_number')
    total_col = _first_existing(cols, 'grand_total', 'total')
    status_col = _first_existing(cols, 'status')
    paid_col = _first_existing(cols, 'paid_at', 'created_at')

    select_parts = []
    select_parts.append(f"{id_col} AS receipt_id" if id_col is not None else "NULL AS receipt_id")
    select_parts.append(f"{no_col} AS receipt_no" if no_col is not None else "'' AS receipt_no")
    select_parts.append(f"{total_col} AS total" if total_col is not None else "0 AS total")
    select_parts.append(f"{paid_col} AS paid_at" if paid_col is not None else "'' AS paid_at")

    where_sql, where_params = _receipt_filter_clause(
        status_col=status_col,
        paid_col=paid_col,
        period_from=period_from,
        period_to=period_to,
        status='PAID',
    )
    sql = f"SELECT {', '.join(select_parts)} FROM receipts{where_sql} ORDER BY {paid_col or 'receipt_id'} ASC"
    rows = conn.execute(sql, tuple(where_params)).fetchall()
    return [dict(row) for row in rows]


def _fetch_paid_item_rows(
    conn: sqlite3.Connection,
    paid_receipts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for receipt in paid_receipts:
        receipt_no = str(receipt.get('receipt_no') or '')
        if not receipt_no:
            continue
        receipt_id = receipt.get('receipt_id')
        paid_at = receipt.get('paid_at')
        hour_slot = _hour_slot_label(paid_at)
        hour_order = hour_slot[0] if hour_slot else 0
        items = receipt_repo.list_receipt_items_by_no(receipt_no, receipt_id=_to_int(receipt_id) if receipt_id is not None else None, conn=conn)
        for item in items:
            qty = _to_float(item.get('qty'))
            line_sales = _to_float(item.get('line_total'))
            rows.append(
                {
                    'hour_order': hour_order,
                    'hour_slot': hour_slot[1] if hour_slot else '00:00 - 01:00',
                    'product_code': str(item.get('product_code') or ''),
                    'product_name': item.get('product_name') or '',
                    'category': item.get('category') or '',
                    'unit': item.get('unit') or '',
                    'qty_sold': qty,
                    'line_sales': line_sales,
                }
            )
    return rows


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

    if paid_col is not None and period_from is not None:
        where_parts.append(f"{paid_col} >= ?")
        params.append(period_from)

    if paid_col is not None and period_to is not None:
        where_parts.append(f"{paid_col} <= ?")
        params.append(period_to)

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


def _parse_cutoff_datetime(period_from: Optional[str], period_to: Optional[str]) -> Optional[datetime]:
    cutoff_value = period_to or period_from
    if cutoff_value is None:
        return None
    dt = parse_to_datetime(cutoff_value)
    if dt is not None:
        return dt
    try:
        return datetime.fromisoformat(str(cutoff_value).replace('Z', '+00:00'))
    except Exception:
        return None


def _months_since(last_sold: datetime, cutoff: datetime) -> Optional[int]:
    if last_sold is None or cutoff is None:
        return None
    if last_sold > cutoff:
        return None
    months = (cutoff.year - last_sold.year) * 12 + (cutoff.month - last_sold.month)
    if cutoff.day < last_sold.day:
        months -= 1
    return months


def _norm_key(value: Any) -> str:
    return str(value or '').strip().lower()


def _build_inactivity_report_rows(
    conn: sqlite3.Connection,
    *,
    period_from: Optional[str],
    period_to: Optional[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    products = products_repo.list_products(conn=conn)
    if not products:
        return [], {
            'bucket_counts': {'3_6': 0, '6_12': 0, '1_plus': 0, 'never': 0},
            'total_inactive_products': 0,
        }

    cutoff_dt = _parse_cutoff_datetime(period_from, period_to)
    if cutoff_dt is None:
        cutoff_dt = parse_to_datetime(now_iso())

    paid_receipts = _fetch_paid_receipt_rows(conn, period_from=None, period_to=period_to)
    last_sold_by_code: Dict[str, datetime] = {}
    last_sold_by_name: Dict[str, datetime] = {}

    for receipt in paid_receipts:
        receipt_no = str(receipt.get('receipt_no') or '')
        if not receipt_no:
            continue
        paid_dt = parse_to_datetime(receipt.get('paid_at'))
        if paid_dt is None:
            continue
        receipt_id = receipt.get('receipt_id')
        items = receipt_repo.list_receipt_items_by_no(
            receipt_no,
            receipt_id=_to_int(receipt_id) if receipt_id is not None else None,
            conn=conn,
        )
        for item in items:
            code_key = _norm_key(item.get('product_code'))
            name_key = _norm_key(item.get('product_name'))
            if code_key:
                current = last_sold_by_code.get(code_key)
                if current is None or paid_dt > current:
                    last_sold_by_code[code_key] = paid_dt
            if name_key:
                current = last_sold_by_name.get(name_key)
                if current is None or paid_dt > current:
                    last_sold_by_name[name_key] = paid_dt

    buckets: Dict[str, List[Dict[str, Any]]] = {
        '3_6': [],
        '6_12': [],
        '1_plus': [],
        'never': [],
    }

    for product in products:
        product_code = str(product.get('product_code') or '')
        product_name = str(product.get('name') or '')
        category = str(product.get('category') or '')
        code_key = _norm_key(product_code)
        name_key = _norm_key(product_name)
        last_sold_dt = last_sold_by_code.get(code_key) or last_sold_by_name.get(name_key)

        if last_sold_dt is None:
            buckets['never'].append(
                {
                    'product_code': product_code,
                    'product_name': product_name,
                    'category': category,
                    'last_sold': None,
                }
            )
            continue

        months_since = _months_since(last_sold_dt, cutoff_dt) if cutoff_dt is not None else None
        if months_since is None or months_since < 3:
            continue
        if months_since < 6:
            bucket_key = '3_6'
        elif months_since < 12:
            bucket_key = '6_12'
        else:
            bucket_key = '1_plus'

        buckets[bucket_key].append(
            {
                'product_code': product_code,
                'product_name': product_name,
                'category': category,
                'last_sold': last_sold_dt.isoformat(sep=' '),
            }
        )

    def _sort_rows(rows: List[Dict[str, Any]], *, never_sold: bool = False) -> List[Dict[str, Any]]:
        if never_sold:
            return sorted(rows, key=lambda r: (_norm_key(r.get('product_code')), _norm_key(r.get('product_name'))))
        return sorted(
            rows,
            key=lambda r: (
                parse_to_datetime(r.get('last_sold')) or datetime.min,
                _norm_key(r.get('product_code')),
                _norm_key(r.get('product_name')),
            ),
        )

    buckets['3_6'] = _sort_rows(buckets['3_6'])
    buckets['6_12'] = _sort_rows(buckets['6_12'])
    buckets['1_plus'] = _sort_rows(buckets['1_plus'])
    buckets['never'] = _sort_rows(buckets['never'], never_sold=True)

    summary = {
        'bucket_counts': {
            '3_6': len(buckets['3_6']),
            '6_12': len(buckets['6_12']),
            '1_plus': len(buckets['1_plus']),
            'never': len(buckets['never']),
        },
        'total_inactive_products': len(buckets['3_6']) + len(buckets['6_12']) + len(buckets['1_plus']) + len(buckets['never']),
    }

    return [
        {'bucket': '3_6', 'title': 'NO SALE FOR 3–6 MONTHS', 'products': buckets['3_6']},
        {'bucket': '6_12', 'title': 'NO SALE FOR 6–12 MONTHS', 'products': buckets['6_12']},
        {'bucket': '1_plus', 'title': 'NO SALE FOR MORE THAN 1 YEAR', 'products': buckets['1_plus']},
        {'bucket': 'never', 'title': 'NEVER SOLD', 'products': buckets['never']},
    ], summary


def detailed_report(
    params: Dict[str, Any],
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Return the detailed sales report."""
    period_from, period_to = _safe_period(params)
    own = conn is None
    c = conn or get_conn()
    try:
        paid_rows = _fetch_paid_receipt_rows(c, period_from=period_from, period_to=period_to)
        paid_ids = [row.get('receipt_id') for row in paid_rows if row.get('receipt_id') is not None]
        paid_nos = [str(row.get('receipt_no') or '') for row in paid_rows if row.get('receipt_no')]
        gross_sales = sum(_to_float(row.get('total')) for row in paid_rows)

        payment_breakdown = _fetch_payment_breakdown(c, receipt_ids=paid_ids, receipt_nos=paid_nos)
        product_rows = _fetch_product_aggregates(c, receipt_ids=paid_ids, receipt_nos=paid_nos)
        categories = _build_category_breakdown(product_rows)
        top_products = _top_n_products(product_rows, limit=10, sort_key='line_sales')

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


def summary_report(
    params: Dict[str, Any],
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Return the summary sales report."""
    period_from, period_to = _safe_period(params)
    own = conn is None
    c = conn or get_conn()
    try:
        paid_rows = _fetch_paid_receipt_rows(c, period_from=period_from, period_to=period_to)
        paid_ids = [row.get('receipt_id') for row in paid_rows if row.get('receipt_id') is not None]
        paid_nos = [str(row.get('receipt_no') or '') for row in paid_rows if row.get('receipt_no')]
        gross_sales = sum(_to_float(row.get('total')) for row in paid_rows)

        payment_breakdown = _fetch_payment_breakdown(c, receipt_ids=paid_ids, receipt_nos=paid_nos)
        outflows, outflow_subtotals = _fetch_outflows(c, period_from=period_from, period_to=period_to)
        refund_total = _to_float(outflow_subtotals.get('REFUND_OUT'))
        vendor_total = _to_float(outflow_subtotals.get('VENDOR_OUT'))
        net_after_outflows = gross_sales - refund_total - vendor_total

        excluded = _fetch_excluded_receipts(c, period_from=period_from, period_to=period_to)

        paid_item_rows = _fetch_paid_item_rows(c, paid_rows)

        hour_sales: Dict[int, Dict[str, Any]] = {}
        hour_rows: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        all_product_rows: List[Dict[str, Any]] = []
        for row in paid_item_rows:
            hour_order = _to_int(row.get('hour_order'))
            hour_slot = str(row.get('hour_slot') or '')
            hour_sales.setdefault(hour_order, {'hour_order': hour_order, 'hour_slot': hour_slot, 'sales_amount': 0.0})
            hour_sales[hour_order]['sales_amount'] = _to_float(hour_sales[hour_order]['sales_amount']) + _to_float(row.get('line_sales'))
            hour_rows[hour_order].append(row)
            all_product_rows.append(row)

        sales_by_hour = [hour_sales[idx] for idx in sorted(hour_sales)]
        peak_hour = max(sales_by_hour, key=lambda r: _to_float(r.get('sales_amount')), default=None)

        def _top_rows_for(rows: List[Dict[str, Any]], *, sort_key: str, limit: int) -> List[Dict[str, Any]]:
            return _top_n_products(rows, limit=limit, sort_key=sort_key)

        top_qty_by_hour = []
        top_sales_by_hour = []
        for hour_order in sorted(hour_rows):
            label = hour_sales[hour_order]['hour_slot']
            rows = hour_rows[hour_order]
            top_qty_by_hour.append({'hour_slot': label, 'products': _top_rows_for(rows, sort_key='qty_sold', limit=5)})
            top_sales_by_hour.append({'hour_slot': label, 'products': _top_rows_for(rows, sort_key='line_sales', limit=5)})

        top_qty_day = _top_n_products(all_product_rows, limit=10, sort_key='qty_sold')
        top_sales_day = _top_n_products(all_product_rows, limit=10, sort_key='line_sales')

        return {
            'header': {
                'period_from': period_from,
                'period_to': period_to,
                'generated_at': now_iso(),
                'generated_by': _resolve_generated_by(c, params),
            },
            'sales_summary': {
                'paid_receipt_count': len(paid_rows),
                'gross_sales': _to_float(gross_sales),
                'less_refund_outflow': refund_total,
                'less_vendor_outflow': vendor_total,
                'net_after_outflows': _to_float(net_after_outflows),
            },
            'sales_by_hour': sales_by_hour,
            'peak_hour': peak_hour,
            'top_products_by_qty_hour': top_qty_by_hour,
            'top_products_by_sales_hour': top_sales_by_hour,
            'top_products_by_qty_day': top_qty_day,
            'top_products_by_sales_day': top_sales_day,
            'payment_breakdown': payment_breakdown,
            'cash_outflows': outflows,
            'outflow_subtotals': outflow_subtotals,
            'excluded': excluded,
        }
    finally:
        if own:
            c.close()


def inactivity_report(
    params: Dict[str, Any],
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Return the inactivity report."""
    period_from, period_to = _safe_period(params)
    own = conn is None
    c = conn or get_conn()
    try:
        sections, summary = _build_inactivity_report_rows(c, period_from=period_from, period_to=period_to)
        return {
            'header': {
                'period_checked': period_to or period_from,
                'generated_at': now_iso(),
                'generated_by': _resolve_generated_by(c, params),
            },
            'sections': sections,
            'summary': summary,
        }
    finally:
        if own:
            c.close()
