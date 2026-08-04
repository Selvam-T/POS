"""
Barcode Scanner Module
Listens for rapid keyboard input from barcode scanners using pynput.
Emits Qt signals when complete barcodes are detected.

Usage:
    scanner = BarcodeScanner()
    scanner.barcode_scanned.connect(my_handler_function)
    scanner.start()
"""

from PyQt5.QtCore import QObject, pyqtSignal
from pynput import keyboard
import time

from config import SCANNER_KEY_INTERVAL_SECONDS
from modules.devices.scanner_trace_logger import trace_scanner_event


class BarcodeScanner(QObject):
    """
    Barcode scanner listener that distinguishes scanner input from manual typing.
    
    Signals:
        barcode_scanned(str): Emitted when a complete barcode is detected
    """
    
    # Qt Signal: emitted when barcode is scanned
    barcode_scanned = pyqtSignal(str)
    # Activity signal: emitted on every key press with timestamp and fast-key flag.
    scanner_activity = pyqtSignal(float, bool)
    
    def __init__(self, timeout=None):
        """
        Initialize barcode scanner.
        
        Args:
            timeout: Time threshold in seconds to distinguish scanner from manual typing
                    Scanner typically inputs characters in <50ms intervals
                    Manual typing is typically >100ms intervals
        """
        super().__init__()
        self._buffer = ''
        self._last_time = 0
        self._timeout = SCANNER_KEY_INTERVAL_SECONDS if timeout is None else timeout
        self._listener = None
        self._listener_thread = None
        self._enabled = True
        self._min_barcode_length = 3  # Minimum characters for valid barcode
        self._candidate_started_at = 0.0
        self._candidate_max_gap = 0.0
        self._candidate_slow_gaps = 0
        self._candidate_resets = 0
        self._trace_emitted_candidates = 0
        self._trace_rejected_candidates = 0
        
    def start(self):
        """Start listening for barcode scanner input."""
        if self._listener is not None:
            return
            
        # Create keyboard listener
        self._listener = keyboard.Listener(on_press=self._on_key_press)
        
        # Start listener in background thread
        self._listener.start()
        trace_scanner_event(
            'listener_started',
            timeout_seconds=self._timeout,
            listener_alive=self.listener_is_alive(),
        )
        
    def stop(self):
        """Stop listening for barcode scanner input."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
            self._buffer = ''
            self._reset_candidate_metrics()
            trace_scanner_event('listener_stopped')
            
    def set_enabled(self, enabled: bool):
        """
        Enable or disable barcode processing without stopping the listener.
        
        Args:
            enabled: True to process barcodes, False to ignore
        """
        self._enabled = enabled
        trace_scanner_event('scanner_enabled_changed', enabled=bool(enabled))
        if not enabled:
            self._buffer = ''  # Clear buffer when disabled
            
    def listener_is_alive(self) -> bool:
        """Return listener-thread health without starting or repairing it."""
        listener = self._listener
        if listener is None:
            return False
        try:
            return bool(listener.is_alive())
        except Exception:
            try:
                return bool(listener.running)
            except Exception:
                return False

    def _on_key_press(self, key):
        """
        Callback for keyboard events from pynput.
        
        Args:
            key: The key that was pressed
        """
        try:
            return self._process_key_press(key)
        except Exception as exc:
            trace_scanner_event(
                'listener_callback_exception',
                exception=repr(exc),
                key_repr=repr(key),
                virtual_key=getattr(key, 'vk', None),
                scan_code=getattr(key, '_scan', None),
                buffer_length=(
                    len(self._buffer) if isinstance(self._buffer, (str, bytes)) else None
                ),
                buffer_type=type(self._buffer).__name__,
            )
            # A malformed or unsupported global key event must not terminate
            # pynput's listener thread. Restore the scanner invariant and wait
            # for the next candidate instead.
            self._buffer = ''
            self._last_time = 0
            self._reset_candidate_metrics()
            return None

    def _process_key_press(self, key):
        """Process one keyboard event using the existing scanner algorithm."""
        if not self._enabled:
            return

        if not isinstance(self._buffer, str):
            trace_scanner_event(
                'scanner_buffer_recovered',
                previous_buffer_type=type(self._buffer).__name__,
            )
            self._buffer = ''
            self._last_time = 0
            self._reset_candidate_metrics()

        now = time.time()
        time_diff = now - self._last_time
        is_fast = self._last_time > 0 and time_diff <= self._timeout
        try:
            self.scanner_activity.emit(now, is_fast)
        except Exception:
            pass
        
        try:
            # Get character from key
            char = key.char
        except AttributeError:
            # Handle special keys (Enter, Shift, etc.)
            if key == keyboard.Key.enter:
                diagnostic_buffer = self._buffer
                buffer_is_text = isinstance(diagnostic_buffer, str)
                candidate = diagnostic_buffer.strip() if buffer_is_text else ''
                raw_length = len(diagnostic_buffer) if buffer_is_text else None
                emitted = bool(
                    buffer_is_text
                    and candidate
                    and raw_length >= self._min_barcode_length
                )
                reason = 'emitted' if emitted else (
                    'empty-buffer' if not diagnostic_buffer else (
                        'below-minimum-length' if buffer_is_text else 'invalid-buffer-type'
                    )
                )
                if emitted:
                    self._trace_emitted_candidates += 1
                else:
                    self._trace_rejected_candidates += 1
                    trace_scanner_event(
                        'candidate_rejected',
                        barcode=candidate,
                        raw_length=raw_length,
                        buffer_type=type(diagnostic_buffer).__name__,
                        reason=reason,
                        duration_seconds=(now - self._candidate_started_at) if self._candidate_started_at else None,
                        maximum_inter_key_gap_seconds=self._candidate_max_gap,
                        gaps_over_threshold=self._candidate_slow_gaps,
                        buffer_resets=self._candidate_resets,
                    )
                if self._buffer and len(self._buffer) >= self._min_barcode_length:
                    # Enter key pressed with data in buffer → barcode complete
                    barcode = self._buffer.strip()
                    if barcode:
                        # Emit Qt signal (thread-safe)
                        self.barcode_scanned.emit(barcode)
                    self._buffer = ''
                else:
                    self._buffer = ''
                self._reset_candidate_metrics()
            return

        # pynput can represent an untranslatable Windows virtual-key event as
        # KeyCode(char=None). It is not barcode text and must never be stored
        # in the string buffer. Keep a compact anomaly trace while ignoring it.
        if char is None:
            trace_scanner_event(
                'non_character_key_ignored',
                key_repr=repr(key),
                virtual_key=getattr(key, 'vk', None),
                scan_code=getattr(key, '_scan', None),
                time_since_previous_key_seconds=(
                    time_diff if self._last_time > 0 else None
                ),
                within_scanner_interval=is_fast,
                buffer_length=len(self._buffer),
            )
            return
        
        # Check timing to distinguish scanner from manual typing
        if time_diff > self._timeout:
            # Slow typing → likely manual input, start new buffer
            self._buffer = char
            if self._candidate_started_at:
                self._candidate_slow_gaps += 1
                self._candidate_resets += 1
            else:
                self._candidate_started_at = now
            
        else:
            # Fast input → likely scanner, append to buffer
            self._buffer += char

        if not self._candidate_started_at:
            self._candidate_started_at = now
        if self._last_time > 0:
            self._candidate_max_gap = max(self._candidate_max_gap, time_diff)
            
            
        self._last_time = now

    def _reset_candidate_metrics(self):
        self._candidate_started_at = 0.0
        self._candidate_max_gap = 0.0
        self._candidate_slow_gaps = 0
        self._candidate_resets = 0

    def take_trace_summary(self):
        """Return and reset compact input counts for periodic diagnostics."""
        summary = {
            'candidates_emitted': self._trace_emitted_candidates,
            'candidates_rejected': self._trace_rejected_candidates,
        }
        self._trace_emitted_candidates = 0
        self._trace_rejected_candidates = 0
        return summary
