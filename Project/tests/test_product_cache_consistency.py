import sqlite3

from dev_tools.diagnostics.check_product_cache_consistency import (
    compare_product_cache,
)
from modules.menu.admin_menu import (
    _build_product_data_sql,
    _category_export_data,
)


def test_product_cache_consistency_counts_all_difference_types():
    rows = [
        {
            "product_code": "a1",
            "name": "APPLE_juice",
            "selling_price": 2.5,
            "unit": "each",
            "category": "Beverages",
        },
        {
            "product_code": "B2",
            "name": "Bread",
            "selling_price": 3,
            "unit": "",
            "category": "Bakery",
        },
        {
            "product_code": "C3",
            "name": "Cake",
            "selling_price": 4,
            "unit": "Each",
            "category": "Bakery",
        },
    ]
    cache = {
        "A1": ("Apple Juice", 2.5, "Each", "Beverages"),
        "B2": ("Wrong Bread", 3.0, "Each", "Bakery"),
        "EXTRA": ("Extra", 1.0, "Each", "Other"),
    }

    result = compare_product_cache(rows, cache)

    assert result["database_total"] == 3
    assert result["cache_total"] == 3
    assert result["consistent_total"] == 1
    assert result["inconsistent_total"] == 3
    assert result["missing_from_cache"] == ["C3"]
    assert result["extra_in_cache"] == ["EXTRA"]
    assert result["value_mismatches"] == ["B2"]


def test_category_export_has_id_and_human_readable_name():
    headers, rows = _category_export_data(
        [{"category_id": 7, "name": "Beverages"}]
    )

    assert headers == ["category_id", "category_name"]
    assert rows == [[7, "Beverages"]]


def test_product_data_sql_recreates_category_before_products():
    category_data = (
        """
        CREATE TABLE Category (
            category_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
        """,
        ["category_id", "name"],
        [(7, "Beverages")],
    )
    product_data = (
        """
        CREATE TABLE Product_list (
            product_code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            FOREIGN KEY(category_id) REFERENCES Category(category_id)
        )
        """,
        ["product_code", "name", "category_id"],
        [("P'01", "Cola", 7)],
    )

    sql_text = _build_product_data_sql(
        category_data,
        product_data,
        generated_at="2026-07-25T12:00:00",
    )

    assert sql_text.index("CREATE TABLE Category") < sql_text.index(
        "CREATE TABLE Product_list"
    )
    conn = sqlite3.connect(":memory:")
    conn.executescript(sql_text)
    assert conn.execute(
        """
        SELECT p.product_code, p.name, c.name
          FROM Product_list p
          JOIN Category c ON c.category_id = p.category_id
        """
    ).fetchone() == ("P'01", "Cola", "Beverages")
    conn.close()
