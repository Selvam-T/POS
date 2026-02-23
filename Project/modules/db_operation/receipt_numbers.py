"""Receipt number generation (YYYYMMDD-####)."""

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
        # Avoid nested BEGIN when caller already owns a transaction.
        already_in_tx = False
        try:
            already_in_tx = bool(getattr(c, 'in_transaction', False))
        except Exception:
            already_in_tx = False

        if own or not already_in_tx:
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
