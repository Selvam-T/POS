"""Normalize Product_list.last_updated to ``YYYY-MM-DD HH:MM:SS``."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


CONFIRMATION = "NORMALIZE-PRODUCT-TIMESTAMPS"
SPACE_PATTERN = "????-??-?? ??:??:??"
T_PATTERN = "????-??-??T??:??:??"


def timestamp_counts(conn: sqlite3.Connection) -> dict[str, int]:
    values = [row[0] for row in conn.execute("SELECT last_updated FROM Product_list")]
    counts = {"blank": 0, "canonical": 0, "iso_t": 0, "invalid": 0}
    for value in values:
        text = "" if value is None else str(value).strip()
        if not text:
            counts["blank"] += 1
        elif len(text) == 19 and text[4] == "-" and text[7] == "-" and text[10] == " ":
            counts["canonical"] += 1
        elif len(text) == 19 and text[4] == "-" and text[7] == "-" and text[10] == "T":
            counts["iso_t"] += 1
        else:
            counts["invalid"] += 1
    return counts


def normalize_product_timestamps(conn: sqlite3.Connection) -> int:
    before = timestamp_counts(conn)
    if before["invalid"]:
        raise RuntimeError(
            f"Refusing normalization: {before['invalid']} invalid last_updated values found"
        )

    try:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute(
            """
            UPDATE Product_list
               SET last_updated = substr(last_updated, 1, 10) || ' ' || substr(last_updated, 12)
             WHERE last_updated GLOB ?
            """,
            (T_PATTERN,),
        )
        updated = int(cursor.rowcount)
        after = timestamp_counts(conn)
        if updated != before["iso_t"]:
            raise RuntimeError(
                f"Timestamp update mismatch: expected {before['iso_t']}, updated {updated}"
            )
        if after["iso_t"] or after["invalid"]:
            raise RuntimeError(f"Timestamp verification failed: {after}")
        conn.commit()
        return updated
    except Exception:
        conn.rollback()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path, help="Explicit database path")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()

    database_path = args.db.resolve()
    if not database_path.is_file():
        raise FileNotFoundError(f"Database not found: {database_path}")
    conn = sqlite3.connect(str(database_path))
    try:
        before = timestamp_counts(conn)
        print(f"Database: {database_path}")
        print(f"Timestamp counts: {before}")
        if args.check_only:
            print("Check-only completed. Database was not modified.")
            return 0
        if args.confirm != CONFIRMATION:
            raise ValueError(f"Supply exactly: --confirm {CONFIRMATION}")
        updated = normalize_product_timestamps(conn)
        print(f"Normalized rows: {updated}")
        print(f"Timestamp counts after: {timestamp_counts(conn)}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
