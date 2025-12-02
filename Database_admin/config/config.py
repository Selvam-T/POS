"""
Admin configuration for Database_admin utilities (outside app project).

Assumed layout:
  POS/Database_admin/    <- this file lives here
  POS/db/Anumani.db      <- database lives here

Env overrides (optional):
  ADMIN_DB_PATH       Absolute path to Anumani.db (overrides derived path)
  ADMIN_DB_FILENAME   Defaults to 'Anumani.db'
  ADMIN_EXPORT_DIR    Absolute path for CSV exports (defaults to <this>/data)
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # .../POS/Database_admin
POS_DIR = os.path.dirname(BASE_DIR)                    # .../POS

DB_FILENAME = os.getenv('ADMIN_DB_FILENAME', 'Anumani.db')
DB_PATH = os.getenv('ADMIN_DB_PATH', os.path.join(POS_DIR, 'db', DB_FILENAME))

# Exports land under Database_admin/data by default
EXPORT_DIR = os.getenv('ADMIN_EXPORT_DIR', os.path.join(BASE_DIR, 'data'))

# Ensure export folder exists
os.makedirs(EXPORT_DIR, exist_ok=True)

