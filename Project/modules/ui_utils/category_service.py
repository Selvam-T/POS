"""Category business operations backed exclusively by SQLite."""

from __future__ import annotations

from modules.db_operation import categories_repo, products_repo, refresh_product_cache
from modules.db_operation.sqlite_runtime import get_conn, transaction
from modules.ui_utils.input_validation import validate_category


def _validated_name(value: str) -> str:
    name = str(value or "").strip()
    if not name:
        raise ValueError("Category is required")
    ok, error = validate_category(name)
    if not ok:
        raise ValueError(error)
    return name


def _required_category(name: str, *, conn):
    category = categories_repo.get_by_name(name, conn=conn)
    if not category:
        raise ValueError(f"Required category '{name}' is missing")
    return category


def _ensure_mutable(category: dict, operation: str) -> None:
    if bool(category.get("is_protected")):
        name = category.get("name") or "This category"
        raise ValueError(
            f"Category '{name}' is protected and cannot be {operation}."
        )


def list_category_records() -> list[dict]:
    return categories_repo.list_categories()


def list_categories() -> list[str]:
    return [str(row["name"]) for row in list_category_records()]


def get_category_id(name: str) -> int:
    category = categories_repo.get_by_name(str(name or "").strip())
    if not category:
        raise ValueError(f"Category '{name}' does not exist")
    return int(category["category_id"])


def add_category(name: str) -> int:
    clean_name = _validated_name(name)
    try:
        return categories_repo.add_category(clean_name)
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise ValueError(f"Category '{clean_name}' already exists") from exc
        raise


def update_category(old_name: str, new_name: str) -> int:
    clean_new = _validated_name(new_name)
    conn = get_conn()
    try:
        with transaction(conn):
            source = _required_category(old_name, conn=conn)
            _ensure_mutable(source, "replaced")
            target = categories_repo.get_by_name(clean_new, conn=conn)

            if target and int(target["category_id"]) != int(source["category_id"]):
                products_updated = products_repo.reassign_category(
                    int(source["category_id"]),
                    int(target["category_id"]),
                    conn=conn,
                )
                categories_repo.delete_category(
                    int(source["category_id"]),
                    conn=conn,
                )
            else:
                categories_repo.rename_category(
                    int(source["category_id"]),
                    clean_new,
                    conn=conn,
                )
                products_updated = 0
    finally:
        conn.close()

    refresh_product_cache()
    return products_updated


def delete_category(name: str, *, replacement: str | None = None) -> int:
    conn = get_conn()
    try:
        with transaction(conn):
            source = _required_category(name, conn=conn)
            _ensure_mutable(source, "removed")
            replacement_name = replacement or "Other"
            target = _required_category(replacement_name, conn=conn)
            if int(source["category_id"]) == int(target["category_id"]):
                raise ValueError("Replacement category must be different")
            products_updated = products_repo.reassign_category(
                int(source["category_id"]),
                int(target["category_id"]),
                conn=conn,
            )
            categories_repo.delete_category(
                int(source["category_id"]),
                conn=conn,
            )
    finally:
        conn.close()

    refresh_product_cache()
    return products_updated
