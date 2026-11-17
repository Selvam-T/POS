"""Global keyboard listener and timing-based barcode classification."""

import time

from PyQt5.QtCore import QObject, pyqtSignal
from pynput import keyboard

from config import (
    SCANNER_CANDIDATE_INACTIVITY_SECONDS,
    SCANNER_KEY_INTERVAL_SECONDS,
    SCANNER_LONG_CODE_MIN_LENGTH,
    SCANNER_MAX_AVERAGE_GAP_SECONDS,
    SCANNER_MIN_FAST_GAP_RATIO,
)
from modules.devices.scanner_trace_logger import trace_scanner_event


class BarcodeScanner(QObject):
    """Retain keyboard candidates until Enter and emit scanner-like ones."""

    barcode_scanned = pyqtSignal(str)
    # Closes the manager's candidate snapshot after routing.
    candidate_completed = pyqtSignal(bool)
    # Boolean indicates whether the latest gap was scanner-fast.
    scanner_activity = pyqtSignal(float, bool)

    def __init__(self, timeout=None, inactivity_timeout=None):
        super().__init__()
        self._buffer = ''
        self._last_time = 0.0
        self._timeout = SCANNER_KEY_INTERVAL_SECONDS if timeout is None else timeout
        self._inactivity_timeout = (
            SCANNER_CANDIDATE_INACTIVITY_SECONDS
            if inactivity_timeout is None
            else inactivity_timeout
        )
        self._listener = None
        self._enabled = True
        self._min_barcode_length = 3
        self._candidate_started_at = 0.0
        self._candidate_max_gap = 0.0
        self._candidate_slow_gaps = 0
        self._candidate_gaps = []
        self._trace_emitted_candidates = 0
        self._trace_rejected_candidates = 0

    def start(self):
        """Start listening for global keyboard input."""
        if self._listener is not None:
            return
        self._listener = keyboard.Listener(on_press=self._on_key_press)
        self._listener.start()
        trace_scanner_event(
            'listener_started',
            fast_gap_seconds=self._timeout,
            inactivity_timeout_seconds=self._inactivity_timeout,
            listener_alive=self.listener_is_alive(),
        )

    def stop(self):
        """Stop listening and discard any unfinished candidate."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
            self._clear_candidate()
            trace_scanner_event('listener_stopped')

    def set_enabled(self, enabled: bool):
        """Enable or disable barcode processing without stopping the listener."""
        self._enabled = enabled
        trace_scanner_event('scanner_enabled_changed', enabled=bool(enabled))
        if not enabled:
            self._clear_candidate()

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
        """Contain malformed global key events so the listener stays alive."""
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
            self._clear_candidate()
            return None

    def _process_key_press(self, key):
        """Process one event without using a single slow gap as a reset."""
        if not self._enabled:
            return

        if not isinstance(self._buffer, str):
            trace_scanner_event(
                'scanner_buffer_recovered',
                previous_buffer_type=type(self._buffer).__name__,
            )
            self._clear_candidate()

        now = time.monotonic()
        time_diff = now - self._last_time
        is_fast = self._last_time > 0 and time_diff <= self._timeout
        try:
            self.scanner_activity.emit(now, is_fast)
        except Exception:
            pass

        try:
            char = key.char
        except AttributeError:
            if key == keyboard.Key.enter:
                self._finish_candidate(now, time_diff)
            return

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

        # Only prolonged inactivity starts a new candidate.
        if self._last_time > 0 and time_diff > self._inactivity_timeout:
            self._trace_abandoned_candidate(now, time_diff)
            self._clear_candidate()

        if not self._buffer:
            self._candidate_started_at = now
        elif self._last_time > 0:
            self._candidate_gaps.append(time_diff)
            self._candidate_max_gap = max(self._candidate_max_gap, time_diff)
            if time_diff > self._timeout:
                self._candidate_slow_gaps += 1

        self._buffer += char
        self._last_time = now

    def _finish_candidate(self, now, time_diff):
        candidate = self._buffer.strip()
        raw_length = len(self._buffer)
        expired = bool(self._last_time and time_diff > self._inactivity_timeout)
        emitted, reason, metrics = self._classify_candidate(
            candidate, raw_length, expired
        )
        if emitted:
            self._trace_emitted_candidates += 1
            self.barcode_scanned.emit(candidate)
        else:
            self._trace_rejected_candidates += 1
            trace_scanner_event(
                'candidate_rejected',
                barcode=candidate,
                raw_length=raw_length,
                buffer_type=type(self._buffer).__name__,
                reason=reason,
                duration_seconds=(
                    now - self._candidate_started_at
                    if self._candidate_started_at else None
                ),
                maximum_inter_key_gap_seconds=self._candidate_max_gap,
                gaps_over_threshold=self._candidate_slow_gaps,
                **metrics,
            )
        self.candidate_completed.emit(emitted)
        self._clear_candidate()

    def _classify_candidate(self, candidate, raw_length, expired):
        gaps = list(self._candidate_gaps)
        gap_count = len(gaps)
        fast_gap_count = sum(1 for gap in gaps if gap <= self._timeout)
        fast_gap_ratio = fast_gap_count / gap_count if gap_count else 0.0
        average_gap = sum(gaps) / gap_count if gap_count else None
        metrics = {
            'average_inter_key_gap_seconds': average_gap,
            'fast_gap_count': fast_gap_count,
            'inter_key_gap_count': gap_count,
            'fast_gap_ratio': fast_gap_ratio,
        }

        if expired:
            return False, 'candidate-inactivity-timeout', metrics
        if not candidate:
            return False, 'empty-buffer', metrics
        if raw_length < self._min_barcode_length:
            return False, 'below-minimum-length', metrics

        average_is_scanner_like = (
            average_gap is not None
            and average_gap <= SCANNER_MAX_AVERAGE_GAP_SECONDS
        )
        majority_is_fast = fast_gap_ratio >= SCANNER_MIN_FAST_GAP_RATIO
        long_fast_sequence = (
            raw_length >= SCANNER_LONG_CODE_MIN_LENGTH
            and average_is_scanner_like
        )
        if (majority_is_fast and average_is_scanner_like) or long_fast_sequence:
            return True, 'emitted', metrics
        return False, 'timing-not-scanner-like', metrics

    def _trace_abandoned_candidate(self, now, inactivity_gap):
        if not self._buffer:
            return
        self._trace_rejected_candidates += 1
        trace_scanner_event(
            'candidate_abandoned',
            barcode=self._buffer.strip(),
            raw_length=len(self._buffer),
            reason='candidate-inactivity-timeout',
            duration_seconds=(
                now - self._candidate_started_at
                if self._candidate_started_at else None
            ),
            inactivity_gap_seconds=inactivity_gap,
            maximum_inter_key_gap_seconds=self._candidate_max_gap,
            gaps_over_threshold=self._candidate_slow_gaps,
        )

    def _clear_candidate(self):
        self._buffer = ''
        self._last_time = 0.0
        self._reset_candidate_metrics()

    def _reset_candidate_metrics(self):
        self._candidate_started_at = 0.0
        self._candidate_max_gap = 0.0
        self._candidate_slow_gaps = 0
        self._candidate_gaps = []

    def take_trace_summary(self):
        """Return and reset compact input counts for periodic diagnostics."""
        summary = {
            'candidates_emitted': self._trace_emitted_candidates,
            'candidates_rejected': self._trace_rejected_candidates,
        }
        self._trace_emitted_candidates = 0
        self._trace_rejected_candidates = 0
        return summary
