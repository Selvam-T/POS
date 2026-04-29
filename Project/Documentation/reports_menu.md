# Reports Menu Functional Notes

## Scope
This document summarizes the current functional design for report-menu wiring, focusing on the active helper functions and behaviors.

## Core Controller Function
### `modules/menu/report_menu.py`
- `launch_reports_dialog(host_window)`
  - Loads and returns the report dialog (`ui/report_menu.ui`) as modal + frameless.
  - Applies shared dialog stylesheet (`assets/dialog.qss`).
  - Wires `customCloseBtn` and `btnReportCancel` using admin-style reject flow:
    - `customCloseBtn`: closes dialog and posts default non-error status (`Report dialog closed.`) to main status bar.
    - `btnReportCancel`: closes dialog and posts cancel non-error status (`Report selection cancelled.`) to main status bar.
  - Applies role defaults/permissions via `_apply_role_default_state(...)`.
  - Wires shared date gating via `DateRangeGateController`.
  - Wires `resetReportBtn` to restore defaults for report type and date frame.
  - Wires `viewReportBtn` to resolve selected report type, fetch detailed,
    summary, chart, or inactivity data when needed, and open viewer via
    `modules/menu/report_viewers.py`.
  - Wires `savePdfReportBtn` and `saveExcelReportBtn` to the shared export
    helper module `modules/menu/report_exports.py`.
  - Export files are written to `Path.home() / 'POS_Exports' / 'Reports'`.
  - Filename templates follow the report type and format, for example:
    - `Audit_report_pdf_11apr2026_12-44.pdf`
    - `Audit_report_xlsx_11apr2026_12-44.xlsx`
    - `Insight_report_pdf_11apr2026_12-44.pdf`
    - `Inactivity_report_xlsx_11apr2026_12-44.xlsx`
  - `chartReportRadioBtn` supports PDF export only; `saveExcelReportBtn` is
    disabled while chart is selected.
  - Chart report generation uses shared repository helpers and opens a chart
    viewer window instead of the text report viewer.
  - Sets default landing focus to `viewReportBtn` (deferred to next event loop tick).

- `_apply_role_default_state(dlg, is_admin)`
  - Admin defaults:
    - `detailReportRadioBtn` selected
    - `todayRadioBtn` selected
    - all report-type/date-range radios enabled
  - Staff defaults:
    - `summaryReportRadioBtn` selected
    - `todayRadioBtn` selected
    - `detailReportRadioBtn`, `chartReportRadioBtn`, `inactivityReportRadioBtn`, `dateRangeRadioBtn` disabled

- `_defer_focus(widget)`
  - Utility to apply focus on the next event-loop tick (`QTimer.singleShot(0, ...)`) for reliable focus landing.

- `_current_report_type(dlg)`
  - Resolves selected report type from report radio buttons (`detail|summary|chart|inactivity`).

- `_build_report_params(dlg, host_window)`
  - Collects date range + user context params for report data requests.

- Detailed report integration
  - For `detail` selection, `viewReportBtn` calls
    `modules.menu.report_generator.get_detailed_report(...)`.
  - Viewer rendering is delegated to `modules.menu.report_viewers.open_report_viewer(...)`.

- Summary report integration
  - For `summary` selection, `viewReportBtn` calls
    `modules.menu.report_generator.get_summary_report(...)`.
  - Summary rendering uses the same shared viewer shell and searchable text
    layout as detailed, but with summary-specific sections:
    sales by hour, top products by hour/day, and top 5 product lists.

- Chart report integration
  - For `chart` selection, `viewReportBtn` calls
    `modules.menu.report_generator.get_chart_report(...)`.
  - Chart rendering is done in a dedicated viewer window with actual chart
    widgets.
  - Chart export is PDF-only; Excel export is disabled and the controller
    shows a friendly message if the user tries to save XLSX.
  - Chart metrics are averaged over the selected date range before rendering.

- Inactivity report integration
  - For `inactivity` selection, `viewReportBtn` calls
    `modules.menu.report_generator.get_inactivity_report(...)`.
  - Inactivity rendering uses the same shared viewer shell and searchable text
    layout as detailed/summary, with fixed-width tables for inactive product
    buckets and the summary count block.
  - While `inactivityReportRadioBtn` is selected, the date-range frame is
    temporarily locked: `dateRangeRadioBtn` is disabled, the date edits are
    read-only/greyed, and the field labels are dimmed. When the radio is
    deselected, the current date-mode selection is restored.

## Viewer/UI Module
### `modules/menu/report_viewers.py`
- Owns viewer/dialog UI functions (no data fetching).
- Uses one shared viewer shell (`open_report_viewer`) with per-report renderers:
  - `detail`: searchable `QPlainTextEdit` with report text
  - `summary`: searchable `QPlainTextEdit` with report text
  - `inactivity`: searchable `QPlainTextEdit` with report text
  - Rationale: `QPlainTextEdit` is used for the detailed report to preserve
    fixed-width/monospaced column alignment and provide lightweight search
    without adding external PDF toolchains. `QTextBrowser` is better suited
    for complex HTML/CSS layouts; PDF export would require additional
    dependencies and is unnecessary for this simple, fixed-width design.
  - other types (`chart` and unknown values): placeholder content renderer
- Uses the shared `REPORT_VIEWER_RATIOS` tuple from `config.py` for viewer
  sizing, with a pixel fallback when the tuple is unavailable.
