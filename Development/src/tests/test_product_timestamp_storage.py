import sqlite3

from modules.db_operation import products_repo
from dev_tools.maintenance import normalize_products


STORED_AT = "2026-08-01 12:34:56"


def _connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE Product_list (
            product_code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            supplier TEXT,
            selling_price REAL NOT NULL,
            cost_price REAL,
            unit TEXT,
            last_updated TEXT
        )
        """
    )
    return conn


def test_product_writes_use_canonical_storage_timestamp(monkeypatch):
    monkeypatch.setattr(products_repo, "now_db_timestamp", lambda: STORED_AT)
    conn = _connection()

    products_repo.add_product("P1", "Test", 1, conn=conn)
    assert conn.execute(
        "SELECT last_updated FROM Product_list WHERE product_code = 'P1'"
    ).fetchone()[0] == STORED_AT

    products_repo.update_product("P1", name="Updated", conn=conn)
    assert conn.execute(
        "SELECT last_updated FROM Product_list WHERE product_code = 'P1'"
    ).fetchone()[0] == STORED_AT

    assert products_repo.reassign_category(1, 2, conn=conn) == 1
    assert conn.execute(
        "SELECT last_updated FROM Product_list WHERE product_code = 'P1'"
    ).fetchone()[0] == STORED_AT


def test_product_maintenance_uses_canonical_storage_timestamp(monkeypatch):
    monkeypatch.setattr(normalize_products, "now_db_timestamp", lambda: STORED_AT)
    conn = _connection()
    conn.execute(
        "INSERT INTO Product_list VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("P1", "TEST", 1, "SUPPLIER", 1.0, 0.5, "Each", "old"),
    )
    conn.commit()

    change = normalize_products.Change(
        product_code="P1",
        name_old="TEST",
        name_new="Test",
        supplier_old="SUPPLIER",
        supplier_new="Supplier",
    )
    applied, conflicts = normalize_products.apply_changes(
        conn, [change], touch_last_updated=True
    )
    assert (applied, conflicts) == (1, [])
    assert conn.execute(
        "SELECT last_updated FROM Product_list WHERE product_code = 'P1'"
    ).fetchone()[0] == STORED_AT

    conn.execute("UPDATE Product_list SET last_updated = 'old' WHERE product_code = 'P1'")
    conn.commit()
    touched, failures = normalize_products.touch_last_updated_for_codes(conn, ["P1"])
    assert (touched, failures) == (1, [])
    assert conn.execute(
        "SELECT last_updated FROM Product_list WHERE product_code = 'P1'"
    ).fetchone()[0] == STORED_AT
