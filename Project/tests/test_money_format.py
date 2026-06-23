from modules.ui_utils.money_format import (
    format_cash_currency,
    format_currency,
    format_number,
    money_value,
    round_cash_005,
    round_money,
)


def test_format_currency_uses_shared_display_style():
    assert format_currency(1234.5) == "$ 1,234.50"
    assert format_currency(0) == "$ 0.00"


def test_format_currency_is_defensive_for_display():
    assert format_currency(None) == "$ 0.00"
    assert format_currency("not money") == "$ 0.00"


def test_money_value_accepts_currency_display_strings():
    assert money_value("$ 1,234.50") == 1234.5
    assert money_value("($ 12.30)") == -12.3


def test_format_number_can_keep_plain_numeric_display():
    assert format_number(1234.5) == "1,234.50"
    assert format_number(1234.5, grouped=False) == "1234.50"


def test_round_money_uses_display_precision():
    assert round_money(1.005) == 1.01
    assert round_money("not money") == 0.0


def test_round_cash_005_rounds_to_nearest_five_cents():
    expected = {
        1.00: 1.00,
        1.01: 1.00,
        1.02: 1.00,
        1.03: 1.05,
        1.04: 1.05,
        1.05: 1.05,
        1.06: 1.05,
        1.07: 1.05,
        1.08: 1.10,
        1.09: 1.10,
        1.10: 1.10,
    }

    for value, rounded in expected.items():
        assert round_cash_005(value) == rounded


def test_format_cash_currency_uses_nearest_five_cent_rounding():
    assert format_cash_currency(1.01) == "$ 1.00"
    assert format_cash_currency(1.09) == "$ 1.10"
