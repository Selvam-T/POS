# Report Generator

This document describes the `modules/menu/report_generator.py` adapter and the
`modules/db_operation/reports_repo.py` data layer for generating sales
reports.

Purpose
- Provide a thin UI-facing API used by report dialogs to request report
  data without coupling the UI to SQL or aggregation logic.
- Centralize multi-table joins and aggregations in `reports_repo.py` so each
  report can be tested independently from the Qt UI.

Current status
- `get_detailed_report(params)` is implemented and returns structured Detailed
  Sales Report data from `modules/db_operation/reports_repo.py`.
- `get_summary_report(params)` is implemented and returns structured Summary
  Sales Report data from the same repository.
- `get_inactivity_report(params)` is implemented and returns structured
  Inactive Products Report data from the same repository.
- `get_chart_report(params)` is implemented and returns structured chart
  report data from the same repository.
- `modules/menu/report_menu.py` now calls this adapter when
  `detailReportRadioBtn`, `summaryReportRadioBtn`, `chartReportRadioBtn`, or
  `inactivityReportRadioBtn` is selected.
- Viewer/UI rendering is intentionally separated into
  `modules/menu/report_viewers.py` (shared shell + per-report content renderer).
  - Note: The detailed viewer uses `QPlainTextEdit` (monospaced, searchable)
    to preserve fixed-width column alignment and avoid introducing external
    PDF toolchains or heavier HTML-based rendering. `QTextBrowser` is more
    appropriate for complex HTML/CSS reports; for the current simple
    textual layout `QPlainTextEdit` keeps rendering lightweight and
    dependency-free.
- Report viewer sizes are controlled by the shared `REPORT_VIEWER_RATIOS`
  tuple in `config.py` and applied by `report_viewers.py`.
- Viewer exit is via native titlebar `X` close button.

Chart report note
- The Chart report is rendered in the viewer window using chart widgets and
  exported to PDF only.
- Chart data is normalized to the selected date range, so the chart values are
  expressed as averages per day rather than raw totals.
- The data layer reuses the same paid-receipt and receipt-item helpers used by
  the summary report; chart-specific aggregation lives in
  `modules/db_operation/reports_repo.py`.
- If the chart renderer is unavailable or chart generation fails, the caller
  should log the error and show a safe fallback message rather than crashing.

Summary report note
- The Summary report is now presented as Sales Trends & Patterns.
- Section 1 uses average values over the selected date range, and the hourly
  and day product sections continue to rank products by average quantity or
  sales rather than raw totals. This keeps the report normalized to the length
  of the report window.

Integration
- UI: import `modules.menu.report_generator` and call
  `get_detailed_report`, `get_summary_report`, or `get_inactivity_report`.
- Data: `report_generator` calls into `modules.db_operation.reports_repo`.

Implementation notes
- When implementing real queries, prefer reusing existing per-table repos
  (receipts_repo, receipt_items_repo, receipt_payments_repo, cash_outflows_repo)
  for single-table operations and let `reports_repo` coordinate complex
  joins/aggregations.

Testing
- `tests/test_reports_repo.py` validates that `detailed_report` returns the
  expected structure. Replace the stub with real SQL when ready; tests
  should be extended to validate aggregated values against a seeded test DB.
