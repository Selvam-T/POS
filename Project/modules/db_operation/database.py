"""
Database utilities for POS system.
Provides product cache management and database operations.
"""
import sqlite3
import os
from typing import Dict, Tuple, Optional
from PyQt5.QtWidgets import QStatusBar
from PyQt5.QtCore import QTimer


# Global product cache: {product_code: {'name': str, 'price': float}}
PRODUCT_CACHE: Dict[str, Dict[str, any]] = {}

# Note: All barcode validations must use in-memory PRODUCT_CACHE only.

# Database path: ../db/Anumani.db relative to Project folder
# Since this file is now in modules/db_operation/, we need to go up 2 levels to Project, then 1 more to POS
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(os.path.dirname(BASE_DIR), 'db', 'Anumani.db')


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
            print(f"✗ Database not found at: {db_path}")
            return False
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query all products from Product_list table
        cursor.execute("""
            SELECT product_code, name, selling_price 
            FROM Product_list
        """)
        
        rows = cursor.fetchall()
        
        for row in rows:
            product_code, name, price = row
            PRODUCT_CACHE[str(product_code)] = {
                'name': str(name),
                'price': float(price)
            }
        
        conn.close()
        print(f"✓ Loaded {len(PRODUCT_CACHE)} products into cache from {db_path}")
        return True
        
    except sqlite3.Error as e:
        print(f"✗ Database error loading products: {e}")
        return False
    except Exception as e:
        print(f"✗ Error loading product cache: {e}")
        return False


def get_product_info(product_code: str) -> Tuple[bool, str, float]:
    """Get product information from cache.
    
    Args:
        product_code: The product barcode/code to lookup
        
    Returns:
        Tuple of (found, name, price)
        - found: True if product exists in cache
        - name: Product name (or product_code if not found)
        - price: Selling price (or 0.0 if not found)
    """
    if product_code in PRODUCT_CACHE:
        product = PRODUCT_CACHE[product_code]
        return True, product['name'], product['price']
    else:
        return False, product_code, 0.0


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


# Auto-load cache on module import
print(f"Database path: {DB_PATH}")
load_product_cache()
