from pathlib import Path


def test_sales_table_has_visible_focus_border():
    qss = Path('assets/qss/sales.qss').read_text(encoding='utf-8')

    assert 'QTableWidget#salesTable:focus' in qss
    assert 'border: 4px solid #f59e0b;' in qss
