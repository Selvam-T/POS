import datetime

from modules.db_operation.sqlite_runtime import now_db_timestamp
from modules.date_time.formatters import format_datetime


def test_now_db_timestamp_uses_space_separated_storage_format():
    value = now_db_timestamp()

    assert "T" not in value
    assert len(value) == 19
    assert datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def test_product_timestamp_display_remains_user_friendly():
    expected = "03 Jul 2026  03:44 pm"

    assert format_datetime("2026-07-03 15:44:20") == expected
    assert format_datetime("2026-07-03T15:44:20") == expected
