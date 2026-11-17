from modules.ui_utils.input_validation import validate_product_name


def test_add_rejects_name_assigned_to_another_product(monkeypatch):
    monkeypatch.setattr(
        "modules.db_operation.product_cache.PRODUCT_CACHE",
        {"P1": ("Mg Yoghurt", 1.0, "Each", "Dairy")},
    )

    ok, error = validate_product_name("mg yoghurt")

    assert not ok
    assert error == "Product name already exists"


def test_update_allows_current_product_to_retain_its_unique_name(monkeypatch):
    monkeypatch.setattr(
        "modules.db_operation.product_cache.PRODUCT_CACHE",
        {
            "P1": ("Mg Yoghurt", 1.0, "Each", "Dairy"),
            "P2": ("Fresh Milk", 2.0, "Each", "Dairy"),
        },
    )

    ok, error = validate_product_name("MG Yoghurt", exclude_code="P1")

    assert ok
    assert error == ""


def test_update_rejects_renaming_to_another_products_name(monkeypatch):
    monkeypatch.setattr(
        "modules.db_operation.product_cache.PRODUCT_CACHE",
        {
            "P1": ("Mg Yoghurt", 1.0, "Each", "Dairy"),
            "P2": ("Fresh Milk", 2.0, "Each", "Dairy"),
        },
    )

    ok, error = validate_product_name("Fresh Milk", exclude_code="P1")

    assert not ok
    assert error == "Product name already exists"
