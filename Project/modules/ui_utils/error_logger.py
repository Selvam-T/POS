from datetime import datetime
from pathlib import Path

from config import LOG_PATH

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


def ensure_error_log_file(log_path=None) -> str:
    """Create the shared log directory and file when they do not exist."""
    path = Path(log_path or LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    return str(path)


def truncate_error_log(log_path=None) -> str:
    """Empty the shared log file without deleting it."""
    path = Path(ensure_error_log_file(log_path))
    with path.open('w', encoding='utf-8') as log_file:
        log_file.truncate(0)
    return str(path)


def log_error_message(msg, log_path=None):
    """Append error message with timestamp to error.log."""
    try:
        path = Path(ensure_error_log_file(log_path))
        with path.open('a', encoding='utf-8') as log_file:
            log_file.write(f"{_format_timestamp(datetime.now())} - {msg}\n")
    except Exception:
        pass


try:
    ensure_error_log_file()
except Exception:
    pass
