#!/usr/bin/env python3
"""Normalize Product_list text fields to consistent display casing.

This script updates existing rows in the sqlite Product_list table by applying
`_to_camel_case()` to:
- name
- category
- supplier

Default is DRY RUN (no writes). Use --apply to write.

Why this exists:
- Older rows may have been inserted as lowercase (e.g. "castor oil").
- UI displays camel-cased values, so normalizing storage avoids confusion and
  makes name-based searches more predictable.

Usage (from project root):
  python tools/normalize_products.py
  python tools/normalize_products.py --apply

Optional:
  python tools/normalize_products.py --db-path path/to/pos.db --apply
  python tools/normalize_products.py --include-veg --apply
"""

from __future__ import annotations

import datetime
import os

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


def _tool_log(message: str) -> None:
    try:
        root = Path(__file__).resolve().parents[1]
        log_dir = root / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "tools.log"
        ts = datetime.datetime.now().isoformat(timespec="seconds")
        with log_file.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] normalize_products: {message}{os.linesep}")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_operation.db import get_conn, get_db_path, now_iso, transaction  # noqa: E402
from modules.db_operation.product_cache import _to_camel_case  # noqa: E402


@dataclass(frozen=True)
class Change:
    product_code: str
    name_old: str
    name_new: str
    category_old: str
    category_new: str
    supplier_old: str
    supplier_new: str


def _veg_number_from_code(raw: str) -> Optional[int]:
    s = (raw or "").strip()
    if not s or len(s) < 4:
        return None
    if s[:3].casefold() != "veg":
        return None
    tail = s[3:]
    try:
        return int(tail)
    except Exception:
        return None


def is_reserved_veg_code(code: str) -> bool:
    n = _veg_number_from_code(code)
    return n is not None and 1 <= n <= 16


def _norm_text(s: Optional[str]) -> str:
    return (s or "").strip()


def compute_changes(
    rows: Iterable[sqlite3.Row], *, include_veg: bool
) -> List[Change]:
    changes: List[Change] = []
    for r in rows:
        code = _norm_text(r["product_code"])
        if (not include_veg) and is_reserved_veg_code(code):
            continue

        name_old = _norm_text(r["name"])
        category_old = _norm_text(r["category"])
        supplier_old = _norm_text(r["supplier"])

        name_new = _to_camel_case(name_old)
        category_new = _to_camel_case(category_old)
        supplier_new = _to_camel_case(supplier_old)

        if (
            name_new != name_old
            or category_new != category_old
            or supplier_new != supplier_old
        ):
            changes.append(
                Change(
                    product_code=code,
                    name_old=name_old,
                    name_new=name_new,
                    category_old=category_old,
                    category_new=category_new,
                    supplier_old=supplier_old,
                    supplier_new=supplier_new,
                )
            )

    return changes


def _format_change(c: Change) -> str:
    parts: List[str] = []
    if c.name_old != c.name_new:
        parts.append(f"name: '{c.name_old}' -> '{c.name_new}'")
    if c.category_old != c.category_new:
        parts.append(f"category: '{c.category_old}' -> '{c.category_new}'")
    if c.supplier_old != c.supplier_new:
        parts.append(f"supplier: '{c.supplier_old}' -> '{c.supplier_new}'")
    return f"{c.product_code}: " + ", ".join(parts)


def apply_changes(
    conn: sqlite3.Connection,
    changes: List[Change],
    *,
    touch_last_updated: bool,
) -> Tuple[int, List[Tuple[str, str]]]:
    """Returns (applied_count, conflicts).

    Conflicts are returned as list of (product_code, error_message).
    """

    applied = 0
    conflicts: List[Tuple[str, str]] = []

    base_sql = """
    UPDATE Product_list
       SET name = ?,
           category = ?,
           supplier = ?
    """.strip()

    if touch_last_updated:
        base_sql += ",\n           last_updated = ?\n"

    base_sql += " WHERE product_code = ? COLLATE NOCASE"

    with transaction(conn):
        for ch in changes:
            conn.execute("SAVEPOINT sp_norm;")
            try:
                params: List[object] = [ch.name_new, ch.category_new, ch.supplier_new]
                if touch_last_updated:
                    params.append(now_iso())
                params.append(ch.product_code)

                conn.execute(base_sql, tuple(params))
                conn.execute("RELEASE sp_norm;")
                applied += 1
            except sqlite3.IntegrityError as e:
                conn.execute("ROLLBACK TO sp_norm;")
                conn.execute("RELEASE sp_norm;")
                conflicts.append((ch.product_code, str(e)))
            except Exception as e:
                conn.execute("ROLLBACK TO sp_norm;")
                conn.execute("RELEASE sp_norm;")
                conflicts.append((ch.product_code, f"Unexpected error: {e}"))

    return applied, conflicts


