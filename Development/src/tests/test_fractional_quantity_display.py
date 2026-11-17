"""Test for fractional quantity display (2-decimal formatting for small values)."""

import unittest
from modules.menu.report_viewers import _format_summary_report_text, _format_detailed_report_text


class TestFractionalQuantityDisplay(unittest.TestCase):
    """Test that quantities between 0 and 1 display with 2 decimals."""

    def test_summary_report_fractional_ea_display(self):
        """Verify summary report shows 2-decimal for fractional 'ea' quantities."""
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
            'top_products_by_qty_hour': [],
            'top_products_by_sales_hour': [],
            'top_products_by_qty_day': [
                {'product_name': 'Product_Fractional', 'qty_sold': 0.5, 'unit': 'ea', 'line_sales': 25},
            ],
            'top_products_by_sales_day': [],
            'excluded': {},
        }
        
        text, _, _, _ = _format_summary_report_text(report)
        
        # Verify '0.50 ea' (2-decimal) appears in output
        self.assertIn('0.50', text, "Fractional quantity should display with two decimals")
        self.assertIn('Product_Fractional', text, "Product should be in output")

    def test_summary_report_fractional_kg_display(self):
        """Verify summary report shows correct formatting for fractional 'kg' quantities."""
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
            'top_products_by_qty_hour': [],
            'top_products_by_sales_hour': [],
            'top_products_by_qty_day': [
                {'product_name': 'Garlic', 'qty_sold': 0.5, 'unit': 'kg', 'line_sales': 25},
            ],
            'top_products_by_sales_day': [],
            'excluded': {},
        }
        
        text, _, _, _ = _format_summary_report_text(report)
        
        # For 0.5kg, it should display as "500 g" (500 grams); very small grams show decimals
        self.assertIn('Garlic', text, "Product should be in output")

    def test_detail_report_fractional_display(self):
        """Verify detailed report shows 2-decimal for fractional quantities."""
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
            'payment_breakdown': [],
            'categories': [
                {
                    'category_name': 'Test Category',
                    'category_total': 100,
                    'products': [
                        {'product_name': 'Fractional Product', 'qty_sold': 0.5, 'unit': 'ea', 'line_sales': 50},
                    ],
                },
            ],
            'top_products': [],
            'cash_outflows': [],
            'excluded': {},
        }
        
        text, _, _, _ = _format_detailed_report_text(report)
        
        # Verify '0.50 ea' (2-decimal) appears in output
        self.assertIn('0.50', text, "Fractional quantity should display with two decimals")
        self.assertIn('Fractional Product', text, "Product should be in output")

    def test_zero_quantity_display(self):
        """Verify that qty 0 displays as '0', not a small decimal."""
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
            'payment_breakdown': [],
            'categories': [
                {
                    'category_name': 'Test Category',
                    'category_total': 100,
                    'products': [
                        {'product_name': 'Zero Product', 'qty_sold': 0, 'unit': 'ea', 'line_sales': 0},
                    ],
                },
            ],
            'top_products': [],
            'cash_outflows': [],
            'excluded': {},
        }
        
        text, _, _, _ = _format_detailed_report_text(report)
        
        # Should show '0', not '< 1'
        lines = text.split('\n')
        zero_line = [l for l in lines if 'Zero Product' in l]
        self.assertTrue(any('0 ea' in l or '0  ea' in l for l in zero_line), "Zero qty should display as '0 ea'")


if __name__ == '__main__':
    unittest.main()
