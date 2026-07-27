"""Database counts and SQLite integrity diagnostic."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Iterable

from modules.db_operation.sqlite_runtime import get_db_path
from modules.menu.diagnostics.common import (
    quote_identifier,
    read_only_connection,
    timestamp,
)


CORE_TABLES = (
    "Product_list",
    "Category",
    "users",
    "receipts",
    "receipt_items",
    "receipt_payments",
    "cash_outflows",
)


def run_database_diagnostics(
    db_path: str | None = None,
    *,
    required_tables: Iterable[str] = CORE_TABLES,
) -> dict:
    """Run database counts and SQLite integrity checks without writing."""
    started_at = timestamp()
    started_clock = perf_counter()
    conn = None

    result = {
        "check": "Database counts and SQLite integrity",
        "status": "FAIL",
        "started_at": started_at,
        "completed_at": None,
        "duration_seconds": 0.0,
        "database_path": "",
        "database_size_bytes": None,
        "read_only": True,
        "foreign_keys_enabled": False,
        "required_tables": list(required_tables),
        "missing_tables": [],
        "table_counts": {},
        "quick_check": [],
        "foreign_key_violations": [],
        "issues": [],
    }

    try:
        database_path = str(Path(db_path or get_db_path()).resolve())
        result["database_path"] = database_path
        result["database_size_bytes"] = Path(database_path).stat().st_size

        conn = read_only_connection(database_path)
        result["foreign_keys_enabled"] = bool(
            conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        )

        table_rows = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        actual_by_key = {
            str(row["name"]).casefold(): str(row["name"])
            for row in table_rows
        }

        missing = [
            table
            for table in result["required_tables"]
            if str(table).casefold() not in actual_by_key
        ]
        result["missing_tables"] = missing

        for expected_name in result["required_tables"]:
            actual_name = actual_by_key.get(str(expected_name).casefold())
            if actual_name is None:
                continue
            count = conn.execute(
                f"SELECT COUNT(*) FROM {quote_identifier(actual_name)}"
            ).fetchone()[0]
            result["table_counts"][expected_name] = int(count)

        counter_name = actual_by_key.get("receipt_counters")
        if counter_name:
            count = conn.execute(
                f"SELECT COUNT(*) FROM {quote_identifier(counter_name)}"
            ).fetchone()[0]
            result["table_counts"]["receipt_counters"] = int(count)

        result["quick_check"] = [
            str(row[0]) for row in conn.execute("PRAGMA quick_check;").fetchall()
        ]
        result["foreign_key_violations"] = [
            {
                "table": str(row[0]),
                "rowid": row[1],
                "parent": str(row[2]),
                "foreign_key_id": row[3],
            }
            for row in conn.execute("PRAGMA foreign_key_check;").fetchall()
        ]

        if missing:
            result["issues"].append(
                "Missing required tables: " + ", ".join(missing)
            )
        if result["quick_check"] != ["ok"]:
            details = "; ".join(result["quick_check"]) or "no result"
            result["issues"].append(f"SQLite quick_check failed: {details}")
        if result["foreign_key_violations"]:
            result["issues"].append(
                "Foreign-key violations: "
                f"{len(result['foreign_key_violations'])}"
            )
        if not result["foreign_keys_enabled"]:
            result["issues"].append(
                "Foreign-key enforcement could not be enabled for the "
                "diagnostic connection."
            )

        result["status"] = "PASS" if not result["issues"] else "FAIL"
    except Exception as exc:
        result["issues"].append(
            f"{type(exc).__name__}: {str(exc) or 'Database diagnostic failed'}"
        )
    finally:
        if conn is not None:
            conn.close()
        result["completed_at"] = timestamp()
        result["duration_seconds"] = round(perf_counter() - started_clock, 3)

    return result
