from unittest.mock import Mock, patch

from PyQt5.QtWidgets import QApplication, QTableWidget, QWidget

from modules.devices.barcode_manager import BarcodeManager


_APP = None


def ensure_app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication([])
    return _APP


def test_successful_scan_returns_focus_to_sales_table():
    ensure_app()
    parent = QWidget()
    parent.receipt_context = {
        'source': 'ACTIVE_SALE',
        'active_receipt_id': None,
        'status': 'NONE',
    }
    parent._sales_table_ready = True
    parent.sales_table = Mock(spec=QTableWidget)
    parent.statusbar = None
    parent._require_sales_table_ready = lambda: True

    with patch('modules.devices.barcode_manager.BarcodeScanner.start'):
        manager = BarcodeManager(parent)

    with (
        patch('modules.table_ui.table_operations.get_product_info', return_value=(True, 'Item', 1.0, 'Each')),
        patch('modules.table_ui.handle_barcode_scanned', return_value='added'),
    ):
        manager.on_barcode_scanned('12345')

    parent.sales_table.setFocus.assert_called_once()
    parent.close()
