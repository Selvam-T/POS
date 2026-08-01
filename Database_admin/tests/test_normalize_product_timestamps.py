import sqlite3

import pytest

from audit.verify_db_and_product_list import timestamp_counts as audit_timestamp_counts
from migration.normalize_product_timestamps import normalize_product_timestamps, timestamp_counts


def _connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE Product_list (product_code TEXT, last_updated TEXT)")
    conn.executemany(
        "INSERT INTO Product_list VALUES (?, ?)",
        [
            ("A", "2026-07-03 15:44:20"),
            ("B", "2026-07-09T19:54:57"),
        ],
    )
    conn.commit()
    return conn


def test_normalization_converts_t_separator_transactionally():
    conn = _connection()

    assert normalize_product_timestamps(conn) == 1
    assert timestamp_counts(conn) == {
        "blank": 0,
        "canonical": 2,
        "iso_t": 0,
        "invalid": 0,
    }
    assert conn.execute(
        "SELECT last_updated FROM Product_list WHERE product_code = 'B'"
    ).fetchone()[0] == "2026-07-09 19:54:57"


def test_normalization_rolls_back_on_database_error():
    conn = _connection()
    conn.execute(
        """
        CREATE TRIGGER reject_timestamp_update
        BEFORE UPDATE OF last_updated ON Product_list
        BEGIN
            SELECT RAISE(ABORT, 'forced failure');
        END
        """
    )
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError, match="forced failure"):
        normalize_product_timestamps(conn)

    assert conn.execute(
        "SELECT last_updated FROM Product_list WHERE product_code = 'B'"
    ).fetchone()[0] == "2026-07-09T19:54:57"


def test_database_audit_uses_timestamp_format_counts():
    conn = _connection()

    assert audit_timestamp_counts(conn) == {
        "blank": 0,
        "canonical": 1,
        "iso_t": 1,
        "invalid": 0,
    }
