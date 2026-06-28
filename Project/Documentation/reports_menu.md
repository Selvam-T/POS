# Reports Menu Functional Notes

## Scope
This document summarizes the current functional design for report-menu wiring, focusing on the active helper functions and behaviors.

## Core Controller Function
### `modules/menu/report_menu.py`
- `launch_reports_dialog(host_window)`
  - Loads and returns the report dialog (`ui/report_menu.ui`) as modal + frameless.
  - Applies shared dialog stylesheet (`assets/qss/dialog.qss`).
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
    - `Sales_record_pdf_11apr2026_12-44.pdf`
    - `Sales_record_xlsx_11apr2026_12-44.xlsx`
    - `Sales_trends_pdf_11apr2026_12-44.pdf`
    - `Inactivity_report_xlsx_11apr2026_12-44.xlsx`
  - `chartReportBtn` supports PDF export only; `saveExcelReportBtn` is
    enabled while chart is selected but clicking it shows a friendly message: "Chart saving to Excel is not available."
  - Chart report generation uses shared repository helpers and opens a chart
    viewer window instead of the text report viewer.
  - Sets default landing focus to `viewReportBtn` (deferred to next event loop tick).

- `_apply_role_default_state(dlg, is_admin)`
  - **Both Admin and Staff now land on Detailed report by default.**
  - Admin role permissions:
    - `salesReportBtn`: enabled (not locked)
    - `insightReportBtn`: enabled, subject to date-range gating (see below)
    - `chartReportBtn`: enabled
    - `inactivityReportBtn`: enabled
    - `dateRangeRadioBtn`: enabled
    - `todayRadioBtn`: selected (default)
  - **Staff role permissions:**
    - `salesReportBtn`: **disabled** with locked property applied — Staff can only view Detail reports; button is auto-selected without requiring user interaction
    - `insightReportBtn`: **disabled with locked property** (Staff cannot access)
    - `chartReportBtn`: **disabled with locked property** (Staff cannot access)
    - `inactivityReportBtn`: **disabled with locked property** (Staff cannot access)
    - `dateRangeRadioBtn`: disabled, greyed out (Staff locked to "Today" mode)
    - `todayRadioBtn`: selected (default)

  - **Staff Report Button Restrictions — Implementation Detail:**
    - **Reason for disabling all report buttons:** All `*ReportBtn` buttons are disabled for Staff to prevent QSS pseudo-selector effects (`:hover` and `:focus`) from displaying incorrectly on the default-selected `salesReportBtn`. By disabling all report buttons, the `:disabled` pseudo-selector takes precedence in the stylesheet, preventing unintended visual feedback.
    - **Locked property + QSS styling:** Each report button has the `locked` dynamic property set to `true` via `set_locked_property(button, true)`. The stylesheet rule `QPushButton[locked="true"]:disabled` applies a grey background (#b8bdc4), dimmed border (#9ea4ad), and white text color (#e8eaed) to create a visually locked appearance.
    - **Hidden buttons via white font:** Non-default buttons (`insightReportBtn`, `chartReportBtn`, `inactivityReportBtn`) use the same white text color in the locked/disabled state, making them visually indistinguishable from the background and effectively hidden while remaining accessible to screen readers and keyboard navigation.
    - **Auto-default selection without user interaction:** `salesReportBtn` is always set to `.setChecked(True)` regardless of user role. For Staff users, this means the Detail report is automatically selected when the dialog opens, without requiring any button click. The button remains disabled to prevent the user from attempting other report types.
    - **Controller implementation:**
      ```python
      detail.setEnabled(not is_admin)      # salesReportBtn disabled for Staff
      set_locked_property(detail, not is_admin)  # locked=true for Staff
      detail.setChecked(True)               # Always checked by default
      ```
    - **QSS rule (`assets/qss/dialog.qss`):**
      ```css
      QPushButton[locked="true"]:disabled {
          background-color: #b8bdc4;
          border: 1px solid #9ea4ad;
          color: #e8eaed;
      }
      ```

  - **Date-range gating for Summary button (Admin only):**
    - When Admin selects "Date Range", Insight button is locked (disabled, greyed)
    - When Admin selects "Today", Insight button is unlocked (enabled, clickable)
    - Staff users always see Insight locked regardless of date mode

- `_defer_focus(widget)`
  - Utility to apply focus on the next event-loop tick (`QTimer.singleShot(0, ...)`) for reliable focus landing.

- `_current_report_type(dlg)`
  - Resolves selected report type from report buttons (`detail|summary|chart|inactivity`).

- `_build_report_params(dlg, host_window)`
  - Collects date range + user context params for report data requests.

- Detailed report integration
  - For `detail` selection, `viewReportBtn` calls
    `modules.menu.report_generator.get_detailed_report(...)`.
  - Viewer rendering is delegated to `modules.menu.report_viewers.open_report_viewer(...)`.
  - Staff users receive the **minimal detailed report** variant:
    - Sections 4 and 5 are omitted
    - The remaining sections are renumbered so Cash Outflows Detail becomes section 4 and Other Activity becomes section 5
    - The same report payload is reused for viewer, PDF, and Excel export; the presentation layer switches the section set based on the Staff detail variant flag
  - **Column layout (sections 4–5):**
    - Section 4 (Earnings Broken Down by Category): Amount column width increased to 14 characters
    - Section 5 (Top 10 Best Sellers By Earnings): Amount column width increased to 14 characters
    - Improves readability and alignment of currency values.
  - Currency values are formatted through `modules/ui_utils/money_format.format_currency(...)`
    as `$ 1,234.56`.
  - Gross/payment totals use rounded payable receipt totals. Product/category
    earnings use true item line totals; when they differ, the report payload
    includes a computed rounding adjustment.

- Summary report integration
  - For `summary` selection, `viewReportBtn` calls
    `modules.menu.report_generator.get_summary_report(...)`.
  - Summary rendering uses the same shared viewer shell and searchable text
    layout as detailed, but with summary-specific sections:
    sales by hour, top products by hour/day, and top 5 product lists.
  - **Summary report access control:**
    - **Admin users:** Can access Summary report; subject to date-range gating.
      When Admin selects "Date Range", Summary button is locked and disabled.
      When Admin selects "Today", Summary button is unlocked and re-enabled.
    - **Staff users:** Cannot access Summary report; button is permanently disabled,
      greyed out, and non-clickable.
  - **Column layout (sections 3–6):**
    - "Avg Qty" column width: 16 characters
    - Extra spacing (2 spaces) between "Avg Qty" and "Avg Revenue" columns
    - Improves visual separation and readability of product rankings

- Chart report integration
  - For `chart` selection, `viewReportBtn` calls
    `modules.menu.report_generator.get_chart_report(...)`.
  - Chart rendering is done in a dedicated viewer window with actual chart
    widgets.
  - Chart currency labels use `modules/ui_utils/money_format.format_currency(...)`
    for the same `$ 1,234.56` display style as text reports.
  - Chart export is PDF-only; Excel export is disabled and the controller
    shows a friendly message if the user tries to save XLSX.
  - Chart metrics are averaged over the selected date range before rendering.

- Inactivity report integration
  - For `inactivity` selection, `viewReportBtn` calls
    `modules.menu.report_generator.get_inactivity_report(...)`.
  - Inactivity rendering uses the same shared viewer shell and searchable text
    layout as detailed/summary, with fixed-width tables for inactive product
    buckets and the summary count block.
  - While `inactivityReportBtn` is selected, the date-range frame is
    temporarily locked: `dateRangeRadioBtn` is disabled, the date edits are
    read-only/greyed, and the field labels are dimmed. When the button is
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

### Quantity Display Formatting
- When displaying quantities (`qty_sold`), the viewer applies the following rules:
  - **For 'ea' (each) units:**
    - If `qty >= 1`, display as an integer (rounded) e.g., "5 ea" or "2 ea" for 1.5
    - If `0 < qty < 1`, display with two decimal places (e.g., "0.50 ea")
    - This avoids showing "0 ea" for small non-zero averages while keeping larger
      counts succinct.
  - **For 'kg' (weight) units:**
    - If `qty >= 1.0 kg`, display as "X.XX kg" (two decimal places)
    - If `0 < qty < 1.0 kg`, convert to grams and display as whole grams when >= 1 g (e.g., "500 g")
    - If converted grams < 1 g, display as a two-decimal gram value (e.g., "0.50 g")
  - **Default for other units:**
    - If `0 < qty < 1`, display with two decimal places; otherwise show a 3-decimal fallback
      for larger fractional values.
  - **Rationale:** Consistent two-decimal presentation for small quantities prevents
    misleading zero displays while keeping unit conversions readable.
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
    writes the failure to `logs/error.log`.
  - Reason: this is a dependency failure, not a size failure. When the package
    is available, Excel export proceeds normally, even for large reports.
- In both PDF and Excel paths, the controller logs unexpected failures and
  updates the report status label so the user sees a safe, short message.

## Summary Report Section Structure
### Report Sections (On-screen Viewer & XLSX Export)

The summary report displays business trends and patterns with the following structure:

1. **Average Sales Summary** — High-level overview of daily averages (receipt count, gross sales, outflows, net)
2. **Average Hourly Earnings** — Summary table and peak hour indicator
3. **Top Earning Items (By Hour)** — Products ranked by earnings within each hourly bucket
   - **Split by unit type** (to avoid comparing pieces vs. weights):
     - Pieces (unit = Each/ea): top 3 per hour
     - Weight (unit = kg/g): top 3 per hour
   - Rendered with a blank row separating each unit-type sub-list
   - Sorted by earnings (line_sales) descending; ties broken by quantity ascending
   
4. **Most Popular Items (By Hour)** — Products ranked by quantity sold within each hourly bucket
   - **Split by unit type**:
     - Pieces (unit = Each/ea): top 3 per hour
     - Weight (unit = kg/g): top 3 per hour
   - Rendered with a blank row separating each unit-type sub-list
   - Sorted by quantity descending; ties broken by earnings ascending

5. **Most Consistent Sellers (By Earnings)** — Products with highest total earnings across the period
   - **Split by unit type**:
     - Pieces (unit = Each/ea): top 10
     - Weight (unit = kg/g): top 5
   - Rendered with a blank row separating each unit-type sub-list
   - Sorted by earnings (line_sales) descending; ties broken by quantity ascending

6. **Most Consistent Sellers (By Quantity)** — Products with highest total quantity sold across the period
   - **Split by unit type**:
     - Pieces (unit = Each/ea): top 10
     - Weight (unit = kg/g): top 5
   - Rendered with a blank row separating each unit-type sub-list
   - Sorted by quantity descending; ties broken by earnings ascending

### Rationale for Unit Type Splitting
- Comparing pieces (counted as individual items) with weights (measured in kg/grams) is misleading.
  For example, ranking 1000 pieces of sponges alongside 5 kg of apples would incorrectly suggest
  the sponges are more popular, even if apples generated more revenue or volume.
- By splitting, the report shows true rankings within each unit category, allowing fair comparisons.

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

- `init_date_range_bounds(from_date_edit, to_date_edit, today=None)`
  - Initializes both date edits to today.
  - Prevents future date selection by setting both maximum dates to today.
  - Applies the shared range constraint that To date cannot be earlier than From date.

- `clamp_date_range_bounds(from_date_edit, to_date_edit, today=None)`
  - Keeps both date edits capped at today.
  - Sets `to_date_edit.minimumDate` from the current From date.
  - Auto-clamps To date if it becomes earlier than From date.
  - This helper is also used directly by Receipt History, which has an always-active date range and does not use report's radio/action gating flow.

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
      - both date edits are capped at today through shared date-range helpers
      - `to_date_edit` minimum date follows selected From date
      - To date auto-clamped if it becomes earlier than From date
    - label lock behavior:
      - when date-range is unavailable/unselected, passed field labels are marked `locked=true`
      - when date-range is selected/active, labels are restored (`locked=false`)

## Styling Hooks (QSS)
### `assets/qss/dialog.qss`
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
- Viewer styling hooks are centralized in `assets/qss/dialog.qss` using viewer object names.

See the report generator adapter and data-layer notes: Documentation/report_generator.md
