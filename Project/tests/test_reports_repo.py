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
        cur.execute(
            "INSERT INTO receipts(receipt_id, receipt_no, status, grand_total, created_at, paid_at, customer_name, note) "
            "VALUES (1, '20260206-0001', 'PAID', 50.00, '2026-06-02T10:00:00', '2026-06-02T10:05:00', '', '')"
        )
        cur.execute(
            "INSERT INTO receipts(receipt_id, receipt_no, status, grand_total, created_at, paid_at, customer_name, note) "
            "VALUES (2, '20260206-0002', 'UNPAID', 20.00, '2026-06-02T11:00:00', NULL, 'John', 'Pending')"
        )
        cur.execute(
            "INSERT INTO receipt_items(receipt_id, product_name, category, quantity, unit, unit_price, line_total) "
            "VALUES (1, 'Milk 2L', 'Dairy', 2, 'Each', 6.5, 13.0)"
        )
        cur.execute(
            "INSERT INTO receipt_items(receipt_id, product_name, category, quantity, unit, unit_price, line_total) "
            "VALUES (1, 'Bread', 'Bakery', 1, 'Each', 5.0, 5.0)"
        )
        cur.execute(
            "INSERT INTO receipt_payments(receipt_id, payment_type, amount, tendered) VALUES (1, 'CASH', 18.0, 20.0)"
        )
        cur.execute(
            "INSERT INTO cash_outflows(outflows_type, amount, created_at, cashier_id, note) "
            "VALUES ('REFUND_OUT', 3.0, '2026-06-02T12:00:00', 1, 'Refund test')"
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
            self.assertEqual(rpt['sales_summary']['paid_receipt_count'], 1)
            self.assertEqual(rpt['sales_summary']['gross_sales'], 50.0)
            self.assertEqual(rpt['sales_summary']['less_refund_outflow'], 3.0)
            self.assertEqual(rpt['sales_summary']['net_after_outflows'], 47.0)

            self.assertEqual(len(rpt['payment_breakdown']), 1)
            self.assertEqual(rpt['payment_breakdown'][0]['method'], 'CASH')
            self.assertEqual(rpt['payment_breakdown'][0]['amount'], 18.0)

            self.assertEqual(len(rpt['categories']), 2)
            self.assertEqual(rpt['top_products'][0]['product_name'], 'Milk 2L')

            self.assertEqual(rpt['excluded']['unpaid_receipts_count'], 1)
            self.assertEqual(rpt['excluded']['unpaid_receipts_total'], 20.0)
        finally:
            conn.close()


if __name__ == '__main__':
    unittest.main()
