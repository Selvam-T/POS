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
        patch('modules.devices.scanner.time.monotonic', side_effect=[1.00, 1.01, 1.02, 1.03]),
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


def test_one_slow_gap_does_not_discard_barcode_prefix():
    scanner = BarcodeScanner(timeout=0.05, inactivity_timeout=0.75)
    emitted = []
    scanner.barcode_scanned.connect(emitted.append)
    code = '8887319900328'
    times = [1.00, 1.02, 1.04, 1.12]
    times.extend(1.12 + (index * 0.02) for index in range(1, 10))
    times.append(times[-1] + 0.02)

    with (
        patch('modules.devices.scanner.time.monotonic', side_effect=times),
        patch('modules.devices.scanner.trace_scanner_event') as trace,
    ):
        for char in code:
            scanner._on_key_press(_character(char))
        scanner._on_key_press(keyboard.Key.enter)

    assert emitted == [code]
    trace.assert_not_called()


def test_long_sequence_with_consistent_moderate_gaps_is_accepted():
    scanner = BarcodeScanner(timeout=0.05, inactivity_timeout=0.75)
    emitted = []
    scanner.barcode_scanned.connect(emitted.append)
    code = '8887319426163'
    times = [1.00 + (index * 0.08) for index in range(len(code) + 1)]

    with (
        patch('modules.devices.scanner.time.monotonic', side_effect=times),
        patch('modules.devices.scanner.trace_scanner_event') as trace,
    ):
        for char in code:
            scanner._on_key_press(_character(char))
        scanner._on_key_press(keyboard.Key.enter)

    assert emitted == [code]
    trace.assert_not_called()


def test_short_manual_speed_sequence_is_not_routed_as_barcode():
    scanner = BarcodeScanner(timeout=0.05, inactivity_timeout=0.75)
    emitted = []
    completions = []
    scanner.barcode_scanned.connect(emitted.append)
    scanner.candidate_completed.connect(completions.append)

    with (
        patch(
            'modules.devices.scanner.time.monotonic',
            side_effect=[1.00, 1.08, 1.16, 1.24, 1.32],
        ),
        patch('modules.devices.scanner.trace_scanner_event') as trace,
    ):
        for char in 'TEST':
            scanner._on_key_press(_character(char))
        scanner._on_key_press(keyboard.Key.enter)

    assert emitted == []
    assert completions == [False]
    assert trace.call_args.args == ('candidate_rejected',)
    assert trace.call_args.kwargs['reason'] == 'timing-not-scanner-like'


def test_inactivity_abandons_only_the_unfinished_candidate():
    scanner = BarcodeScanner(timeout=0.05, inactivity_timeout=0.75)
    emitted = []
    scanner.barcode_scanned.connect(emitted.append)

    with (
        patch(
            'modules.devices.scanner.time.monotonic',
            side_effect=[1.00, 1.02, 2.00, 2.02, 2.04, 2.06],
        ),
        patch('modules.devices.scanner.trace_scanner_event') as trace,
    ):
        scanner._on_key_press(_character('9'))
        scanner._on_key_press(_character('9'))
        scanner._on_key_press(_character('1'))
        scanner._on_key_press(_character('2'))
        scanner._on_key_press(_character('3'))
        scanner._on_key_press(keyboard.Key.enter)

    assert emitted == ['123']
    assert trace.call_args.args == ('candidate_abandoned',)
    assert trace.call_args.kwargs['barcode'] == '99'
    assert scanner.take_trace_summary() == {
        'candidates_emitted': 1,
        'candidates_rejected': 1,
    }


def test_short_candidate_is_traced_but_remains_rejected():
    scanner = BarcodeScanner(timeout=0.10)
    emitted = []
    scanner.barcode_scanned.connect(emitted.append)

    with (
        patch('modules.devices.scanner.time.monotonic', side_effect=[1.00, 1.01, 1.02]),
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
        patch('modules.devices.scanner.time.monotonic', side_effect=[1.00, 1.01]),
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
            'modules.devices.scanner.time.monotonic',
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
