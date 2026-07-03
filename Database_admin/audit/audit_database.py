"""Compatibility wrapper for database audit."""

from __future__ import annotations

import sys
from pathlib import Path

ADMIN_ROOT = Path(__file__).resolve().parents[1]
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from audit.verify_db_and_product_list import verify_database


if __name__ == "__main__":
    verify_database()
