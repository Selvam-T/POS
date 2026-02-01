import sys
import os

# Get the directory of the current script, then go up one level
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Add that parent directory to the system path
sys.path.append(parent_dir)

from modules.db_operation import PRODUCT_CACHE, get_product_info
import sqlite3
from modules.db_operation.db import get_db_path

codes = [f"veg0{i}" for i in range(1, 9)]

print("PRODUCT_CACHE:")
for code in codes:
    found, name, price, unit = get_product_info(code)
    print(f"{code}: {name if found else 'NOT FOUND'}: {unit if found else 'N/A'}")

print("\nDB Table:")
db_path = get_db_path()
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
for code in codes:
    cursor.execute("SELECT name, unit, category FROM Product_list WHERE product_code = ? COLLATE NOCASE", (code,))
    row = cursor.fetchone()
    print(f"{code}: {row[0] if row else 'NOT FOUND'}: {row[1] if row else 'N/A'}: {row[2] if row else 'N/A'}")
conn.close()