def touch_last_updated_for_codes(
    conn: sqlite3.Connection, codes: List[str]
) -> Tuple[int, List[Tuple[str, str]]]:
    """Touch last_updated for specific product codes.

    Returns (touched_count, failures) where failures are (code, error).
    """
    touched = 0
    failures: List[Tuple[str, str]] = []
    if not codes:
        return 0, failures

    sql = "UPDATE Product_list SET last_updated = ? WHERE product_code = ? COLLATE NOCASE"
    now = now_iso()
    with transaction(conn):
        for code in codes:
            conn.execute("SAVEPOINT sp_touch;")
            try:
                cur = conn.execute(sql, (now, code))
                conn.execute("RELEASE sp_touch;")
                if cur.rowcount > 0:
                    touched += 1
                else:
                    failures.append((code, "No such product_code"))
            except Exception as e:
                conn.execute("ROLLBACK TO sp_touch;")
                conn.execute("RELEASE sp_touch;")
                failures.append((code, str(e)))

    return touched, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize Product_list casing via _to_camel_case().")
    parser.add_argument("--apply", action="store_true", help="Write changes to the database (default: dry run)")
    parser.add_argument("--db-path", type=str, default="", help="Override database path")
    parser.add_argument("--include-veg", action="store_true", help="Include Veg01-Veg16 codes (default: skip)")
    parser.add_argument(
        "--touch-last-updated",
        action="store_true",
        help="Also update last_updated to now for changed rows (default: leave unchanged)",
    )
    parser.add_argument(
        "--touch-last-updated-codes",
        nargs="*",
        default=[],
        help="Touch last_updated for these product_code(s) even if there are no casing changes",
    )
    parser.add_argument("--max-show", type=int, default=30, help="Max sample changes to print")

    args = parser.parse_args()

    db_path = args.db_path.strip() or get_db_path()
    _tool_log(f"DB: {db_path}")

    conn = get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT product_code, name, category, supplier FROM Product_list ORDER BY product_code COLLATE NOCASE"
        ).fetchall()

        changes = compute_changes(rows, include_veg=bool(args.include_veg))
        _tool_log(f"Rows scanned: {len(rows)}")
        _tool_log(f"Rows needing change: {len(changes)}")

        if changes:
            for c in changes[: max(0, int(args.max_show))]:
                _tool_log(_format_change(c))
            if len(changes) > int(args.max_show):
                _tool_log(f"... ({len(changes) - int(args.max_show)} more not shown)")

        if not args.apply:
            _tool_log("DRY RUN complete. Use --apply to write changes.")
            return 0

        touch_codes = [str(c).strip() for c in (args.touch_last_updated_codes or []) if str(c).strip()]

        exit_code = 0

        if changes:
            applied, conflicts = apply_changes(conn, changes, touch_last_updated=bool(args.touch_last_updated))
            _tool_log(f"Applied: {applied}/{len(changes)}")
            if conflicts:
                exit_code = 2
                _tool_log(f"Conflicts: {len(conflicts)}")
                for code, msg in conflicts[: max(0, int(args.max_show))]:
                    _tool_log(f"[conflict] {code}: {msg}")
                if len(conflicts) > int(args.max_show):
                    _tool_log(f"... ({len(conflicts) - int(args.max_show)} more conflicts not shown)")

        if touch_codes:
            touched, failures = touch_last_updated_for_codes(conn, touch_codes)
            _tool_log(f"last_updated touched: {touched}/{len(touch_codes)}")
            if failures:
                exit_code = max(exit_code, 2)
                for code, msg in failures[: max(0, int(args.max_show))]:
                    _tool_log(f"[touch-failed] {code}: {msg}")

        if (not changes) and (not touch_codes):
            _tool_log("No changes to apply.")

        _tool_log("Done.")
        return exit_code
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
