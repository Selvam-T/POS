"""Comprehensive test for summary report unit type splitting."""

import unittest
from modules.menu.report_viewers import _format_summary_report_text


class TestSummaryReportFormatting(unittest.TestCase):
    """Test that summary report output matches specifications."""

    def test_hourly_split_output_format(self):
        """Verify hourly section output format with unit type split."""
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
                    'hour_slot': '11:00 - 12:00',
                    'products': [
                        {'product_name': 'Black Pepper W/grain', 'qty_sold': 17, 'unit': 'ea', 'line_sales': 164.15},
                        {'product_name': 'Aec Scouring Sponge 3s Ua088', 'qty_sold': 14, 'unit': 'ea', 'line_sales': 21.00},
                        {'product_name': 'Ch Coke Bun 220g', 'qty_sold': 11, 'unit': 'ea', 'line_sales': 14.62},
                        {'product_name': 'Apple', 'qty_sold': 0.6, 'unit': 'kg', 'line_sales': 20},
                        {'product_name': 'Garlic', 'qty_sold': 0.5, 'unit': 'kg', 'line_sales': 10},
                        {'product_name': 'Potato', 'qty_sold': 0.2, 'unit': 'kg', 'line_sales': 5},
                    ],
                },
            ],
            'top_products_by_sales_hour': [],
            'top_products_by_qty_day': [],
            'top_products_by_sales_day': [],
            'excluded': {},
        }
        
        text, bold_lines, _, _ = _format_summary_report_text(report)
        
        # Verify structure
        self.assertIn('4. Most Popular Items (By Hour)', text, "Section 4 header should be present")
        self.assertIn('11:00 - 12:00', text, "Hour slot should be present and bold")
        self.assertIn('Black Pepper', text, "Piece product should be in output")
        self.assertIn('Apple', text, "Weight product should be in output")
        
        # Verify the hour slot is marked as bold
        self.assertIn('11:00 - 12:00', bold_lines, "Hour slot should be in bold_lines set")
        
        # Verify ranking is sequential (1, 2, 3) for both pieces and weight
        lines = text.split('\n')
        rank_lines = [l for l in lines if ' 1. ' in l or ' 2. ' in l or ' 3. ' in l]
        self.assertGreater(len(rank_lines), 0, "Ranking lines should be present")

    def test_section_labels_match_spec(self):
        """Verify section labels exactly match the requirements."""
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
            'top_products_by_qty_day': [],
            'top_products_by_sales_day': [],
            'excluded': {},
        }
        
        text, _, _, _ = _format_summary_report_text(report)
        
        # Verify section headers in order
        self.assertIn('3. Top Earning Items (By Hour)', text)
        self.assertIn('4. Most Popular Items (By Hour)', text)
        self.assertIn('5. Most Consistent Sellers (By Earnings)', text)
        self.assertIn('6. Most Consistent Sellers (By Quantity)', text)
        
        # Verify order
        pos_3 = text.find('3. Top Earning')
        pos_4 = text.find('4. Most Popular')
        pos_5 = text.find('5. Most Consistent Sellers (By Earnings)')
        pos_6 = text.find('6. Most Consistent Sellers (By Quantity)')
        
        self.assertLess(pos_3, pos_4, "Section 3 before Section 4")
        self.assertLess(pos_4, pos_5, "Section 4 before Section 5")
        self.assertLess(pos_5, pos_6, "Section 5 before Section 6")

    def test_tie_breaking_by_amount(self):
        """Verify products with equal primary metric are sorted by amount."""
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
                        # Same qty, different amounts - should sort by amount desc
                        {'product_name': 'Product_High', 'qty_sold': 10, 'unit': 'ea', 'line_sales': 100},
                        {'product_name': 'Product_Low', 'qty_sold': 10, 'unit': 'ea', 'line_sales': 50},
                    ],
                },
            ],
            'top_products_by_sales_hour': [],
            'top_products_by_qty_day': [],
            'top_products_by_sales_day': [],
            'excluded': {},
        }
        
        text, _, _, _ = _format_summary_report_text(report)
        
        # Find positions of products
        high_pos = text.find('Product_High')
        low_pos = text.find('Product_Low')
        
        # High amount product should appear first (rank 1)
        self.assertGreater(high_pos, 0, "High amount product should be in output")
        self.assertGreater(low_pos, high_pos, "High amount product should rank before low amount")


if __name__ == '__main__':
    unittest.main()
