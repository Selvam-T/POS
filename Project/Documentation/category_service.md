# Category Service

Categories are master data in SQLite `Category`; JSON category storage no
longer exists.

- `list_category_records()` returns IDs, names, protected status, and ordering.
- `list_categories()` returns display names.
- `get_category_id(name)` resolves required system categories such as
  `Vegetable`.
- `add_category(name)` validates and inserts one Category row.
- `update_category(old, new)` renames in place when `new` is unused. If `new`
  already exists, products are reassigned and the old row is deleted as a
  merge.
- `delete_category(name)` transactionally reassigns products to `Other`, then
  deletes the selected Category row.

`Other` and `Vegetable` have `is_protected = 1`. Attempts to remove or replace
them raise an informative validation message. Successful rename, merge, and
delete operations refresh `PRODUCT_CACHE` after commit.

`receipt_items.category` remains historical snapshot text and is never changed.

References: `modules/ui_utils/category_service.py`,
`modules/db_operation/categories_repo.py`,
`modules/db_operation/products_repo.py`, and
`modules/db_operation/product_cache.py`.
