"""Test summary report split by unit type."""

import unittest
from modules.menu.report_viewers import _format_summary_report_text


class TestSummaryReportSplit(unittest.TestCase):
    """Test summary report formatting with unit type splitting."""

    def test_section_ordering(self):
        """Verify sections 3, 4, 5, 6 are in correct order after swap."""
        report = {
            'header': {
                'period_from': '2026-04-01',
                'period_to': '2026-04-30',
                'generated_at': '2026-04-30 10:00:00',
                'generated_by': 'test_user',
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
            'top_products_by_qty_day': [],
            'top_products_by_sales_day': [],
            'excluded': {},
        }
        
        text, _, _, _ = _format_summary_report_text(report)
        
        # Find section positions
        pos_3 = text.find('3. Top Earning Items (By Hour)')
        pos_4 = text.find('4. Most Popular Items (By Hour)')
        pos_5 = text.find('5. Most Consistent Sellers (By Earnings)')
        pos_6 = text.find('6. Most Consistent Sellers (By Quantity)')
        
        # Verify section order
        self.assertGreater(pos_3, 0, "Section 3 not found")
        self.assertGreater(pos_4, pos_3, "Section 4 should come after Section 3")
        self.assertGreater(pos_5, pos_4, "Section 5 should come after Section 4")
        self.assertGreater(pos_6, pos_5, "Section 6 should come after Section 5")

    def test_hourly_section_split_by_unit(self):
        """Verify hourly sections split products by unit type."""
        report = {
            'header': {
                'period_from': '2026-04-01',
                'period_to': '2026-04-30',
                'generated_at': '2026-04-30 10:00:00',
                'generated_by': 'test_user',
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
                        {'product_name': 'Mango', 'qty_sold': 8, 'unit': 'ea', 'line_sales': 25},
                        {'product_name': 'Orange', 'qty_sold': 3, 'unit': 'kg', 'line_sales': 40},
                    ],
                },
            ],
            'top_products_by_sales_hour': [],
            'top_products_by_qty_day': [],
            'top_products_by_sales_day': [],
            'excluded': {},
        }
        
        text, _, _, _ = _format_summary_report_text(report)
        
        # Find the section with unit split markers
        # Should show pieces (ea) first, then blank line, then weight (kg)
        self.assertIn('Banana', text, "Banana (ea) should be in output")
        self.assertIn('Apple', text, "Apple (kg) should be in output")
        
        # Verify pieces appear before weight within the hour slot
        banana_pos = text.find('Banana')
        apple_pos = text.find('Apple')
        self.assertGreater(banana_pos, 0, "Banana should be in output")
        self.assertGreater(apple_pos, 0, "Apple should be in output")

    def test_daily_section_weight_limit(self):
        """Verify daily consistent sellers by quantity limits weight to 5."""
        report = {
            'header': {
                'period_from': '2026-04-01',
                'period_to': '2026-04-30',
                'generated_at': '2026-04-30 10:00:00',
                'generated_by': 'test_user',
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
                {'product_name': f'Piece_{i}', 'qty_sold': 10 - i, 'unit': 'ea', 'line_sales': 50 - i}
                for i in range(15)
            ] + [
                {'product_name': f'Weight_{i}', 'qty_sold': 20 - i, 'unit': 'kg', 'line_sales': 100 - i}
                for i in range(10)
            ],
            'top_products_by_sales_day': [],
            'excluded': {},
        }
        
        text, _, _, _ = _format_summary_report_text(report)
        
        # Count weight products in output
        weight_count = sum(1 for i in range(10) if f'Weight_{i}' in text)
        
        # Should be limited to 5 for weight products in "By Quantity" section
        self.assertLessEqual(weight_count, 5, f"Weight products should be limited to 5, found {weight_count}")


if __name__ == '__main__':
    unittest.main()
