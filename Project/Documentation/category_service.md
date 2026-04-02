# Category Service (quick)

- `add_category(name)`: updates JSON category store only (`category_state`).
- `update_category(old, new)`: validates, calls DB replace (`products_repo.replace_category`) inside a transaction, then calls `refresh_product_cache()` and updates the JSON store. Returns number of products updated.
- `delete_category(name, replacement=None)`: replaces category on `Product_list` rows with a replacement (default 'Other'), calls `refresh_product_cache()`, and removes the category from the JSON store.

References: `modules/ui_utils/category_service.py`, `modules/db_operation/products_repo.py`, `modules/db_operation/product_cache.py`.
