"""DB operation facade.

This package provides a small, stable public surface for the rest of the app.

Implementation is split into:
- db.py: connection + transaction helpers
- products_repo.py: SQL-only operations
- product_cache.py: in-memory cache + fast lookups
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .product_cache import (
    PRODUCT_CACHE,
    load_product_cache,
    refresh_product_cache,
    get_product_info,
    upsert_cache_item,
    remove_cache_item,
)
from . import products_repo
from .sale_committer import SaleCommitter


def get_product_slim(product_code: str) -> Tuple[bool, str, float, str]:
        """Fast DB lookup for basic fields without loading PRODUCT_CACHE.

        Returns:
            (found, name, selling_price, unit)
        """
        row = products_repo.get_product_slim(product_code)
        if not row:
                return False, '', 0.0, 'EACH'
        name, price, unit = row
        unit_val = unit or 'EACH'
        return True, str(name or ''), float(price or 0.0), str(unit_val)


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
        # Keep in-memory cache consistent with DB (in-place update)
        try:
            upsert_cache_item(product_code, name, float(selling_price or 0.0), unit)
        except Exception as e:
            # Best-effort; UI may still call refresh_product_cache().
            try:
                from modules.ui_utils.error_logger import log_error
                log_error(f"add_product: cache upsert failed for {product_code}: {e}")
            except Exception:
                pass
        return True, 'OK'
    except Exception as e:
        msg = str(e)
        if 'UNIQUE constraint failed' in msg and 'Product_list.name' in msg:
            return False, 'Product name already exists.'
        if 'UNIQUE constraint failed' in msg and 'Product_list.product_code' in msg:
            return False, 'Product code already exists.'
        return False, msg


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
        if not updated:
            return False, 'Product not found'
        # Keep in-memory cache consistent with DB (in-place update)
        try:
            upsert_cache_item(product_code, name, float(selling_price or 0.0), unit)
        except Exception as e:
            try:
                from modules.ui_utils.error_logger import log_error
                log_error(f"update_product: cache upsert failed for {product_code}: {e}")
            except Exception:
                pass
        return True, 'OK'
    except Exception as e:
        msg = str(e)
        if 'UNIQUE constraint failed' in msg and 'Product_list.name' in msg:
            return False, 'Product name already exists.'
        return False, msg


def delete_product(product_code: str) -> Tuple[bool, str]:
    """Delete a product row. Returns (ok, message)."""
    try:
        deleted = products_repo.delete_product(product_code)
        if not deleted:
            return False, 'Product not found'
        # Keep in-memory cache consistent with DB (in-place update)
        try:
            remove_cache_item(product_code)
        except Exception as e:
            try:
                from modules.ui_utils.error_logger import log_error
                log_error(f"delete_product: cache remove failed for {product_code}: {e}")
            except Exception:
                pass
        return True, 'OK'
    except Exception as e:
        return False, str(e)


__all__ = [
    'PRODUCT_CACHE',
    'load_product_cache',
    'refresh_product_cache',
    'get_product_info',
    'get_product_full',
    'get_product_slim',
    'add_product',
    'update_product',
    'delete_product',
    'SaleCommitter',
]
