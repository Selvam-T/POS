"""App-wide product cache.

Location: Project/modules/db_operation/product_cache.py

This module is intentionally UI-free (no PyQt imports).

Cache shape:
    PRODUCT_CACHE: { normalized_product_code: (display_name, selling_price, display_unit) }

Compatibility note:
The rest of the app historically expects:
    found, name, price, unit = get_product_info(code)
so this module preserves that tuple shape.
"""

from typing import Dict, Optional, Tuple

from . import products_repo
from modules.ui_utils.canonicalization import canonicalize_product_code, canonicalize_title_text


# {normalized_product_code: (name, selling_price, unit)}
PRODUCT_CACHE: Dict[str, Tuple[str, float, str]] = {}

# {normalized_product_code: display_product_code}
# Keeps a user-friendly casing for product codes without changing PRODUCT_CACHE tuple shape.
PRODUCT_CODE_DISPLAY: Dict[str, str] = {}


def _norm(s: Optional[str]) -> str:
    """Normalize product code / barcode for cache keys."""
    return canonicalize_product_code(s)


def _to_camel_case(text: Optional[str]) -> str:
    """
    Convert to Title/Camel-ish case for display consistency.
    Keeps simple separators and trims whitespace.
    """
    return canonicalize_title_text(text)


def load_product_cache() -> Dict[str, Tuple[str, float, str]]:
    """
    Full reload from DB into PRODUCT_CACHE.
    Returns the cache dict.
    """
    PRODUCT_CACHE.clear()
    PRODUCT_CODE_DISPLAY.clear()
    rows = products_repo.list_products_slim()

    for product_code, name, selling_price, unit in rows:
        key = _norm(product_code)
        if not key:
            continue

        # Store canonical display code (matches cache key + storage canonicalization).
        PRODUCT_CODE_DISPLAY[key] = key
        name_disp = _to_camel_case(name)
        unit_disp = _to_camel_case(unit) or _to_camel_case('Each')
        PRODUCT_CACHE[key] = (
            name_disp,
            float(selling_price),
            unit_disp,
        )
    return PRODUCT_CACHE


def refresh_product_cache() -> Dict[str, Tuple[str, float, str]]:
    """Alias for load_product_cache()."""
    return load_product_cache()


def get_product_info(product_code: str) -> Tuple[bool, str, float, str]:
    """Cache-only lookup.

    Returns:
      (found, name, selling_price, unit)

    If not found, returns:
      (False, <original_code>, 0.0, 'EACH')
    """
    if not PRODUCT_CACHE:
        load_product_cache()

    raw = str(product_code) if product_code is not None else ""
    key = _norm(raw)
    if not key:
        return False, raw, 0.0, "EACH"

    rec = PRODUCT_CACHE.get(key)
    if rec:
        name, price, unit = rec
        return True, (name if name else raw), float(price), unit

    return False, raw, 0.0, "EACH"


def upsert_cache_item(product_code: str, name: str, selling_price: float, unit: str) -> None:
    """
    Update/add one item in cache (call after product add/update).
    """
    # IMPORTANT: do not re-canonicalize here.
    # Writes should already be canonicalized at the input boundary.
    key = _norm(product_code)
    if not key:
        return
    PRODUCT_CODE_DISPLAY[key] = key
    name_disp = (name or '').strip()
    unit_disp = (unit or '').strip() or 'Each'
    PRODUCT_CACHE[key] = (name_disp, float(selling_price), unit_disp)


def remove_cache_item(product_code: str) -> None:
    """
    Remove from cache (call after product delete).
    """
    target = _norm(product_code)
    if not target:
        return
    PRODUCT_CACHE.pop(target, None)
    PRODUCT_CODE_DISPLAY.pop(target, None)
