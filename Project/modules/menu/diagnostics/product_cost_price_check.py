"""Missing product cost-price diagnostic."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Mapping, Sequence

from modules.db_operation.sqlite_runtime import get_db_path
from modules.menu.diagnostics.common import read_only_connection, timestamp
from modules.ui_utils.canonicalization import canonicalize_product_code


def find_missing_product_cost_prices(database_rows: Sequence[Mapping]) -> dict:
    codes = []
    for row in database_rows:
        value = row.get("cost_price")
        if value is None or (isinstance(value, str) and not value.strip()):
            codes.append(canonicalize_product_code(row.get("product_code")))
    return {
        "database_total": len(database_rows),
        "missing_cost_price_total": len(codes),
        "missing_cost_price_codes": sorted(codes),
    }


def _read_product_rows(database_path: str) -> list[dict]:
    conn = read_only_connection(database_path)
    try:
        rows = conn.execute(
            "SELECT product_code, cost_price FROM Product_list ORDER BY product_code"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def run_product_cost_price_diagnostics(
    *,
    db_path: str | None = None,
    database_rows: Sequence[Mapping] | None = None,
) -> dict:
    started_clock = perf_counter()
    result = {
        "check": "Products with missing cost price",
        "status": "FAIL",
        "started_at": timestamp(),
        "completed_at": None,
        "duration_seconds": 0.0,
        "database_path": "",
        "database_total": 0,
        "missing_cost_price_total": 0,
        "missing_cost_price_codes": [],
        "issues": [],
    }
    try:
        if database_rows is None:
            database_path = str(Path(db_path or get_db_path()).resolve())
            result["database_path"] = database_path
            rows = _read_product_rows(database_path)
        else:
            rows = list(database_rows)
            if db_path:
                result["database_path"] = str(Path(db_path).resolve())

        result.update(find_missing_product_cost_prices(rows))
        if result["missing_cost_price_total"]:
            result["issues"].append(
                "Products with missing cost price: "
                f"{result['missing_cost_price_total']}"
            )
        result["status"] = "WARNING" if result["issues"] else "PASS"
    except Exception as exc:
        result["issues"].append(
            f"{type(exc).__name__}: "
            f"{str(exc) or 'Cost-price diagnostic failed'}"
        )
    finally:
        result["completed_at"] = timestamp()
        result["duration_seconds"] = round(perf_counter() - started_clock, 3)
    return result
