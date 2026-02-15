"""
Receipt number generation.

Location: Project/modules/db_operation/receipt_numbers.py

Format: YYYYMMDD-#### (counter max 9999)
Resets daily.

Implementation uses a small helper table:
  receipt_counters(date TEXT PRIMARY KEY, counter INTEGER NOT NULL)

You can replace this later with your own receipt table-based logic if you prefer.
"""

import sqlite3
from datetime import date, datetime
from typing import Optional

from .db import get_conn, transaction


_COUNTER_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS receipt_counters (
  date TEXT PRIMARY KEY,
  counter INTEGER NOT NULL
);
"""


def _yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def next_receipt_no(for_date: Optional[date] = None, *, conn: Optional[sqlite3.Connection] = None) -> str:
    d = for_date or datetime.now().date()
    day = _yyyymmdd(d)

    own = conn is None
    c = conn or get_conn()
    try:
        # If caller provided a connection that is already inside a transaction,
        # avoid starting another transaction here (SQLite does not support
        # nested BEGIN). Use the active transaction context instead.
        already_in_tx = False
        try:
            already_in_tx = bool(getattr(c, 'in_transaction', False))
        except Exception:
            already_in_tx = False

        if own or not already_in_tx:
            # Own connection or external connection not currently in transaction:
            # use the transaction wrapper to ensure BEGIN IMMEDIATE semantics.
            with transaction(c):
                c.execute(_COUNTER_TABLE_SQL)
                row = c.execute(
                    "SELECT counter FROM receipt_counters WHERE date = ?",
                    (day,)
                ).fetchone()

                if row:
                    nxt = row["counter"] + 1
                    c.execute(
                        "UPDATE receipt_counters SET counter = ? WHERE date = ?",
                        (nxt, day)
                    )
                else:
                    nxt = 1
                    c.execute(
                        "INSERT INTO receipt_counters (date, counter) VALUES (?, ?)",
                        (day, nxt)
                    )

                if nxt > 9999:
                    raise ValueError(f"Counter exceeded 9999 for {day}")

                return f"{day}-{nxt:04d}"
        else:
            # Connection provided and already in a transaction: do not call
            # transaction() again; perform the counter update inline so the
            # outer transaction controls atomicity.
            c.execute(_COUNTER_TABLE_SQL)
            row = c.execute(
                "SELECT counter FROM receipt_counters WHERE date = ?",
                (day,)
            ).fetchone()

            if row:
                nxt = row["counter"] + 1
                c.execute(
                    "UPDATE receipt_counters SET counter = ? WHERE date = ?",
                    (nxt, day)
                )
            else:
                nxt = 1
                c.execute(
                    "INSERT INTO receipt_counters (date, counter) VALUES (?, ?)",
                    (day, nxt)
                )

            if nxt > 9999:
                raise ValueError(f"Counter exceeded 9999 for {day}")

            return f"{day}-{nxt:04d}"
    finally:
        if own:
            c.close()
