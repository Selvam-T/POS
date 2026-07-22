"""Dedicated diagnostics for ignored or failed completed barcode scans."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from config import BARCODE_ROUTING_LOG_PATH


def log_barcode_routing(
    *,
    outcome: str,
    reason: str,
    barcode: str,
    log_path: str | Path | None = None,
    **context: Any,
) -> None:
    """Append one timestamped JSON record without affecting application flow."""
    try:
        path = Path(log_path or BARCODE_ROUTING_LOG_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            'timestamp': datetime.now().astimezone().isoformat(timespec='seconds'),
            'outcome': str(outcome or 'unknown'),
            'reason': str(reason or 'unspecified'),
            'barcode': str(barcode or ''),
        }
        record.update(context)
        with path.open('a', encoding='utf-8') as log_file:
            log_file.write(json.dumps(record, ensure_ascii=False, default=str) + '\n')
    except Exception:
        # Diagnostics must never interrupt payment or sales-table operation.
        pass
