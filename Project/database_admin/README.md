# Database Admin Notes

## Product Name Uniqueness Constraint

The `Product_list` table enforces uniqueness of product names at the database level using a unique index with case-insensitive collation. This ensures that no two products can have the same name, regardless of letter case.

### SQL Schema

The relevant constraint is implemented as:

```sql
CREATE UNIQUE INDEX uq_product_name_nocase ON Product_list(name COLLATE NOCASE);
```

This means that attempts to insert or update a product with a name that already exists (case-insensitive) will result in a database error (sqlite3.IntegrityError).

### Application Behavior

- When adding or updating a product, the application checks for this constraint and provides a clear error message if a duplicate name is detected.
- The error message is displayed to the user via the status label in the UI.

### Example

Attempting to add two products with names 'Apple' and 'apple' will fail on the second insert or update, as the names are considered identical by the database.

---

For more details, see the `Product_list` table schema and the application logic in `modules/db_operation/database.py`.
