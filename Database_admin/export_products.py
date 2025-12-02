"""
Export Product_list to CSV for re-import (Database_admin version).

Default output: <Database_admin>/data/product_import_11_7.csv
- Normalizes name and product_code to CamelCase by default for cleaner re-import
- Use --raw to export values as-is

Usage (from POS/Database_admin):
  python export_products.py [--out data\\product_import_11_7.csv] [--db ..\\db\\Anumani.db] [--raw]
"""
import csv
import os
import sys
import argparse
import sqlite3

# Prefer local admin config next to this script
try:
    # If this template is copied into POS/Database_admin, config.py will be alongside.
    from config import DB_PATH as CONFIG_DB_PATH, EXPORT_DIR
except Exception:
    # If run from template location inside the app repo, resolve admin config relatively
    TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))
    ADMIN_ROOT = TEMPLATE_DIR  # this will be replaced when copied
    if ADMIN_ROOT not in sys.path:
        sys.path.insert(0, ADMIN_ROOT)
    try:
        from config import DB_PATH as CONFIG_DB_PATH, EXPORT_DIR  # type: ignore
    except Exception as e:
        CONFIG_DB_PATH = None
        EXPORT_DIR = os.path.join(TEMPLATE_DIR, 'data')


def to_camel_case(text: str) -> str:
    if text is None:
        return ''
    s = str(text).strip()
    if not s:
        return ''
    for sep in ['\t', '\n', '_', '-']:
        s = s.replace(sep, ' ')
    parts = [p for p in s.split(' ') if p]
    return ' '.join(w[:1].upper() + w[1:].lower() if w else '' for w in parts)


def export_products(db_path: str, out_path: str, raw: bool) -> int:
    if not db_path or not os.path.exists(db_path):
        print(f"[ERROR] Database not found: {db_path}")
        return 2
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT product_code, name, category, supplier, selling_price, cost_price, unit, last_updated
        FROM Product_list
        ORDER BY name COLLATE NOCASE
        """
    )
    rows = cur.fetchall()
    conn.close()

    headers = [
        'product_code', 'name', 'category', 'supplier',
        'selling_price', 'cost_price', 'unit', 'last_updated'
    ]

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(headers)
        for r in rows:
            code, name, cat, sup, sp, cp, unit, lu = r
            if not raw:
                code = to_camel_case(code)
                name = to_camel_case(name)
                cat = to_camel_case(cat) if cat is not None else None
                sup = to_camel_case(sup) if sup is not None else None
            w.writerow([
                '' if code is None else code,
                '' if name is None else name,
                '' if cat is None else cat,
                '' if sup is None else sup,
                0.0 if sp is None else float(sp),
                '' if cp is None else cp,
                '' if unit is None else unit,
                '' if lu is None else lu,
            ])

    print(f"[OK] Exported {len(rows)} rows to {out_path}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--out', help='Output CSV path; default to <Database_admin>/data/product_import_11_7.csv')
    p.add_argument('--db', help='Path to Anumani.db; defaults to ADMIN DB_PATH from Database_admin/config.py')
    p.add_argument('--raw', action='store_true', help='Export values without CamelCase normalization')
    args = p.parse_args(argv)

    db_path = args.db or CONFIG_DB_PATH
    out_path = args.out or os.path.join(EXPORT_DIR, 'product_import_11_7.csv')
    return export_products(db_path, out_path, args.raw)


if __name__ == '__main__':
    sys.exit(main())
