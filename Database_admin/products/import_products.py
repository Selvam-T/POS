"""Import products from data/products.csv using the staged legacy migration flow."""

from __future__ import annotations

import sys
from pathlib import Path

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from migration.migrate_legacy_products import migrate_legacy_products
from migration.stage_legacy_products import stage_legacy_products
from migration.validate_legacy_products import validate_legacy_products


def import_products() -> int:
    staged = stage_legacy_products()
    cleaned, _ = validate_legacy_products(staged)
    return migrate_legacy_products(cleaned)


if __name__ == "__main__":
    import_products()
