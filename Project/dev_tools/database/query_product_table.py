import sys
import os

# Get the project root from dev_tools/database.
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add that parent directory to the system path
sys.path.append(parent_dir)

from modules.db_operation import get_product_info
import sqlite3
from modules.db_operation.sqlite_runtime import get_db_path

codes = [f"veg0{i}" for i in range(1, 9)]

print("PRODUCT_CACHE:")
for code in codes:
    found, name, price, unit = get_product_info(code)
    print(f"{code}: {name if found else 'NOT FOUND'}: {unit if found else 'N/A'}")

print("\nDB Table (category_id -> Category.name):")
db_path = get_db_path()
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
for code in codes:
    cursor.execute(
        """
        SELECT p.name, p.unit, p.category_id, c.name
          FROM Product_list AS p
          JOIN Category AS c ON c.category_id = p.category_id
         WHERE p.product_code = ? COLLATE NOCASE
        """,
        (code,),
    )
    row = cursor.fetchone()
    print(
        f"{code}: {row[0] if row else 'NOT FOUND'}: "
        f"{row[1] if row else 'N/A'}: "
        f"category_id={row[2] if row else 'N/A'}: "
        f"category={row[3] if row else 'N/A'}"
    )
conn.close()
