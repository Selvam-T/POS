"""DB operation facade.

This package provides a small, stable public surface for the rest of the app.

Implementation is split into:
- db.py: connection + transaction helpers
- products_repo.py: SQL-only operations
- product_cache.py: in-memory cache + fast lookups
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .product_cache import PRODUCT_CACHE, load_product_cache, refresh_product_cache, get_product_info
from . import products_repo


def get_product_full(product_code: str) -> Tuple[bool, Dict[str, Any]]:
    """Compatibility wrapper around products_repo.get_product_full()."""
    row = products_repo.get_product_full(product_code)
    if not row:
        return False, {}
    # Map repo fields into the names used across the UI.
    unit_val = row.get('unit', '')
    if unit_val is None or str(unit_val).strip() == '':
        unit_val = 'Each'
    return True, {
        'product_code': row.get('product_code', ''),
        'name': row.get('name', ''),
        'category': row.get('category', ''),
        'supplier': row.get('supplier', ''),
        'price': float(row.get('selling_price') or 0.0),
        'cost': float(row.get('cost_price') or 0.0),
        'unit': unit_val,
        'last_updated': row.get('last_updated', ''),
    }


def add_product(
    product_code: str,
    name: str,
    selling_price: float = 0.0,
    category: str = '',
    supplier: str = '',
    cost_price: float = 0.0,
    unit: str = 'EACH',
    last_updated: Optional[str] = None,
) -> Tuple[bool, str]:
    """Add a product row.

    Signature matches existing UI call sites (positional args) and ignores
    last_updated (DB layer owns timestamps).
    """
    try:
        products_repo.add_product(
            product_code=product_code,
            name=name,
            category=category,
            supplier=supplier,
            selling_price=float(selling_price or 0.0),
            cost_price=float(cost_price or 0.0),
            unit=unit,
        )
        return True, 'OK'
    except Exception as e:
        return False, str(e)


def update_product(
    product_code: str,
    name: str = '',
    selling_price: float = 0.0,
    category: str = '',
    supplier: str = '',
    cost_price: float = 0.0,
    unit: str = 'EACH',
) -> Tuple[bool, str]:
    """Update a product row. Returns (ok, message)."""
    try:
        updated = products_repo.update_product(
            product_code,
            name=name,
            category=category,
            supplier=supplier,
            selling_price=float(selling_price or 0.0),
            cost_price=float(cost_price or 0.0),
            unit=unit,
        )
        return (True, 'OK') if updated else (False, 'Product not found')
    except Exception as e:
        return False, str(e)


def delete_product(product_code: str) -> Tuple[bool, str]:
    """Delete a product row. Returns (ok, message)."""
    try:
        deleted = products_repo.delete_product(product_code)
        return (True, 'OK') if deleted else (False, 'Product not found')
    except Exception as e:
        return False, str(e)


__all__ = [
    'PRODUCT_CACHE',
    'load_product_cache',
    'refresh_product_cache',
    'get_product_info',
    'get_product_full',
    'add_product',
    'update_product',
    'delete_product',
]
