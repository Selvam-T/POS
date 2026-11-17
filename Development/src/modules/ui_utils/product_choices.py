"""Shared product-derived choice builders for POS dialogs."""

from __future__ import annotations

from typing import Mapping


def normalize_product_choice_name(value: object) -> str:
    """Trim surrounding whitespace while preserving stored name content."""
    return str(value or "").strip()


def build_product_name_choices(product_cache: Mapping | None) -> list[str]:
    """Build a sorted name for every nonempty PRODUCT_CACHE record."""
    choices = []
    for record in (product_cache or {}).values():
        name = normalize_product_choice_name(
            record[0]
            if isinstance(record, (tuple, list)) and record
            else ""
        )
        if not name:
            continue
        choices.append(name)
    return sorted(choices, key=str.casefold)
