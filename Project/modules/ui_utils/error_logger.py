import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_PATH = os.path.join(BASE_DIR, 'log', 'error.log')

_MONTHS = (
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
)


def _format_timestamp(now: datetime) -> str:
    month = _MONTHS[now.month - 1]
    return (
        f"{now.day:02d} {month} {now.year}, "
        f"{now.hour:02d} : {now.minute:02d} : {now.second:02d} .{now.microsecond:06d}"
    )


def log_error_message(msg):
    """Append error message with timestamp to error.log."""
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(f"{_format_timestamp(datetime.now())} - {msg}\n")
    except Exception:
        pass
