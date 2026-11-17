"""Test summary report XLSX export changes."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from modules.menu import report_exports


class TestSummaryReportExport(unittest.TestCase):
    """Test summary report XLSX export with unit type splitting."""

    def test_summary_workbook_data_split_structure(self):
        """Verify _summary_workbook_data returns split unit type data."""
        report = {
            'header': {
                'period_from': '2026-04-01',
                'period_to': '2026-04-30',
                'generated_at': '2026-04-30 10:00:00',
                'generated_by': 'cashier_1',
            },
            'sales_summary': {
                'paid_receipt_count': 100,
                'gross_sales': 5000,
                'less_refund_outflow': 200,
                'less_vendor_outflow': 300,
                'net_after_outflows': 4500,
            },
            'sales_by_hour': [],
            'peak_hour': {},
            'top_products_by_qty_hour': [
                {
                    'hour_slot': '10:00 - 11:00',
                    'products': [
                        {'product_name': 'Banana', 'qty_sold': 10, 'unit': 'ea', 'line_sales': 30},
                        {'product_name': 'Apple', 'qty_sold': 5, 'unit': 'kg', 'line_sales': 50},
                    ],
                },
            ],
            'top_products_by_sales_hour': [],
            'top_products_by_qty_day': [],
            'top_products_by_sales_day': [],
            'excluded': {},
        }
        
        # Import the function
        from modules.menu.report_exports import _summary_workbook_data
        
        data = _summary_workbook_data(report)
        
        # Verify new split data keys exist
        self.assertIn('sales_hour_pieces', data, "Should have sales_hour_pieces key")
        self.assertIn('sales_hour_weight', data, "Should have sales_hour_weight key")
        self.assertIn('qty_hour_pieces', data, "Should have qty_hour_pieces key")
        self.assertIn('qty_hour_weight', data, "Should have qty_hour_weight key")
        self.assertIn('sales_day_pieces', data, "Should have sales_day_pieces key")
        self.assertIn('sales_day_weight', data, "Should have sales_day_weight key")
        self.assertIn('qty_day_pieces', data, "Should have qty_day_pieces key")
        self.assertIn('qty_day_weight', data, "Should have qty_day_weight key")
        
        # Verify old unsplit keys are gone
        self.assertNotIn('qty_by_hour_rows', data, "Old qty_by_hour_rows should not exist")
        self.assertNotIn('sales_by_hour_top_rows', data, "Old sales_by_hour_top_rows should not exist")

    def test_summary_workbook_data_hourly_split(self):
        """Verify hourly data is correctly split by unit type."""
        report = {
            'header': {
                'period_from': '2026-04-01',
                'period_to': '2026-04-30',
                'generated_at': '2026-04-30 10:00:00',
                'generated_by': 'cashier_1',
            },
            'sales_summary': {
                'paid_receipt_count': 100,
                'gross_sales': 5000,
                'less_refund_outflow': 200,
                'less_vendor_outflow': 300,
                'net_after_outflows': 4500,
            },
            'sales_by_hour': [],
            'peak_hour': {},
            'top_products_by_qty_hour': [
                {
                    'hour_slot': '10:00 - 11:00',
                    'products': [
                        {'product_name': 'Banana', 'qty_sold': 10, 'unit': 'ea', 'line_sales': 30},
                        {'product_name': 'Mango', 'qty_sold': 8, 'unit': 'ea', 'line_sales': 25},
                        {'product_name': 'Apple', 'qty_sold': 5, 'unit': 'kg', 'line_sales': 50},
                        {'product_name': 'Orange', 'qty_sold': 3, 'unit': 'kg', 'line_sales': 40},
                    ],
                },
            ],
            'top_products_by_sales_hour': [],
            'top_products_by_qty_day': [],
            'top_products_by_sales_day': [],
            'excluded': {},
        }
        
        from modules.menu.report_exports import _summary_workbook_data
        
        data = _summary_workbook_data(report)
        
        # Verify pieces data
        qty_hour_pieces = data['qty_hour_pieces']
        self.assertGreater(len(qty_hour_pieces), 0, "Should have pieces data")
        
        # Verify all pieces data has 'ea' unit and correct hour slot
        for row in qty_hour_pieces:
            hour_slot = row[0]
            self.assertEqual(hour_slot, '10:00 - 11:00', "Hour slot should match")
            # row[4] is the unit column
            self.assertEqual(row[4], 'ea', f"Unit should be 'ea', got {row[4]}")
        
        # Verify weight data
        qty_hour_weight = data['qty_hour_weight']
        self.assertGreater(len(qty_hour_weight), 0, "Should have weight data")
        
        # Verify all weight data has 'kg' unit
        for row in qty_hour_weight:
            # row[4] is the unit column
            self.assertIn(row[4], ['kg', 'g'], f"Unit should be 'kg' or 'g', got {row[4]}")


if __name__ == '__main__':
    unittest.main()
