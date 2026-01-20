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


# {normalized_product_code: (name, selling_price, unit)}
PRODUCT_CACHE: Dict[str, Tuple[str, float, str]] = {}

# {normalized_product_code: display_product_code}
# Keeps a user-friendly casing for product codes without changing PRODUCT_CACHE tuple shape.
PRODUCT_CODE_DISPLAY: Dict[str, str] = {}


def _norm(s: Optional[str]) -> str:
        """Normalize product code / barcode for cache keys."""
        return (s or "").strip().upper()


def _to_camel_case(text: Optional[str]) -> str:
    """
    Convert to Title/Camel-ish case for display consistency.
    Keeps simple separators and trims whitespace.
    """
    s = (text or "").strip()
    if not s:
        return ""
    # replace common separators with space
    for ch in ("_", "-", "\t"):
        s = s.replace(ch, " ")
    # collapse whitespace
    parts = [p for p in s.split(" ") if p]
    return " ".join([p[:1].upper() + p[1:].lower() if p else "" for p in parts])


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
        # Store a display casing for code (canonical "camel/title-ish"), while keeping
        # cache keys normalized for fast case-insensitive lookup.
        PRODUCT_CODE_DISPLAY[key] = _to_camel_case(product_code) or str(product_code or '').strip()
        unit_disp = _to_camel_case(unit) or _to_camel_case('Each')
        PRODUCT_CACHE[key] = (
            _to_camel_case(name),
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
    unit_disp = _to_camel_case(unit) or _to_camel_case('Each')
    key = _norm(product_code)
    PRODUCT_CODE_DISPLAY[key] = _to_camel_case(product_code) or str(product_code or '').strip()
    PRODUCT_CACHE[key] = (
        _to_camel_case(name),
        float(selling_price),
        unit_disp,
    )


def remove_cache_item(product_code: str) -> None:
    """
    Remove from cache (call after product delete).
    """
    target = _norm(product_code)
    if not target:
        return
    PRODUCT_CACHE.pop(target, None)
    PRODUCT_CODE_DISPLAY.pop(target, None)
