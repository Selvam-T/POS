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
    """
    Get the next receipt number for a given date.
    - Uses a transaction for correctness under concurrent cashiers.
    """
    d = for_date or datetime.now().date()
    day = _yyyymmdd(d)

    own = conn is None
    c = conn or get_conn()
    try:
        with transaction(c):
            c.execute(_COUNTER_TABLE_SQL)
            row = c.execute("SELECT counter FROM receipt_counters WHERE date = ?", (day,)).fetchone()
            current = int(row["counter"]) if row else 0
            nxt = current + 1
            if nxt > 9999:
                raise ValueError("Receipt counter exceeded 9999 for date %s" % day)

            if row:
                c.execute("UPDATE receipt_counters SET counter = ? WHERE date = ?", (nxt, day))
            else:
                c.execute("INSERT INTO receipt_counters(date, counter) VALUES (?, ?)", (day, nxt))

            return f"{day}-{nxt:04d}"
    finally:
        if own:
            c.close()
