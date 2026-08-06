# Temporary Barcode Scanner Trace

## Purpose

`live_logs/barcode_scanner_trace.log` captures the intermittent condition where the
physical scanner beeps but no item reaches the sales table. It is intentionally
separate from `error.log`, the status-footer error indicator, and the Diagnostics
menu.

The trace writer is observational and independent of scanner timing, focus,
routing, retries, listener recovery, product lookup, and sales-table behaviour.

## Recorded layers

`modules/devices/scanner.py` records listener start/stop, rejected candidates,
and callback exceptions. Normal emitted candidates are counted rather than
written individually. A rejected-candidate record includes candidate length,
duration, average and maximum inter-key gaps, gaps over the fast threshold, and
the fast-gap ratio. An inactivity boundary is recorded as
`candidate_abandoned`. Callback exceptions are recorded and contained so one
malformed global key event cannot terminate the listener thread.

`modules/devices/barcode_manager.py` immediately records rejected routes,
exceptions, and suspicious table outcomes. Records include focus at scan
start/completion, active window/modal, modal block, override presence, receipt
source, sales-table readiness, listener health, and table row counts where
applicable. Normal additions, increments, and dialog overrides are counted.

A read-only five-second health observation records only listener state changes.
Every five minutes, one compact `scanner_summary` compares emitted candidates,
received barcodes, successful routes, and rejected routes. It deliberately does
not restart or repair the listener.

Records are JSON lines with local ISO timestamps. Writing uses a bounded queue
and daemon writer so disk I/O is not performed in the keyboard callback. The log
rotates at 1 MiB with two backups. Logging failures are ignored and cannot affect
POS operation.

## Interpreting an occurrence

- No input-layer completion followed by `listener_alive=false`: listener failure.
- `candidate_rejected`: Enter completed input that failed length, timing, or
  inactivity classification.
- `candidate_abandoned`: an incomplete candidate exceeded the longer
  inactivity timeout before another printable character arrived.
- A summary with more emitted candidates than received barcodes: Qt signal
  delivery or scanner/manager object-lifecycle problem.
- `protected-manual-field`, `modal-block-open`, `hold-loaded`, or
  `sales-table-unavailable`: the named routing gate rejected the scan.
- `route_exception`: inspect the recorded exception and surrounding state.
- `added`/`incremented` with an unexpected row count: inspect table mutation.

## Temporary removal checklist

After the fault is identified:

1. Delete `modules/devices/scanner_trace_logger.py`.
2. Remove trace imports and calls from `scanner.py` and `barcode_manager.py`.
3. Remove the listener-health timer and `listener_is_alive()` if it is not needed
   for the permanent fix.
4. Remove the `BARCODE_SCANNER_TRACE_*` and
   `BARCODE_SCANNER_HEALTH_INTERVAL_MS` settings from `config.py`.
5. Delete `tests/test_barcode_scanner_trace.py` and this document, then remove
   the trace references from the scanner/config documentation.
6. The external trace files can be deleted independently; doing so does not
   alter or clear `error.log`.
