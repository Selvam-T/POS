from unittest.mock import Mock, patch

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QLineEdit, QTableWidget, QWidget

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

    with (
        patch('modules.devices.barcode_manager.BarcodeScanner.start'),
        patch('modules.devices.barcode_manager.trace_scanner_event'),
    ):
        manager = BarcodeManager(parent)

    with (
        patch('modules.table_ui.table_operations.get_product_info', return_value=(True, 'Item', 1.0, 'Each')),
        patch('modules.table_ui.handle_barcode_scanned', return_value='added'),
        patch('modules.devices.barcode_manager.trace_scanner_event'),
    ):
        manager.on_barcode_scanned('12345')

    parent.sales_table.setFocus.assert_called_once()
    parent.close()


def test_normal_scan_is_compacted_into_periodic_summary():
    ensure_app()
    parent = QWidget()
    parent.receipt_context = {'source': 'ACTIVE_SALE'}
    parent._sales_table_ready = True
    parent.sales_table = Mock(spec=QTableWidget)
    parent.sales_table.rowCount.side_effect = [0, 1]
    parent.statusbar = None
    parent._require_sales_table_ready = lambda: True

    with (
        patch('modules.devices.barcode_manager.BarcodeScanner.start'),
        patch('modules.devices.barcode_manager.trace_scanner_event'),
    ):
        manager = BarcodeManager(parent)

    manager.scanner._trace_emitted_candidates = 1
    with (
        patch('modules.table_ui.table_operations.get_product_info', return_value=(True, 'Item', 1.0, 'Each')),
        patch('modules.table_ui.handle_barcode_scanned', return_value='added'),
        patch('modules.devices.barcode_manager.trace_scanner_event') as trace,
    ):
        manager.on_barcode_scanned('12345')
        trace.assert_not_called()
        manager._trace_scanner_summary()

    trace.assert_called_once()
    assert trace.call_args.args == ('scanner_summary',)
    assert trace.call_args.kwargs['candidates_emitted'] == 1
    assert trace.call_args.kwargs['barcodes_received'] == 1
    assert trace.call_args.kwargs['sales_added'] == 1
    parent.close()


def test_scanner_like_printable_key_is_not_speculatively_swallowed():
    ensure_app()
    parent = QWidget()
    with (
        patch('modules.devices.barcode_manager.BarcodeScanner.start'),
        patch('modules.devices.barcode_manager.trace_scanner_event'),
    ):
        manager = BarcodeManager(parent)
    line_edit = QLineEdit(parent)
    manager._scannerBurstUntil = float('inf')
    event = QKeyEvent(QEvent.KeyPress, Qt.Key_A, Qt.NoModifier, 'a')

    assert manager.eventFilter(line_edit, event) is False
    parent.close()


def test_confirmed_scan_restores_non_product_field_after_classification():
    ensure_app()
    parent = QWidget()
    with (
        patch('modules.devices.barcode_manager.BarcodeScanner.start'),
        patch('modules.devices.barcode_manager.trace_scanner_event'),
    ):
        manager = BarcodeManager(parent)
    line_edit = QLineEdit(parent)
    line_edit.setObjectName('manualDescriptionLineEdit')
    line_edit.setText('original8887319900328')
    manager._scanStartWidget = line_edit
    manager._preScanText = 'original'

    manager._restore_confirmed_scan_text('8887319900328')
    QTest.qWait(100)

    assert line_edit.text() == 'original'
    parent.close()


def test_handled_product_code_keeps_matching_final_digit():
    ensure_app()
    parent = QWidget()
    with (
        patch('modules.devices.barcode_manager.BarcodeScanner.start'),
        patch('modules.devices.barcode_manager.trace_scanner_event'),
    ):
        manager = BarcodeManager(parent)
    line_edit = QLineEdit(parent)
    line_edit.setObjectName('addProductCodeLineEdit')
    manager._scanStartWidget = line_edit
    line_edit.setText('888731990032')

    manager._defer_barcode_field_value(line_edit, '8887319900328')
    QTest.qWait(100)

    assert line_edit.text() == '8887319900328'
    parent.close()


def test_deferred_protected_restore_clears_late_scanner_character():
    ensure_app()
    parent = QWidget()
    with (
        patch('modules.devices.barcode_manager.BarcodeScanner.start'),
        patch('modules.devices.barcode_manager.trace_scanner_event'),
    ):
        manager = BarcodeManager(parent)
    line_edit = QLineEdit(parent)
    line_edit.setObjectName('netsPayLineEdit')
    manager._protectedManualText[line_edit] = '100'
    manager._scanStartWidget = line_edit

    manager._restore_confirmed_scan_text('8887319900328')
    line_edit.setText('1008887319900328')
    QTest.qWait(100)

    assert line_edit.text() == '100'
    parent.close()


def test_qt_first_key_snapshots_ordinary_field_before_scanner_text_lands():
    ensure_app()
    parent = QWidget()
    with (
        patch('modules.devices.barcode_manager.BarcodeScanner.start'),
        patch('modules.devices.barcode_manager.trace_scanner_event'),
    ):
        manager = BarcodeManager(parent)
    line_edit = QLineEdit(parent)
    line_edit.setObjectName('updateProductNameLineEdit')
    line_edit.setText('test')
    event = QKeyEvent(QEvent.KeyPress, Qt.Key_8, Qt.NoModifier, '8')

    manager.eventFilter(line_edit, event)
    line_edit.setText('test8887319900328')
    manager._restore_confirmed_scan_text('8887319900328')
    QTest.qWait(100)

    assert line_edit.text() == 'test'
    parent.close()


def test_completed_candidate_closes_focus_snapshot_but_keeps_enter_protection():
    ensure_app()
    parent = QWidget()
    with (
        patch('modules.devices.barcode_manager.BarcodeScanner.start'),
        patch('modules.devices.barcode_manager.trace_scanner_event'),
    ):
        manager = BarcodeManager(parent)
    line_edit = QLineEdit(parent)
    manager._scannerCandidateUntil = 123.0
    manager._suppressEnterUntil = 456.0
    manager._scanStartWidget = line_edit
    manager._preScanText = 'manual text'

    manager._on_scanner_candidate_completed(False)

    assert manager._scannerCandidateUntil == 0.0
    assert manager._scanStartWidget is None
    assert manager._preScanText is None
    assert manager._suppressEnterUntil == 456.0
    parent.close()
