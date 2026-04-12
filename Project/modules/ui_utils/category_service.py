from config import PROTECTED_CATEGORIES
from modules.db_operation import products_repo, refresh_product_cache
from modules.db_operation.db import get_conn, transaction
from modules.ui_utils import category_state
from modules.ui_utils.error_logger import log_error_message


def _other_category_name() -> str:
    for item in PROTECTED_CATEGORIES or []:
        if str(item).strip().lower() == 'other':
            return str(item).strip()
    return 'Other'


def _ensure_category_present(name: str) -> None:
    categories = category_state.list_categories() or []
    if any((c or '').strip().lower() == str(name).strip().lower() for c in categories):
        return
    categories.append(str(name).strip())
    try:
        category_state.save_categories(categories)
    except Exception as e:
        log_error_message(f"category_service: ensure replacement category failed: {e}")
        raise


def replace_category_in_db(old_name: str, new_name: str) -> int:
    """Replace category in Product_list only (snapshot model preserves receipts)."""
    conn = get_conn()
    try:
        with transaction(conn):
            products_updated = products_repo.replace_category(old_name, new_name, conn=conn)
            return products_updated
    except Exception as e:
        log_error_message(f"category_service: DB replace failed ({old_name} -> {new_name}): {e}")
        raise
    finally:
        conn.close()


def add_category(name: str) -> None:
    """Add category to JSON store only."""
    category_state.add_category(name)


def update_category(old_name: str, new_name: str) -> int:
    """Rename category in DB tables, then JSON store."""
    old_cat = category_state.Category.from_raw(old_name)
    new_cat = category_state.Category.from_raw(new_name)

    if old_cat.is_protected():
        raise ValueError("Protected category cannot be renamed")
    ok, err = new_cat.validate()
    if not ok:
        raise ValueError(err)
    if new_cat.is_protected():
        raise ValueError("Protected category cannot be used")

    products_updated = replace_category_in_db(old_cat.normalized(), new_cat.normalized())
    refresh_product_cache()
    category_state.update_category(old_cat.normalized(), new_cat.normalized())
    return products_updated


def delete_category(name: str, *, replacement: str | None = None) -> int:
    """Replace category with 'Other' in DB tables, then remove from JSON store."""
    target = category_state.Category.from_raw(name)
    if target.is_protected():
        raise ValueError("Protected category cannot be deleted")

    repl = replacement or _other_category_name()
    _ensure_category_present(repl)
    products_updated = replace_category_in_db(target.normalized(), repl)
    refresh_product_cache()
    category_state.delete_category(target.normalized())
    return products_updated


def list_categories():
    """Return categories from the JSON store."""
    return category_state.list_categories()