- Viewer closes via native window titlebar `X` button (no in-dialog Close push button).
- Applies dim overlay while viewer is open.

## Export Module
### `modules/menu/report_exports.py`
- Owns shared export helpers for report PDF and XLSX generation.
- Reuses the report text formatters from `report_viewers.py` for PDF output.
- Builds XLSX files from structured report data with one sheet per report section.
- Uses the shared export folder `Path.home() / 'POS_Exports' / 'Reports'`.

### Export fail-safe behavior
- PDF export is guarded before rendering starts for every implemented report
  type: `detail`, `summary`, and `inactivity`.
  - The controller estimates report size from the raw report data structure,
    not from the rendered PDF text.
  - The current cutoff is `5000` estimated render units.
  - This is a conservative safety cutoff to prevent long or unstable PDF
    rendering jobs.
  - How the estimate is derived:
    - `detail`: counts payment rows, category headers, category products,
      top-products rows, outflow rows, summary fields, and excluded fields.
    - `summary`: counts hourly rows, grouped product rows, day ranking rows,
      summary fields, excluded fields, and header metadata.
    - `inactivity`: counts section rows, inactive product rows, summary fields,
      and header metadata.
  - If the estimated size is greater than `5000`, PDF export is stopped
    immediately and the dialog shows: `Report is too large to export to PDF.`
  - Reason: Qt's text-to-PDF rendering can stall or produce a damaged PDF when
    the report becomes too large, so the app decides before layout begins.
  - Chart reports remain deferred for later implementation; the current chart
    branch still uses the placeholder export path.
- Excel export does not use a row-count threshold.
  - The save path checks whether `openpyxl` is available in the current Python
    environment.
  - If `openpyxl` is missing, the dialog shows a short friendly message and
    writes the failure to `log/error.log`.
  - Reason: this is a dependency failure, not a size failure. When the package
    is available, Excel export proceeds normally, even for large reports.
- In both PDF and Excel paths, the controller logs unexpected failures and
  updates the report status label so the user sees a safe, short message.

## Shared Date Gating Module
### `modules/date_time/date_gating.py`
- `set_locked_property(widget, locked)`
  - Sets dynamic property `locked=true/false` and refreshes style.

- `set_dateedit_locked(date_edit, locked)`
  - Locked state:
    - widget disabled
    - display format forced to blank (`' '`) and line-edit cleared
  - Unlocked state:
    - widget enabled
    - original date display format restored

- `set_buttons_locked(buttons, locked)`
  - Enables/disables button list and applies `locked` style property.

- `DateRangeGateController(...)`
  - Shared progressive gating controller for today/date-range flow.
  - Inputs:
    - `today_radio`, `date_range_radio`
    - `from_date_edit`, `to_date_edit`
    - `action_buttons`
    - optional `field_labels`
    - optional `on_actions_unlocked` callback
  - Behavior:
    - `todayRadioBtn` selected:
      - both date edits locked and visually blank
      - action buttons enabled
    - `dateRangeRadioBtn` selected:
      - focus lands on `from_date_edit`
      - `from_date_edit` unlocked first
      - `to_date_edit` remains locked until Enter on From
      - action buttons remain locked until Enter on To
      - on To Enter unlock, callback can move focus (used for `viewReportBtn`)
    - date consistency:
      - `to_date_edit` minimum date follows selected From date
      - To date auto-clamped if it becomes earlier than From date
    - label lock behavior:
      - when date-range is unavailable/unselected, passed field labels are marked `locked=true`
      - when date-range is selected/active, labels are restored (`locked=false`)

## Styling Hooks (QSS)
### `assets/dialog.qss`
- `QDateEdit[locked="true"]` and nested selectors enforce gray/blank locked date fields.
- `QDateEdit[locked="false"]` restores normal editable visuals.
- `QPushButton[objectName="viewReportBtn|savePdfReportBtn|saveExcelReportBtn"][locked="true"]`
  - disabled/locked action button styling.
- `QPushButton#viewReportBtn:focus`, `#savePdfReportBtn:focus`, `#saveExcelReportBtn:focus`
  - explicit orange focus border for report actions.
- `QRadioButton#dateRangeRadioBtn:disabled` and indicator disabled styles
  - gray disabled date-range radio visuals.
- `QLabel[objectName$="FieldLbl"][locked="true|false"]`
  - gray/restored color for date field labels.

## Current Status
- Role defaults and permissions are implemented.
- Shared date gating is implemented and reusable for future controllers.
- Focus landing and progressive focus jump to `viewReportBtn` are implemented.
- `resetReportBtn` restores report type/date defaults and lands focus on `viewReportBtn`.
- `viewReportBtn` now routes through `report_viewers.py` shared shell + per-report renderer architecture.
- Save buttons now export to PDF/XLSX through `report_exports.py`, with charts
  limited to PDF only.
- Chart viewer/export failures are handled safely: the controller logs the
  error and keeps the reports dialog usable.
- PDF export uses a pre-render fail-safe based on raw report dimensions for
  detail, summary, and inactivity reports.
- Excel export uses a dependency fail-safe for `openpyxl` and logs the failure safely.
- Viewer styling hooks are centralized in `assets/dialog.qss` using viewer object names.

See the report generator adapter and data-layer notes: Documentation/report_generator.md
