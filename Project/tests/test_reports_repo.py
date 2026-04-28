import sqlite3
import sys
import unittest

sys.path.insert(0, r'c:\\Users\\SELVAM\\OneDrive\\Desktop\\POS\\Project')

from modules.db_operation import reports_repo


class ReportsRepoTest(unittest.TestCase):
    def _build_conn(self):
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY,
                username TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE Product_list (
                product_code TEXT PRIMARY KEY,
                name TEXT,
                category TEXT,
                supplier TEXT,
                selling_price REAL,
                cost_price REAL,
                unit TEXT,
                last_updated TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE receipts (
                receipt_id INTEGER PRIMARY KEY,
                receipt_no TEXT,
                status TEXT,
                grand_total REAL,
                created_at TEXT,
                paid_at TEXT,
                customer_name TEXT,
                note TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE receipt_items (
                item_id INTEGER PRIMARY KEY,
                receipt_id INTEGER,
                product_code TEXT,
                product_name TEXT,
                category TEXT,
                quantity REAL,
                unit TEXT,
                unit_price REAL,
                line_total REAL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE receipt_payments (
                payment_id INTEGER PRIMARY KEY,
                receipt_id INTEGER,
                payment_type TEXT,
                amount REAL,
                tendered REAL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE cash_outflows (
                outflows_id INTEGER PRIMARY KEY,
                outflows_type TEXT,
                amount REAL,
                created_at TEXT,
                cashier_id INTEGER,
                note TEXT
            )
            """
        )

        cur.execute("INSERT INTO users(user_id, username) VALUES (1, 'admin')")
        cur.executemany(
            "INSERT INTO Product_list(product_code, name, category, supplier, selling_price, cost_price, unit, last_updated) "
            "VALUES (?, ?, ?, '', 0, 0, 'Each', '2026-04-20T00:00:00')",
            [
                ('P014', 'Green Tea 500ml', 'Drinks'),
                ('P022', 'Butter Cookies', 'Snacks'),
                ('P031', 'Dish Sponge Pack', 'Household'),
                ('P045', 'Herbal Shampoo', 'Toiletries'),
                ('P052', 'Mango Pickle', 'Pantry'),
                ('P067', 'Canned Sardine XL', 'Canned Food'),
                ('P081', 'Premium Tea Powder', 'Pantry'),
                ('P094', 'Imported Crackers', 'Snacks'),
                ('P108', 'Glass Cleaner Refill', 'Household'),
                ('P120', 'Special Oil Bottle', 'Pantry'),
                ('P133', 'Organic Jam', 'Groceries'),
                ('P149', 'Mini Wafer Roll', 'Snacks'),
                ('P200', 'Fresh Milk', 'Dairy'),
            ],
        )
        cur.execute(
            "INSERT INTO receipts(receipt_id, receipt_no, status, grand_total, created_at, paid_at, customer_name, note) "
            "VALUES (1, '20260206-0001', 'PAID', 50.00, '2026-06-02T10:00:00', '2026-06-02T10:05:00', '', '')"
        )
        cur.execute(
            "INSERT INTO receipts(receipt_id, receipt_no, status, grand_total, created_at, paid_at, customer_name, note) "
            "VALUES (3, '20260206-0003', 'PAID', 39.50, '2026-06-02T09:00:00', '2026-06-02T09:20:00', '', '')"
        )
        cur.execute(
            "INSERT INTO receipts(receipt_id, receipt_no, status, grand_total, created_at, paid_at, customer_name, note) "
            "VALUES (2, '20260206-0002', 'UNPAID', 20.00, '2026-06-02T11:00:00', NULL, 'John', 'Pending')"
        )
        cur.execute(
            "INSERT INTO receipt_items(receipt_id, product_code, product_name, category, quantity, unit, unit_price, line_total) "
            "VALUES (1, '', 'Milk 2L', 'Dairy', 2, 'Each', 6.5, 13.0)"
        )
        cur.execute(
            "INSERT INTO receipt_items(receipt_id, product_code, product_name, category, quantity, unit, unit_price, line_total) "
            "VALUES (1, '', 'Bread', 'Bakery', 1, 'Each', 5.0, 5.0)"
        )
        cur.execute(
            "INSERT INTO receipt_items(receipt_id, product_code, product_name, category, quantity, unit, unit_price, line_total) "
            "VALUES (3, '', 'Red Apple', 'Fruits', 2.5, 'Kg', 3.0, 7.5)"
        )
        cur.execute(
            "INSERT INTO receipt_items(receipt_id, product_code, product_name, category, quantity, unit, unit_price, line_total) "
            "VALUES (3, '', 'Detergent', 'Household', 1, 'Each', 32.0, 32.0)"
        )
        cur.execute(
            "INSERT INTO receipt_payments(receipt_id, payment_type, amount, tendered) VALUES (1, 'CASH', 18.0, 20.0)"
        )
        cur.execute(
            "INSERT INTO receipt_payments(receipt_id, payment_type, amount, tendered) VALUES (3, 'CASH', 39.5, 40.0)"
        )
        cur.execute(
            "INSERT INTO cash_outflows(outflows_type, amount, created_at, cashier_id, note) "
            "VALUES ('REFUND_OUT', 3.0, '2026-06-02T12:00:00', 1, 'Refund test')"
        )
        conn.commit()
        return conn

    def _build_inactivity_conn(self):
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY,
                username TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE Product_list (
                product_code TEXT PRIMARY KEY,
                name TEXT,
                category TEXT,
                supplier TEXT,
                selling_price REAL,
                cost_price REAL,
                unit TEXT,
                last_updated TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE receipts (
                receipt_id INTEGER PRIMARY KEY,
                receipt_no TEXT,
                status TEXT,
                grand_total REAL,
                created_at TEXT,
                paid_at TEXT,
                customer_name TEXT,
                note TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE receipt_items (
                item_id INTEGER PRIMARY KEY,
                receipt_id INTEGER,
                product_code TEXT,
                product_name TEXT,
                category TEXT,
                quantity REAL,
                unit TEXT,
                unit_price REAL,
                line_total REAL
            )
            """
        )

        cur.execute("INSERT INTO users(user_id, username) VALUES (1, 'admin')")
        cur.executemany(
            "INSERT INTO Product_list(product_code, name, category, supplier, selling_price, cost_price, unit, last_updated) "
            "VALUES (?, ?, ?, '', 0, 0, 'Each', '2026-04-20T00:00:00')",
            [
                ('P014', 'Green Tea 500ml', 'Drinks'),
                ('P022', 'Butter Cookies', 'Snacks'),
                ('P031', 'Dish Sponge Pack', 'Household'),
                ('P045', 'Herbal Shampoo', 'Toiletries'),
                ('P052', 'Mango Pickle', 'Pantry'),
                ('P067', 'Canned Sardine XL', 'Canned Food'),
                ('P081', 'Premium Tea Powder', 'Pantry'),
                ('P094', 'Imported Crackers', 'Snacks'),
                ('P108', 'Glass Cleaner Refill', 'Household'),
                ('P120', 'Special Oil Bottle', 'Pantry'),
                ('P133', 'Organic Jam', 'Groceries'),
                ('P149', 'Mini Wafer Roll', 'Snacks'),
                ('P200', 'Fresh Milk', 'Dairy'),
            ],
        )

        cur.execute(
            "INSERT INTO receipts(receipt_id, receipt_no, status, grand_total, created_at, paid_at, customer_name, note) "
            "VALUES (10, '20260420-0001', 'PAID', 75.00, '2026-01-10T09:00:00', '2026-01-10T09:05:00', '', '')"
        )
        cur.execute(
            "INSERT INTO receipts(receipt_id, receipt_no, status, grand_total, created_at, paid_at, customer_name, note) "
            "VALUES (11, '20260420-0002', 'PAID', 90.00, '2025-10-15T11:00:00', '2025-10-15T11:05:00', '', '')"
        )
        cur.execute(
            "INSERT INTO receipts(receipt_id, receipt_no, status, grand_total, created_at, paid_at, customer_name, note) "
            "VALUES (12, '20260420-0003', 'PAID', 55.00, '2025-03-12T14:00:00', '2025-03-12T14:05:00', '', '')"
        )
        cur.execute(
            "INSERT INTO receipts(receipt_id, receipt_no, status, grand_total, created_at, paid_at, customer_name, note) "
            "VALUES (13, '20260420-0004', 'PAID', 15.00, '2026-04-15T15:00:00', '2026-04-15T15:05:00', '', '')"
        )

        for receipt_id, code, name, category, sold_at in [
            (10, 'P014', 'Green Tea 500ml', 'Drinks', 12.0),
            (10, 'P022', 'Butter Cookies', 'Snacks', 8.0),
            (10, 'P031', 'Dish Sponge Pack', 'Household', 7.0),
            (11, 'P045', 'Herbal Shampoo', 'Toiletries', 20.0),
            (11, 'P052', 'Mango Pickle', 'Pantry', 18.0),
            (11, 'P067', 'Canned Sardine XL', 'Canned Food', 22.0),
            (12, 'P081', 'Premium Tea Powder', 'Pantry', 15.0),
            (12, 'P094', 'Imported Crackers', 'Snacks', 20.0),
            (12, 'P108', 'Glass Cleaner Refill', 'Household', 20.0),
            (13, 'P200', 'Fresh Milk', 'Dairy', 15.0),
        ]:
            cur.execute(
                "INSERT INTO receipt_items(receipt_id, product_code, product_name, category, quantity, unit, unit_price, line_total) "
                "VALUES (?, ?, ?, ?, 1, 'Each', ?, ?)",
                (receipt_id, code, name, category, sold_at, sold_at),
            )

        conn.commit()
        return conn

    def test_detailed_report_aggregates(self):
        conn = self._build_conn()
        try:
            params = {'from': '2026-06-02T00:00:00', 'to': '2026-06-02T23:59:59', 'user_id': 1}
            rpt = reports_repo.detailed_report(params, conn=conn)

            self.assertIsInstance(rpt, dict)
            self.assertEqual(rpt['header']['generated_by'], 'admin')
            self.assertEqual(rpt['sales_summary']['paid_receipt_count'], 2)
            self.assertEqual(rpt['sales_summary']['gross_sales'], 89.5)
            self.assertEqual(rpt['sales_summary']['less_refund_outflow'], 3.0)
            self.assertEqual(rpt['sales_summary']['net_after_outflows'], 86.5)

            self.assertEqual(len(rpt['payment_breakdown']), 1)
            self.assertEqual(rpt['payment_breakdown'][0]['method'], 'CASH')
            self.assertEqual(rpt['payment_breakdown'][0]['amount'], 57.5)

            self.assertGreaterEqual(len(rpt['categories']), 4)
            self.assertEqual(rpt['top_products'][0]['product_name'], 'Detergent')

            self.assertEqual(rpt['excluded']['unpaid_receipts_count'], 1)
            self.assertEqual(rpt['excluded']['unpaid_receipts_total'], 20.0)
        finally:
            conn.close()

    def test_summary_report_aggregates(self):
        conn = self._build_conn()
        try:
            params = {'from': '2026-06-02T00:00:00', 'to': '2026-06-03T23:59:59', 'user_id': 1}
            rpt = reports_repo.summary_report(params, conn=conn)

            self.assertIsInstance(rpt, dict)
            self.assertAlmostEqual(rpt['sales_summary']['paid_receipt_count'], 1.0)
            self.assertAlmostEqual(rpt['sales_summary']['gross_sales'], 44.75)
            self.assertAlmostEqual(rpt['sales_summary']['less_refund_outflow'], 1.5)
            self.assertAlmostEqual(rpt['sales_summary']['net_after_outflows'], 43.25)
            self.assertEqual(len(rpt['sales_by_hour']), 2)
            self.assertEqual(rpt['peak_hour']['hour_slot'], '09:00 - 10:00')
            self.assertAlmostEqual(rpt['sales_by_hour'][0]['sales_amount'], 19.75)
            self.assertAlmostEqual(rpt['sales_by_hour'][1]['sales_amount'], 9.0)
            self.assertAlmostEqual(rpt['peak_hour']['sales_amount'], 19.75)
            self.assertEqual(len(rpt['top_products_by_qty_hour']), 2)
            self.assertEqual(len(rpt['top_products_by_sales_hour']), 2)
            self.assertGreaterEqual(len(rpt['top_products_by_qty_day']), 3)
            self.assertGreaterEqual(len(rpt['top_products_by_sales_day']), 3)
            self.assertEqual(rpt['top_products_by_qty_hour'][0]['products'][0]['product_name'], 'Red Apple')
            self.assertAlmostEqual(rpt['top_products_by_qty_hour'][0]['products'][0]['qty_sold'], 1.25)
            self.assertEqual(rpt['top_products_by_qty_day'][0]['product_name'], 'Red Apple')
            self.assertAlmostEqual(rpt['top_products_by_qty_day'][0]['qty_sold'], 1.25)
            self.assertEqual(rpt['top_products_by_sales_day'][0]['product_name'], 'Detergent')
            self.assertAlmostEqual(rpt['top_products_by_sales_day'][0]['line_sales'], 16.0)
        finally:
            conn.close()

    def test_inactivity_report_buckets(self):
        conn = self._build_inactivity_conn()
        try:
            params = {'to': '2026-04-20T23:59:59', 'user_id': 1}
            rpt = reports_repo.inactivity_report(params, conn=conn)

            self.assertIsInstance(rpt, dict)
            self.assertEqual(rpt['header']['generated_by'], 'admin')
            self.assertEqual(rpt['header']['period_checked'], '2026-04-20T23:59:59')

            sections = {section['bucket']: section for section in rpt['sections']}
            self.assertEqual(len(sections['3_6']['products']), 3)
            self.assertEqual(len(sections['6_12']['products']), 3)
            self.assertEqual(len(sections['1_plus']['products']), 3)
            self.assertEqual(len(sections['never']['products']), 3)
            self.assertEqual(rpt['summary']['total_inactive_products'], 12)
        finally:
            conn.close()


if __name__ == '__main__':
    unittest.main()
