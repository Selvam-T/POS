"""
Database utilities for POS system.
Provides product cache management and database operations.
"""
import sqlite3
import os
from typing import Dict, Tuple, Optional, Any
from PyQt5.QtWidgets import QStatusBar
from PyQt5.QtCore import QTimer


# Global product cache: {product_code: (name, selling_price, unit)}
# Includes unit for determining if items require weighing (KG) or are count-based (EACH)
PRODUCT_CACHE: Dict[str, Tuple[str, float, str]] = {}

# Note: All barcode validations must use in-memory PRODUCT_CACHE only.

# Database path: Prefer config.DB_PATH; fallback to derived path if config not importable
try:
    from config import DB_PATH as CONFIG_DB_PATH
except Exception:
    CONFIG_DB_PATH = None

# Derived fallback (../db/Anumani.db relative to Project folder)
_DERIVED_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DERIVED_DB_PATH = os.path.join(os.path.dirname(_DERIVED_BASE_DIR), 'db', 'Anumani.db')

DB_PATH = CONFIG_DB_PATH or _DERIVED_DB_PATH


def _norm(code: Optional[str]) -> str:
    """Normalize product codes for consistent cache keys (uppercase, trimmed)."""
    try:
        return str(code).strip().upper()
    except Exception:
        return ''

def _remove_cache_variants(code: str) -> None:
    """Remove any cache entries that match the code case-insensitively."""
    try:
        target = _norm(code)
        if not target:
            return
        to_delete = [k for k in list(PRODUCT_CACHE.keys()) if _norm(k) == target]
        for k in to_delete:
            PRODUCT_CACHE.pop(k, None)
    except Exception:
        pass


def _to_camel_case(text: Optional[str]) -> str:
    """Convert string to CamelCase (title case) while preserving non-alphanumerics.
    - Splits on whitespace, hyphen, underscore
    - Trims leading/trailing spaces
    - Keeps internal separators as single spaces when used for names
    Note: For product codes, this will title-case alphabetic sequences (e.g., abc123 -> Abc123).
    """
    if text is None:
        return ''
    try:
        s = str(text).strip()
        if not s:
            return ''
        # Replace common separators with space for word detection
        for sep in ['\t', '\n', '_', '-']:
            s = s.replace(sep, ' ')
        # Collapse multiple spaces
        parts = [p for p in s.split(' ') if p]
        return ' '.join(w[:1].upper() + w[1:].lower() if w else '' for w in parts)
    except Exception:
        return str(text).strip()


def _normalize_for_compare(text: Optional[str]) -> str:
    """Normalize for comparisons: trim + lower (case-insensitive, ignore outer spaces)."""
    if text is None:
        return ''
    return str(text).strip().lower()


def load_product_cache(db_path: str = DB_PATH) -> bool:
    """Load all products from database into memory cache.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        True if successful, False otherwise
    """
    global PRODUCT_CACHE
    PRODUCT_CACHE.clear()
    
    try:
        if not os.path.exists(db_path):
            # Avoid non-ASCII symbols for Windows console compatibility
            print(f"[WARN] Database not found at: {db_path}")
            return False
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query all products from Product_list table including unit
        cursor.execute("SELECT product_code, name, selling_price, unit FROM Product_list")
        rows = cursor.fetchall()
        
        for row in rows:
            product_code, name, selling_price, unit = row
            PRODUCT_CACHE[_norm(product_code)] = (
                str(name) if name is not None else '',
                float(selling_price) if selling_price is not None else 0.0,
                str(unit).strip().upper() if unit is not None else 'EACH',  # Default to EACH if unit is NULL
            )
        
        conn.close()
        # Cache loaded
        return True

    except sqlite3.Error as e:
        print(f"[DB ERROR] Database error loading products: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error loading product cache: {e}")
        return False


