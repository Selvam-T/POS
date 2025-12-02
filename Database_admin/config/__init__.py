"""
Admin config for Database_admin (outside app project).

Computes:
- DB_PATH: ..\\db\\Anumani.db (overridable via ADMIN_DB_PATH or ADMIN_DB_FILENAME)
- EXPORT_DIR: <Database_admin>\\data (overridable via ADMIN_EXPORT_DIR)
"""
import os

# .../POS/Database_admin/config/__init__.py
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ADMIN_ROOT = os.path.dirname(BASE_DIR)      # .../POS/Database_admin
POS_DIR = os.path.dirname(ADMIN_ROOT)       # .../POS

DB_FILENAME = os.getenv('ADMIN_DB_FILENAME', 'Anumani.db')
DB_PATH = os.getenv('ADMIN_DB_PATH', os.path.join(POS_DIR, 'db', DB_FILENAME))

EXPORT_DIR = os.getenv('ADMIN_EXPORT_DIR', os.path.join(ADMIN_ROOT, 'data'))
os.makedirs(EXPORT_DIR, exist_ok=True)

__all__ = ['DB_PATH', 'EXPORT_DIR']