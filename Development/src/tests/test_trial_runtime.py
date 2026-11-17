from datetime import date, datetime, timezone

import config
from modules.runtime import trial


def test_trial_disabled_never_expires(monkeypatch):
    monkeypatch.setattr(config, 'TRIAL_BUILD_ENABLED', False)
    monkeypatch.setattr(config, 'TRIAL_EXPIRY_DATE', date(2026, 6, 30))
    monkeypatch.setattr(
        trial,
        'BUILD_TIMESTAMP_UTC',
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert trial.is_trial_expired(datetime(2099, 1, 1, tzinfo=timezone.utc)) is False


def test_trial_allows_login_through_expiry_date(monkeypatch):
    monkeypatch.setattr(config, 'TRIAL_BUILD_ENABLED', True)
    monkeypatch.setattr(config, 'TRIAL_EXPIRY_DATE', date(2026, 6, 30))
    monkeypatch.setattr(
        trial,
        'BUILD_TIMESTAMP_UTC',
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert trial.is_trial_expired(
        datetime(2026, 6, 30, 23, 59, 59, tzinfo=timezone.utc)
    ) is False


def test_trial_expires_after_expiry_date(monkeypatch):
    monkeypatch.setattr(config, 'TRIAL_BUILD_ENABLED', True)
    monkeypatch.setattr(config, 'TRIAL_EXPIRY_DATE', date(2026, 6, 30))
    monkeypatch.setattr(
        trial,
        'BUILD_TIMESTAMP_UTC',
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert trial.trial_expired_reason(
        datetime(2026, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
    ) == 'EXPIRED'


def test_trial_blocks_clock_rollback_before_build_time(monkeypatch):
    monkeypatch.setattr(config, 'TRIAL_BUILD_ENABLED', True)
    monkeypatch.setattr(config, 'TRIAL_EXPIRY_DATE', date(2026, 6, 30))
    monkeypatch.setattr(
        trial,
        'BUILD_TIMESTAMP_UTC',
        datetime(2026, 6, 23, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert trial.trial_expired_reason(
        datetime(2026, 6, 23, 11, 59, 59, tzinfo=timezone.utc)
    ) == 'CLOCK_ROLLBACK'
