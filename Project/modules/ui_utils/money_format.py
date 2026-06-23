"""Shared currency display and numeric coercion helpers."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


def money_value(value: Any, *, default: float = 0.0) -> float:
    """Return a numeric currency value, accepting display strings too."""
    if value is None:
        return float(default)
    try:
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return float(default)
            negative = text.startswith('(') and text.endswith(')')
            text = text.strip('()').replace('$', '').replace(',', '').strip()
            amount = float(text)
            return -amount if negative else amount
        return float(value)
    except Exception:
        return float(default)


def format_number(value: Any, *, decimals: int = 2, grouped: bool = True) -> str:
    """Format a number for display without a currency symbol."""
    try:
        amount = Decimal(str(money_value(value))).quantize(
            Decimal('1').scaleb(-int(decimals)),
            rounding=ROUND_HALF_UP,
        )
    except (InvalidOperation, ValueError):
        amount = Decimal('0').quantize(Decimal('1').scaleb(-int(decimals)))

    grouping = ',' if grouped else ''
    return f"{amount:{grouping}.{int(decimals)}f}"


def format_currency(value: Any) -> str:
    """Format a display currency value as '$ 1,234.56'."""
    return f"$ {format_number(value, decimals=2, grouped=True)}"


def round_money(value: Any, *, decimals: int = 2, default: float = 0.0) -> float:
    """Round a currency value to the normal display precision."""
    try:
        amount = Decimal(str(money_value(value, default=default))).quantize(
            Decimal('1').scaleb(-int(decimals)),
            rounding=ROUND_HALF_UP,
        )
        return float(amount)
    except (InvalidOperation, ValueError):
        return float(default)


def round_cash_005(value: Any) -> float:
    """Round a cash-settlement amount to the nearest 5 cents."""
    amount = Decimal(str(money_value(value)))
    rounded = (amount / Decimal('0.05')).quantize(
        Decimal('1'),
        rounding=ROUND_HALF_UP,
    ) * Decimal('0.05')
    return float(rounded.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def format_cash_currency(value: Any) -> str:
    """Format a cash-settlement amount after nearest-5-cent rounding."""
    return format_currency(round_cash_005(value))
