"""Temporary, isolated production tracing for intermittent barcode loss.

This module never writes to error.log and is not connected to the Diagnostics
menu or status-footer error indicator. Calls are non-blocking; a daemon writer
performs the file I/O so pynput's keyboard callback is not delayed by logging.
"""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import os
import queue
import threading
from datetime import datetime
from typing import Any

from config import (
    BARCODE_SCANNER_TRACE_BACKUP_COUNT,
    BARCODE_SCANNER_TRACE_ENABLED,
    BARCODE_SCANNER_TRACE_MAX_BYTES,
    BARCODE_SCANNER_TRACE_PATH,
)

_QUEUE: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=2000)
_START_LOCK = threading.Lock()
_WRITER_STARTED = False


def _serializable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return repr(value)


def trace_scanner_event(event: str, **fields: Any) -> None:
    """Queue one scanner trace record without affecting application behaviour."""
    if not BARCODE_SCANNER_TRACE_ENABLED:
        return
    try:
        _ensure_writer()
        record = {
            'timestamp': datetime.now().astimezone().isoformat(timespec='milliseconds'),
            'event': str(event),
            **{str(key): _serializable(value) for key, value in fields.items()},
        }
        _QUEUE.put_nowait(record)
    except Exception:
        # Diagnostic failure must never alter scanner or POS behaviour.
        pass


def _ensure_writer() -> None:
    global _WRITER_STARTED
    if _WRITER_STARTED:
        return
    with _START_LOCK:
        if _WRITER_STARTED:
            return
        thread = threading.Thread(
            target=_writer_loop,
            name='barcode-scanner-trace-writer',
            daemon=True,
        )
        thread.start()
        _WRITER_STARTED = True


def _writer_loop() -> None:
    handler = None
    try:
        os.makedirs(os.path.dirname(BARCODE_SCANNER_TRACE_PATH), exist_ok=True)
        handler = RotatingFileHandler(
            BARCODE_SCANNER_TRACE_PATH,
            maxBytes=BARCODE_SCANNER_TRACE_MAX_BYTES,
            backupCount=BARCODE_SCANNER_TRACE_BACKUP_COUNT,
            encoding='utf-8',
        )
        handler.setFormatter(logging.Formatter('%(message)s'))
    except Exception:
        handler = None

    while True:
        record = _QUEUE.get()
        try:
            if handler is not None:
                log_record = logging.LogRecord(
                    name='barcode_scanner_trace',
                    level=logging.INFO,
                    pathname='',
                    lineno=0,
                    msg=json.dumps(record, ensure_ascii=False, separators=(',', ':')),
                    args=(),
                    exc_info=None,
                )
                handler.emit(log_record)
        except Exception:
            pass
        finally:
            _QUEUE.task_done()
