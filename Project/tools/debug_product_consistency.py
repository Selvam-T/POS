"""
DEBUG script for product data consistency.
Counts records in database, PRODUCT_CACHE, and PRODUCT_DROPDOWN_MODEL.
"""

import os
import sys
import sqlite3
# Ensure project root is in sys.path for module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.db_operation import database

DB_PATH = database.DB_PATH

def count_db_records():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Product_list")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def count_product_cache():
    return len(database.PRODUCT_CACHE)

def count_dropdown_model():
    model = database.PRODUCT_DROPDOWN_MODEL
    if model is None:
        return 0
    return model.rowCount()

def print_debug_counts(label):
    print(f"\n--- {label} ---")
    print(f"DB records: {count_db_records()}")
    print(f"PRODUCT_CACHE: {count_product_cache()}")
    print(f"PRODUCT_DROPDOWN_MODEL: {count_dropdown_model()}")

if __name__ == "__main__":
    print_debug_counts("DEBUG1: After app load")
    # For DEBUG2 and DEBUG3, run this script after add/remove in product_menu