def get_product_info(product_code: str) -> Tuple[bool, str, float, str]:
    """Get product information from cache.
    
    Args:
        product_code: The product barcode/code to lookup
        
    Returns:
        Tuple of (found, name, price, unit)
        - found: True if product exists in cache
        - name: Product name (or product_code if not found)
        - price: Selling price (or 0.0 if not found)
        - unit: Unit type ('KG' or 'EACH', default 'EACH' if not found)
    """
    key_norm = _norm(product_code)
    if key_norm in PRODUCT_CACHE:
        name, price, unit = PRODUCT_CACHE[key_norm]
        return True, (name if name else product_code), float(price), unit
    # Backward compatibility: try raw and lower/upper variants
    raw = str(product_code) if product_code is not None else ''
    if raw in PRODUCT_CACHE:
        name, price, unit = PRODUCT_CACHE[raw]
        return True, (name if name else product_code), float(price), unit
    low = raw.lower()
    if low in PRODUCT_CACHE:
        name, price, unit = PRODUCT_CACHE[low]
        return True, (name if name else product_code), float(price), unit
    up = raw.upper()
    if up in PRODUCT_CACHE:
        name, price, unit = PRODUCT_CACHE[up]
        return True, (name if name else product_code), float(price), unit
    return False, product_code, 0.0, 'EACH'


