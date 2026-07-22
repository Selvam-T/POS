import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PyQt5.QtWidgets import QApplication, QLineEdit, QTableWidget, QWidget

from modules.devices.barcode_manager import BarcodeManager
from modules.devices.barcode_routing_logger import log_barcode_routing


_APP = None


def ensure_app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication([])
    return _APP


def _manager_with_parent():
    ensure_app()
    parent = QWidget()
    parent.receipt_context = {
        'source': 'ACTIVE_SALE',
        'active_receipt_id': None,
        'status': 'NONE',
    }
    parent._sales_table_ready = True
    parent.sales_table = QTableWidget()
    parent.statusbar = None
    parent._require_sales_table_ready = lambda: True
    with patch('modules.devices.barcode_manager.BarcodeScanner.start'):
        manager = BarcodeManager(parent)
    return manager, parent


def test_barcode_routing_log_is_timestamped_json(tmp_path):
    path = tmp_path / 'logs' / 'barcode_routing.log'

    log_barcode_routing(
        outcome='ignored',
        reason='protected-manual-field',
        barcode='12345',
        log_path=path,
        current_focus_widget='qtyInput',
    )

    record = json.loads(path.read_text(encoding='utf-8'))
    assert record['timestamp']
    assert record['outcome'] == 'ignored'
    assert record['reason'] == 'protected-manual-field'
    assert record['barcode'] == '12345'
    assert record['current_focus_widget'] == 'qtyInput'


def test_protected_field_scan_records_ignore_reason():
    app = ensure_app()
    manager, parent = _manager_with_parent()
    qty = QLineEdit(parent)
    qty.setObjectName('qtyInput')
    qty.show()
    qty.setFocus()
    app.processEvents()
    manager._scanStartWidget = qty
    manager._scanStartObjName = 'qtyInput'

    with patch('modules.devices.barcode_manager.log_barcode_routing') as log:
        manager.on_barcode_scanned('12345')

    assert log.call_count == 1
    kwargs = log.call_args.kwargs
    assert kwargs['outcome'] == 'ignored'
    assert kwargs['reason'] == 'protected-manual-field'
    assert kwargs['scan_start_widget'] == 'qtyInput'
    assert kwargs['receipt_source'] == 'ACTIVE_SALE'
    parent.close()


def test_successful_scan_returns_focus_to_sales_table():
    manager, parent = _manager_with_parent()
    table = Mock()
    parent.sales_table = table
    manager._scanStartWidget = None
    manager._scanStartObjName = ''

    with (
        patch('modules.table_ui.table_operations.get_product_info', return_value=(True, 'Item', 1.0, 'Each')),
        patch('modules.table_ui.handle_barcode_scanned', return_value='added'),
        patch('modules.devices.barcode_manager.log_barcode_routing') as log,
    ):
        manager.on_barcode_scanned('12345')

    table.setFocus.assert_called_once()
    log.assert_not_called()
    parent.close()
