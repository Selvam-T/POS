"""Trial-build expiry and clock-rollback checks."""

from datetime import date, datetime, timezone

import config

try:
    from modules.runtime.trial_build import BUILD_TIMESTAMP_UTC
except Exception:
    BUILD_TIMESTAMP_UTC = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _as_utc_datetime(value) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return _as_utc_datetime(parsed)
    raise TypeError(f"Unsupported build timestamp: {value!r}")


def build_timestamp_utc() -> datetime:
    return _as_utc_datetime(BUILD_TIMESTAMP_UTC)


def trial_expired_reason(now: datetime | None = None) -> str | None:
    if not bool(getattr(config, 'TRIAL_BUILD_ENABLED', False)):
        return None

    current = _as_utc_datetime(now or datetime.now(timezone.utc))
    try:
        build_timestamp = build_timestamp_utc()
    except Exception:
        return 'INVALID_BUILD_TIMESTAMP'

    if current < build_timestamp:
        return 'CLOCK_ROLLBACK'

    expiry = getattr(config, 'TRIAL_EXPIRY_DATE', None)
    if not isinstance(expiry, date):
        return 'INVALID_EXPIRY_DATE'

    if current.date() > expiry:
        return 'EXPIRED'

    return None


def is_trial_expired(now: datetime | None = None) -> bool:
    return trial_expired_reason(now) is not None


def trial_expired_message() -> str:
    return str(
        getattr(
            config,
            'TRIAL_EXPIRED_MESSAGE',
            'Testing period expired. Please contact SelvamPOS support.',
        )
    )
