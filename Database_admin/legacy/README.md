# Legacy Scripts

These scripts were moved out of the fresh database setup path.

- `migrate_user_table.py` adds `users.must_change_password` to older databases.
- `migrate_schema.py` is an old schema-inspection template.
- `drop_receipt_tables.py` and `drop_cash_outflows_table.py` are destructive table-drop helpers kept only for reference.

Fresh databases should use the corrected create scripts and `setup_fresh_database.py` instead of these legacy migration scripts.
