import sqlite3

from modules.db_operation.categories_repo import (
    list_categories_with_product_usage,
)


def test_list_categories_with_product_usage_counts_assigned_products():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE Category (
            category_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE Product_list (
            product_code TEXT PRIMARY KEY,
            category_id INTEGER
        );
        INSERT INTO Category(category_id, name) VALUES
            (1, 'Beverages'),
            (2, 'Unused'),
            (3, 'Other');
        INSERT INTO Product_list(product_code, category_id) VALUES
            ('A', 1),
            ('B', 1),
            ('C', 3);
        """
    )

    categories = list_categories_with_product_usage(conn=conn)

    assert categories == [
        {"category_id": 1, "name": "Beverages", "product_count": 2},
        {"category_id": 2, "name": "Unused", "product_count": 0},
        {"category_id": 3, "name": "Other", "product_count": 1},
    ]
