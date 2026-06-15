import os
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
POS_DIR = os.path.dirname(PROJECT_DIR)
LOG_PATH = os.path.join(POS_DIR, 'log', 'error.log')

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
    hour = now.hour % 12 or 12
    period = "am" if now.hour < 12 else "pm"

    return (
        f"{now.day:02d} {month} {now.year}, "
        #f"{now.hour:02d}:{now.minute:02d}:{now.second:02d} .{now.microsecond:06d}"
        f"{hour}:{now.minute:02d}:{now.second:02d} {period}"
    )


def log_error_message(msg):
    """Append error message with timestamp to error.log."""
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(f"{_format_timestamp(datetime.now())} - {msg}\n")
    except Exception:
        pass
