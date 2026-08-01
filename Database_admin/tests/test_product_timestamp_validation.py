from migration.validate_legacy_products import _normalize_last_updated


def test_last_updated_normalizes_supported_storage_formats():
    assert _normalize_last_updated("2026-07-09T19:54:57") == (
        True,
        "2026-07-09 19:54:57",
    )
    assert _normalize_last_updated("2026-07-09 19:54:57") == (
        True,
        "2026-07-09 19:54:57",
    )


def test_last_updated_rejects_noncanonical_values():
    assert _normalize_last_updated("09/07/2026 7:54:57 PM") == (
        False,
        "09/07/2026 7:54:57 PM",
    )
