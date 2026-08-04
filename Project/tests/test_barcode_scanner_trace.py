from unittest.mock import Mock, patch

from pynput import keyboard

from modules.devices.scanner import BarcodeScanner


def _character(value):
    key = Mock()
    key.char = value
    return key


def test_completed_candidate_is_counted_without_per_scan_trace_or_signal_change():
    scanner = BarcodeScanner(timeout=0.10)
    emitted = []
    scanner.barcode_scanned.connect(emitted.append)

    with (
        patch('modules.devices.scanner.time.time', side_effect=[1.00, 1.01, 1.02, 1.03]),
        patch('modules.devices.scanner.trace_scanner_event') as trace,
    ):
        scanner._on_key_press(_character('1'))
        scanner._on_key_press(_character('2'))
        scanner._on_key_press(_character('3'))
        scanner._on_key_press(keyboard.Key.enter)

    assert emitted == ['123']
    trace.assert_not_called()
    assert scanner.take_trace_summary() == {
        'candidates_emitted': 1,
        'candidates_rejected': 0,
    }


def test_short_candidate_is_traced_but_remains_rejected():
    scanner = BarcodeScanner(timeout=0.10)
    emitted = []
    scanner.barcode_scanned.connect(emitted.append)

    with (
        patch('modules.devices.scanner.time.time', side_effect=[1.00, 1.01, 1.02]),
        patch('modules.devices.scanner.trace_scanner_event') as trace,
    ):
        scanner._on_key_press(_character('1'))
        scanner._on_key_press(_character('2'))
        scanner._on_key_press(keyboard.Key.enter)

    assert emitted == []
    assert trace.call_args.args == ('candidate_rejected',)
    assert trace.call_args.kwargs['reason'] == 'below-minimum-length'
    assert scanner.take_trace_summary() == {
        'candidates_emitted': 0,
        'candidates_rejected': 1,
    }


def test_none_character_events_are_ignored_without_corrupting_buffer():
    scanner = BarcodeScanner(timeout=0.10)
    invalid_key = Mock()
    invalid_key.char = None
    invalid_key.vk = 255

    with (
        patch('modules.devices.scanner.time.time', side_effect=[1.00, 1.01]),
        patch('modules.devices.scanner.trace_scanner_event') as trace,
    ):
        scanner._on_key_press(invalid_key)
        scanner._on_key_press(invalid_key)

    assert scanner._buffer == ''
    assert [call.args[0] for call in trace.call_args_list] == [
        'non_character_key_ignored',
        'non_character_key_ignored',
    ]
    assert trace.call_args.kwargs['virtual_key'] == 255


def test_none_character_event_does_not_disrupt_following_barcode():
    scanner = BarcodeScanner(timeout=0.10)
    emitted = []
    scanner.barcode_scanned.connect(emitted.append)
    invalid_key = Mock()
    invalid_key.char = None

    with (
        patch(
            'modules.devices.scanner.time.time',
            side_effect=[1.00, 2.00, 2.01, 2.02, 2.03],
        ),
        patch('modules.devices.scanner.trace_scanner_event'),
    ):
        scanner._on_key_press(invalid_key)
        scanner._on_key_press(_character('1'))
        scanner._on_key_press(_character('2'))
        scanner._on_key_press(_character('3'))
        scanner._on_key_press(keyboard.Key.enter)

    assert emitted == ['123']


def test_unexpected_callback_exception_is_traced_and_contained():
    scanner = BarcodeScanner(timeout=0.10)

    with (
        patch.object(scanner, '_process_key_press', side_effect=RuntimeError('boom')),
        patch('modules.devices.scanner.trace_scanner_event') as trace,
    ):
        assert scanner._on_key_press(_character('1')) is None

    assert scanner._buffer == ''
    assert trace.call_args.args == ('listener_callback_exception',)


def test_trace_does_not_turn_invalid_buffer_at_enter_into_a_new_failure():
    scanner = BarcodeScanner(timeout=0.10)
    scanner._buffer = None

    with patch('modules.devices.scanner.trace_scanner_event') as trace:
        scanner._on_key_press(keyboard.Key.enter)

    assert scanner._buffer == ''
    assert trace.call_args.kwargs['reason'] == 'empty-buffer'


def test_listener_health_check_does_not_restart_listener():
    scanner = BarcodeScanner()
    scanner._listener = Mock()
    scanner._listener.is_alive.return_value = False

    assert scanner.listener_is_alive() is False
    scanner._listener.start.assert_not_called()
