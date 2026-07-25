"""SQL-only repository for Category master data."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from .sqlite_runtime import get_conn, transaction


TABLE = "Category"


def list_categories(
    *,
    include_protected: bool = True,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    where = "" if include_protected else "WHERE is_protected = 0"
    sql = f"""
    SELECT category_id, name, is_protected, sort_order
      FROM {TABLE}
      {where}
     ORDER BY
       CASE WHEN name = 'Other' COLLATE NOCASE THEN 1 ELSE 0 END,
       name COLLATE NOCASE
    """
    own = conn is None
    c = conn or get_conn()
    try:
        return [dict(row) for row in c.execute(sql).fetchall()]
    finally:
        if own:
            c.close()


def get_by_name(
    name: str,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Dict[str, Any]]:
    own = conn is None
    c = conn or get_conn()
    try:
        row = c.execute(
            f"""
            SELECT category_id, name, is_protected, sort_order
              FROM {TABLE}
             WHERE name = ? COLLATE NOCASE
            """,
            (str(name or "").strip(),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        if own:
            c.close()


def get_by_id(
    category_id: int,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Dict[str, Any]]:
    own = conn is None
    c = conn or get_conn()
    try:
        row = c.execute(
            f"""
            SELECT category_id, name, is_protected, sort_order
              FROM {TABLE}
             WHERE category_id = ?
            """,
            (int(category_id),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        if own:
            c.close()


def add_category(
    name: str,
    *,
    is_protected: bool = False,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    own = conn is None
    c = conn or get_conn()
    try:
        def _insert() -> int:
            next_order = int(
                c.execute(
                    f"SELECT COALESCE(MAX(sort_order), 0) + 1 FROM {TABLE}"
                ).fetchone()[0]
            )
            cur = c.execute(
                f"""
                INSERT INTO {TABLE} (name, is_protected, sort_order)
                VALUES (?, ?, ?)
                """,
                (str(name).strip(), int(bool(is_protected)), next_order),
            )
            return int(cur.lastrowid)

        if own:
            with transaction(c):
                return _insert()
        return _insert()
    finally:
        if own:
            c.close()


def rename_category(
    category_id: int,
    new_name: str,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> bool:
    own = conn is None
    c = conn or get_conn()
    try:
        def _update() -> bool:
            cur = c.execute(
                f"UPDATE {TABLE} SET name = ? WHERE category_id = ?",
                (str(new_name).strip(), int(category_id)),
            )
            return cur.rowcount > 0

        if own:
            with transaction(c):
                return _update()
        return _update()
    finally:
        if own:
            c.close()


def delete_category(
    category_id: int,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> bool:
    own = conn is None
    c = conn or get_conn()
    try:
        def _delete() -> bool:
            cur = c.execute(
                f"DELETE FROM {TABLE} WHERE category_id = ?",
                (int(category_id),),
            )
            return cur.rowcount > 0

        if own:
            with transaction(c):
                return _delete()
        return _delete()
    finally:
        if own:
            c.close()
