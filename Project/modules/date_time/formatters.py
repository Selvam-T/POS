"""Date/time helpers: parse and format datetimes.

Provides: parse_to_datetime, format_datetime, format_date, format_time.
"""
from __future__ import annotations
import datetime
from typing import Optional

_COMMON_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d-%m-%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%d",
    "%d-%b-%Y %I:%M %p",
    "%d-%b-%Y",
)


def parse_to_datetime(value) -> Optional[datetime.datetime]:
    """Coerce value into datetime or return None on failure."""
    if value is None:
        return None

    # Already a datetime
    if isinstance(value, datetime.datetime):
        return value

    # Date -> promote to datetime
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return datetime.datetime(value.year, value.month, value.day)

    # Numeric timestamp (seconds)
    if isinstance(value, (int, float)):
        try:
            return datetime.datetime.fromtimestamp(float(value))
        except Exception:
            return None

    # Strings: try ISO then common formats
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Try Python's fromisoformat (fast path)
        try:
            return datetime.datetime.fromisoformat(s)
        except Exception:
            pass

        for fmt in _COMMON_FORMATS:
            try:
                return datetime.datetime.strptime(s, fmt)
            except Exception:
                continue

        # If string contains timezone or extra data, best-effort fallback:
        # try to split date/time portion
        try:
            # e.g. '2023-05-01 12:34:56 extra' -> take first two tokens
            parts = s.split()
            if len(parts) >= 2:
                candidate = " ".join(parts[:2])
                for fmt in _COMMON_FORMATS:
                    try:
                        return datetime.datetime.strptime(candidate, fmt)
                    except Exception:
                        continue
        except Exception:
            pass

    return None


def format_datetime(value, fmt: str = "%d %b %Y  %I:%M %p", lower_ampm: bool = True) -> str:
    """Format value as datetime string; empty input -> empty string."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""

    dt = parse_to_datetime(value)
    if dt is None:
        try:
            return str(value)
        except Exception:
            return ""

    out = dt.strftime(fmt)
    if lower_ampm:
        out = out.replace("AM", "am").replace("PM", "pm")
    return out


def format_date(value, fmt: str = "%d %b %Y") -> str:
    """Format only the date portion."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""
    dt = parse_to_datetime(value)
    if dt is None:
        try:
            return str(value)
        except Exception:
            return ""
    return dt.strftime(fmt)


def format_time(value, fmt: str = "%I:%M %p", lower_ampm: bool = True) -> str:
    """Format only the time portion."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""
    dt = parse_to_datetime(value)
    if dt is None:
        try:
            return str(value)
        except Exception:
            return ""
    out = dt.strftime(fmt)
    if lower_ampm:
        out = out.replace("AM", "am").replace("PM", "pm")
    return out
