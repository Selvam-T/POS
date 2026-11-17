"""App-wide product cache."""

from typing import Dict, Optional, Tuple

from . import products_repo
from modules.ui_utils.canonicalization import canonicalize_product_code, canonicalize_title_text


PRODUCT_CACHE: Dict[str, Tuple[str, float, str, str]] = {}

PRODUCT_CODE_DISPLAY: Dict[str, str] = {}


def _norm(s: Optional[str]) -> str:
    """Normalize product code for cache keys."""
    return canonicalize_product_code(s)


def _to_camel_case(text: Optional[str]) -> str:
    """Normalize display text."""
    return canonicalize_title_text(text)


def load_product_cache() -> Dict[str, Tuple[str, float, str, str]]:
    """Reload and return PRODUCT_CACHE."""
    PRODUCT_CACHE.clear()
    PRODUCT_CODE_DISPLAY.clear()
    # Use the full product list so we can include category in the cache.
    rows = products_repo.list_products()

    for rec in rows:
        product_code = rec.get('product_code') or ''
        name = rec.get('name') or ''
        selling_price = rec.get('selling_price') or 0.0
        unit = rec.get('unit') or ''
        category = rec.get('category') or ''

        key = _norm(product_code)
        if not key:
            continue

        PRODUCT_CODE_DISPLAY[key] = key
        name_disp = _to_camel_case(name)
        unit_disp = _to_camel_case(unit) or _to_camel_case('Each')
        cat_disp = (category or '').strip()
        PRODUCT_CACHE[key] = (
            name_disp,
            float(selling_price),
            unit_disp,
            cat_disp,
        )
    return PRODUCT_CACHE


def refresh_product_cache() -> Dict[str, Tuple[str, float, str, str]]:
    """Alias for load_product_cache()."""
    # test error handling
    #raise RuntimeError('Simulated PRODUCT_CACHE reload failure (debug)')
    return load_product_cache()


def get_product_info(product_code: str) -> Tuple[bool, str, float, str]:
    """Return (found, name, selling_price, unit)."""
    if not PRODUCT_CACHE:
        load_product_cache()

    raw = str(product_code) if product_code is not None else ""
    key = _norm(raw)
    if not key:
        return False, raw, 0.0, "EACH"

    rec = PRODUCT_CACHE.get(key)
    if rec:
        # rec shape: (name, price, unit, category)
        name, price, unit = rec[0], rec[1], rec[2]
        return True, (name if name else raw), float(price), unit

    return False, raw, 0.0, "EACH"


def upsert_cache_item(product_code: str, name: str, selling_price: float, unit: str, category: str = '') -> None:
    """Update or insert one cache item (includes category)."""
    key = _norm(product_code)
    if not key:
        return
    PRODUCT_CODE_DISPLAY[key] = key
    name_disp = (name or '').strip()
    unit_disp = (unit or '').strip() or 'Each'
    cat_disp = (category or '').strip()
    PRODUCT_CACHE[key] = (name_disp, float(selling_price), unit_disp, cat_disp)


def remove_cache_item(product_code: str) -> None:
    """Remove one cache item."""
    target = _norm(product_code)
    if not target:
        return
    PRODUCT_CACHE.pop(target, None)
    PRODUCT_CODE_DISPLAY.pop(target, None)