def get_product_full(product_code: str) -> Tuple[bool, Dict[str, Any]]:
    """Get full product information directly from DB."""
    try:
        if not os.path.exists(DB_PATH):
            return False, {}
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT product_code, name, category, supplier, selling_price, cost_price, unit, last_updated
            FROM Product_list WHERE product_code = ? COLLATE NOCASE
            """,
            (product_code,),
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return False, {}
        (
            code,
            name,
            category,
            supplier,
            selling_price,
            cost_price,
            unit,
            last_updated,
        ) = row
        return True, {
            'code': str(code),
            'name': str(name) if name is not None else '',
            'price': float(selling_price) if selling_price is not None else 0.0,
            'category': str(category) if category is not None else '',
            'supplier': str(supplier) if supplier is not None else '',
            'cost_price': float(cost_price) if cost_price is not None else 0.0,
            'unit': str(unit) if unit is not None else '',
            'last_updated': str(last_updated) if last_updated is not None else '',
        }
    except Exception as e:
        print(f"get_product_full error: {e}")
        return False, {}


def refresh_product_cache(db_path: str = DB_PATH) -> bool:
    """Reload the product cache from database.
    Call this after adding/updating/deleting products.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        True if successful, False otherwise
    """
    return load_product_cache(db_path)


def show_temp_status(status_bar: Optional[QStatusBar], message: str, duration_ms: int = 10000) -> None:
    """Display a temporary message in the status bar.
    Message auto-clears after duration or when another action occurs.
    
    Args:
        status_bar: QStatusBar widget to display message in
        message: Message text to display
        duration_ms: Duration in milliseconds (default 10 seconds)
    """
    if status_bar is None:
        return
    
    try:
        status_bar.showMessage(message)
        # Auto-clear after duration
        QTimer.singleShot(duration_ms, status_bar.clearMessage)
    except Exception as e:
        print(f"Error showing status message: {e}")


# Auto-load cache on module import (silent success)
load_product_cache()


def add_product(
    product_code: str,
    name: str,
    selling_price: float,
    category: Optional[str] = None,
    supplier: Optional[str] = None,
    cost_price: Optional[float] = None,
    unit: Optional[str] = None,
    last_updated: Optional[str] = None,
    db_path: str = DB_PATH,
) -> Tuple[bool, str]:
    """Add a new product to Product_list with full schema fields. Returns (success, message)."""
    try:
        if not os.path.exists(db_path):
            return False, f"Database not found at: {db_path}"
        # Normalize values for storage
        name_norm = _to_camel_case(name)
        code_norm = _to_camel_case(product_code)
        category_norm = _to_camel_case(category) if category is not None else None
        supplier_norm = _to_camel_case(supplier) if supplier is not None else None

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        # Enforce unique name at app level (case-insensitive, trimmed)
        cur.execute("SELECT 1 FROM Product_list WHERE TRIM(name)=TRIM(?) COLLATE NOCASE", (name_norm,))
        if cur.fetchone():
            conn.close()
            return False, "Product name must be unique"
        # Default timestamp if not provided
        if last_updated is None:
            last_updated = _now_str()
        cur.execute(
            """
            INSERT INTO Product_list
                (product_code, name, category, supplier, selling_price, cost_price, unit, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code_norm,
                name_norm,
                category_norm,
                supplier_norm,
                float(selling_price) if selling_price is not None else 0.0,
                float(cost_price) if cost_price is not None else None,
                unit,
                last_updated,
            ),
        )
        conn.commit()
        conn.close()
        # Update cache with name, price, and unit
        # Ensure only normalized key exists in cache
        _remove_cache_variants(code_norm)
        PRODUCT_CACHE[_norm(code_norm)] = (
            str(name_norm) if name_norm is not None else '',
            float(selling_price) if selling_price is not None else 0.0,
            str(unit).strip().upper() if unit is not None else 'EACH',
        )
        return True, "Product added"
    except sqlite3.IntegrityError:
        return False, "Product already exists"
    except sqlite3.Error as e:
        return False, f"DB error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def update_product(
    product_code: str,
    name: Optional[str] = None,
    selling_price: Optional[float] = None,
    category: Optional[str] = None,
    supplier: Optional[str] = None,
    cost_price: Optional[float] = None,
    unit: Optional[str] = None,
    db_path: str = DB_PATH,
) -> Tuple[bool, str]:
    """Update an existing product. Only updates provided fields; always updates last_updated."""
    try:
        if not os.path.exists(db_path):
            return False, f"Database not found at: {db_path}"
        if not product_code:
            return False, "Product code required"
        sets = []
        params = []
        if name is not None:
            name_norm = _to_camel_case(name)
            # Enforce unique name excluding current product
            conn_chk = sqlite3.connect(db_path)
            cur_chk = conn_chk.cursor()
            cur_chk.execute(
                "SELECT 1 FROM Product_list WHERE TRIM(name)=TRIM(?) COLLATE NOCASE AND product_code <> ?",
                (name_norm, product_code),
            )
            exists = cur_chk.fetchone()
            conn_chk.close()
            if exists:
                return False, "Product name must be unique"
            sets.append("name = ?")
            params.append(name_norm)
        if selling_price is not None:
            sets.append("selling_price = ?")
            params.append(float(selling_price))
        if category is not None:
            sets.append("category = ?")
            params.append(_to_camel_case(category))
        if supplier is not None:
            sets.append("supplier = ?")
            params.append(_to_camel_case(supplier))
        if cost_price is not None:
            sets.append("cost_price = ?")
            params.append(float(cost_price))
        if unit is not None:
            sets.append("unit = ?")
            params.append(unit)
        if not sets:
            return False, "No fields to update"
        # Always update last_updated
        sets.append("last_updated = ?")
        params.append(_now_str())
        params.append(product_code)
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(f"UPDATE Product_list SET {', '.join(sets)} WHERE product_code = ?", params)
        if cur.rowcount == 0:
            conn.close()
            return False, "Product not found"
        conn.commit()
        conn.close()
        # Update cache with provided name/price/unit (keep existing if not provided)
        key = _norm(product_code)
        curr_name, curr_price, curr_unit = PRODUCT_CACHE.get(key, ('', 0.0, 'EACH'))
        new_name = curr_name if name is None or str(name) == '' else _to_camel_case(name)
        new_price = curr_price if selling_price is None else float(selling_price)
        new_unit = curr_unit if unit is None else str(unit).strip().upper()
        _remove_cache_variants(product_code)
        PRODUCT_CACHE[key] = (new_name, new_price, new_unit)
        return True, "Product updated"
    except sqlite3.Error as e:
        return False, f"DB error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def delete_product(product_code: str, db_path: str = DB_PATH) -> Tuple[bool, str]:
    """Delete a product by code. Returns (success, message)."""
    try:
        if not os.path.exists(db_path):
            return False, f"Database not found at: {db_path}"
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM Product_list WHERE product_code = ?", (product_code,))
        if cur.rowcount == 0:
            conn.close()
            return False, "Product not found"
        conn.commit()
        conn.close()
        # Remove from slim cache (all variants)
        _remove_cache_variants(product_code)
        return True, "Product deleted"
    except sqlite3.Error as e:
        return False, f"DB error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def _now_str() -> str:
    """Return current local datetime as yyyy-MM-dd HH:mm:ss string without requiring PyQt in DB module."""
    try:
        # Basic portable timestamp using time module
        import time
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    except Exception:
        return ""


# Note: legacy helper _get_name_from_db removed as cache now contains names.
