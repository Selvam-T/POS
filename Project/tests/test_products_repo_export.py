import os
import sqlite3
import tempfile
import unittest
from modules.db_operation.sqlite_runtime import get_conn
from modules.db_operation import categories_repo, products_repo


class TestProductsRepoExport(unittest.TestCase):
    def test_get_product_list_schema_and_rows(self):
        # Create a temporary sqlite file
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            conn = get_conn(db_path=path)
            try:
                cur = conn.cursor()
                # Create Product_list table
                cur.execute(
                    """
                    CREATE TABLE Product_list (
                        product_code TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        selling_price REAL NOT NULL,
                        category_id INTEGER NOT NULL,
                        supplier TEXT,
                        cost_price REAL,
                        unit TEXT,
                        last_updated TEXT
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE Category (
                        category_id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE
                    )
                    """
                )
                cur.execute("INSERT INTO Category(category_id, name) VALUES (1, 'Fruit')")
                # Insert two rows
                cur.execute(
                    "INSERT INTO Product_list (product_code, name, selling_price, category_id, supplier, cost_price, unit, last_updated) VALUES (?,?,?,?,?,?,?,datetime('now'))",
                    ("P1", "Apple", 1.5, 1, "Farm", 0.5, "EACH"),
                )
                cur.execute(
                    "INSERT INTO Product_list (product_code, name, selling_price, category_id, supplier, cost_price, unit, last_updated) VALUES (?,?,?,?,?,?,?,datetime('now'))",
                    ("P2", "Banana", 0.8, 1, "Farm", 0.3, "EACH"),
                )
                conn.commit()

                # Call helper
                create_sql, headers, rows = products_repo.get_product_list_schema_and_rows(conn=conn)

                self.assertIsNotNone(create_sql)
                self.assertIn('CREATE TABLE', create_sql.upper())
                self.assertIsInstance(headers, list)
                self.assertTrue(len(headers) >= 1)
                self.assertEqual(len(rows), 2)

                readable_headers, readable_rows = (
                    products_repo.get_product_list_readable_rows(conn=conn)
                )
                self.assertIn("category", readable_headers)
                self.assertNotIn("category_id", readable_headers)
                category_index = readable_headers.index("category")
                self.assertEqual(
                    [row[category_index] for row in readable_rows],
                    ["Fruit", "Fruit"],
                )

                category_sql, category_headers, category_rows = (
                    categories_repo.get_category_schema_and_rows(conn=conn)
                )
                self.assertIn("CREATE TABLE", category_sql.upper())
                self.assertEqual(category_headers, ["category_id", "name"])
                self.assertEqual([tuple(row) for row in category_rows], [(1, "Fruit")])
            finally:
                conn.close()
        finally:
            try:
                os.remove(path)
            except Exception:
                pass


if __name__ == '__main__':
    unittest.main()
