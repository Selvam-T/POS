import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from config import (
    PRODUCT_CATEGORIES,
    PROTECTED_CATEGORIES,
    CATEGORIES_JSON_BACKUP_PREFIX,
    CATEGORIES_JSON_PATH,
)
from modules.wrappers.settings import appdata_path
from modules.ui_utils.input_validation import validate_category
from modules.ui_utils.error_logger import log_error

_CATEGORY_NAME = 'categories'


class Category:
    # Lightweight model with validation helpers for category names.
    def __init__(self, name: str):
        self.name = str(name or '').strip()

    @classmethod
    def from_raw(cls, value: str) -> 'Category':
        return cls(value)

    def normalized(self) -> str:
        return self.name

    def key(self) -> str:
        return _normalize_key(self.name)

    def is_protected(self) -> bool:
        return is_protected_category(self.name)

    def validate(self) -> Tuple[bool, str]:
        return validate_category(self.name)


def _categories_path() -> Path:
    # Resolve the JSON path (config path preferred; fallback to appdata helper).
    try:
        path = Path(CATEGORIES_JSON_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    except Exception:
        return appdata_path(_CATEGORY_NAME)


def _timestamp() -> str:
    # Timestamp suffix for backups/corrupt files.
    return datetime.now().strftime('%Y%m%dT%H%M%S')


def _archive_corrupt(path: Path) -> None:
    # Preserve corrupt JSON so it can be inspected later.
    try:
        backup = path.with_name(f"{path.name}.corrupt.{_timestamp()}")
        os.replace(str(path), str(backup))
    except Exception as e:
        log_error(f"category_state: archive corrupt failed: {e}")


def _validate_categories_data(data) -> Tuple[bool, str]:
    # File-level shape check; input validation happens elsewhere.
    if not isinstance(data, dict):
        return False, 'Root must be an object'
    categories = data.get('categories')
    if not isinstance(categories, list):
        return False, 'categories must be a list'
    for item in categories:
        if not isinstance(item, str):
            return False, 'categories items must be strings'
    return True, ''


def _normalize_seed(categories: List[str]) -> List[str]:
    # Trim and drop empty values from seed list.
    clean = []
    for item in categories or []:
        text = str(item or '').strip()
        if text:
            clean.append(text)
    return clean


def _other_name() -> str:
    for item in PROTECTED_CATEGORIES or []:
        if str(item).strip().lower() == 'other':
            return str(item).strip()
    return 'Other'


def _order_categories(categories: List[str]) -> List[str]:
    # Keep first item as placeholder, sort the rest, and keep 'Other' last.
    if not categories:
        return []

    placeholder = categories[0]
    rest = categories[1:]

    other_name = _other_name()
    other_items = [c for c in rest if _normalize_key(c) == _normalize_key(other_name)]
    rest = [c for c in rest if _normalize_key(c) != _normalize_key(other_name)]

    rest_sorted = sorted(rest, key=lambda x: (x or '').casefold())
    ordered = [placeholder] + rest_sorted
    if other_items:
        ordered.append(other_name)
    return ordered


def _normalize_key(value: str) -> str:
    # Normalize for uniqueness checks. (Snacks vs snacks)
    return str(value or '').strip().casefold()


def _enforce_unique(categories: List[str]) -> None:
    # Reject duplicates (case-insensitive) before persisting JSON.
    seen = set()
    for item in categories or []:
        key = _normalize_key(item)
        if not key:
            continue
        if key in seen:
            raise ValueError(f"Duplicate category: {item}")
        seen.add(key)


def _write_categories(data: dict, *, backup: bool = True) -> None:
    # Atomic write with optional backup of the previous file.
    path = _categories_path()
    tmp = path.with_suffix('.json.tmp')

    if backup and path.exists():
        backup_name = f"{CATEGORIES_JSON_BACKUP_PREFIX}{_timestamp()}"
        backup_path = path.with_name(backup_name)
        try:
            shutil.copy2(str(path), str(backup_path))
        except Exception as e:
            log_error(f"category_state: backup copy failed: {e}")

    with tmp.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(str(tmp), str(path))


def seed_categories_if_missing() -> List[str]:
    # Seed from config only when file is missing.
    path = _categories_path()
    if path.exists():
        return load_categories()

    categories = _normalize_seed(list(PRODUCT_CATEGORIES or []))
    categories = _order_categories(categories)
    data = {'categories': categories}
    _write_categories(data, backup=False)
    return categories


def load_categories() -> List[str]:
    # Load categories or recover from missing/corrupt file.
    path = _categories_path()
    if not path.exists():
        return seed_categories_if_missing()

    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        ok, msg = _validate_categories_data(data)
        if not ok:
            _archive_corrupt(path)
            return seed_categories_if_missing()
        categories = [str(x) for x in data.get('categories') or []]
        ordered = _order_categories(_normalize_seed(categories))
        if ordered != categories:
            try:
                save_categories(ordered)
            except Exception:
                log_error("category_state: reorder save failed; using unsorted categories")
                return categories
        return ordered
    except Exception:
        _archive_corrupt(path)
        return seed_categories_if_missing()


def save_categories(categories: List[str]) -> None:
    # Persist normalized categories list to JSON.
    clean = _normalize_seed(categories)
    _enforce_unique(clean)
    clean = _order_categories(clean)
    data = {'categories': clean}
    _write_categories(data, backup=True)


def list_categories() -> List[str]:
    # Public list helper for UI population.
    return load_categories()


def add_category(name: str) -> None:
    # Add a single category after validation.
    category = Category.from_raw(name)
    ok, err = category.validate()
    if not ok:
        raise ValueError(err)
    if category.is_protected():
        raise ValueError("Protected category cannot be added")

    categories = load_categories()
    categories.append(category.normalized())
    save_categories(categories)


def update_category(old_name: str, new_name: str) -> None:
    # Rename a category by key match (case-insensitive).
    old = Category.from_raw(old_name)
    if old.is_protected():
        raise ValueError("Protected category cannot be renamed")

    new = Category.from_raw(new_name)
    ok, err = new.validate()
    if not ok:
        raise ValueError(err)
    if new.is_protected():
        raise ValueError("Protected category cannot be used")

    categories = load_categories()
    old_key = old.key()
    # Locate the existing entry for `old_name`.
    replaced_idx = None
    for idx, item in enumerate(categories):
        if _normalize_key(item) == old_key:
            replaced_idx = idx
            break
    if replaced_idx is None:
        raise ValueError("Category not found")

    new_key = new.key()
    # If `new_name` already exists elsewhere in the list, remove the old
    # entry instead of creating a duplicate. This keeps JSON unique while
    # DB replacements (performed elsewhere) can still map old->new.
    exists_elsewhere = any(
        _normalize_key(c) == new_key and i != replaced_idx
        for i, c in enumerate(categories)
    )
    if exists_elsewhere:
        # Remove the old entry
        del categories[replaced_idx]
    else:
        # Safe to replace in-place
        categories[replaced_idx] = new.normalized()

    save_categories(categories)


def delete_category(name: str) -> None:
    # Remove a category by key match (case-insensitive).
    target = Category.from_raw(name)
    if target.is_protected():
        raise ValueError("Protected category cannot be deleted")

    categories = load_categories()
    target_key = target.key()
    filtered = [c for c in categories if _normalize_key(c) != target_key]
    if len(filtered) == len(categories):
        raise ValueError("Category not found")

    save_categories(filtered)


def is_protected_category(name: str) -> bool:
    # Protected names cannot be renamed or deleted.
    return str(name or '').strip() in set(PROTECTED_CATEGORIES or [])
