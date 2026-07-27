# Diagnostics Menu

Updated: July 27, 2026

## Overview

The Diagnostics menu provides operator-initiated, read-only health checks for
the running POS installation. It is opened from the Diagnostics icon immediately
above Logout in the main right-side menu.

The dialog uses the shared frameless dialog design and `assets/qss/dialog.qss`.
It is opened through `DialogWrapper.open_dialog_scanner_blocked`, so barcode
scanner input is blocked while the modal is active and restored during wrapper
cleanup.

## Current Checks

The dialog presents seven selectable checks:

1. Database counts and SQLite integrity
2. Product cache consistency
3. Suspicious or incomplete product codes
4. Duplicate product names
5. Product data quality
6. Category integrity
7. Runtime assets and paths

The Database and Product Cache checks are enabled. The remaining five checks
are visible, disabled, and marked `Coming soon`.

## Database Check

The database diagnostic opens a separate SQLite connection using:

```text
mode=ro
PRAGMA query_only = ON
PRAGMA foreign_keys = ON
```

It does not reload the product cache and does not execute database writes.

The check records:

- Active database path and file size
- Start, completion, and elapsed time
- Presence of the seven core tables
- Row count for every present core table
- Optional `receipt_counters` row count when that runtime table exists
- SQLite `PRAGMA quick_check`
- SQLite `PRAGMA foreign_key_check`
- Whether foreign-key enforcement is enabled on the diagnostic connection

Core tables:

```text
Product_list
Category
users
receipts
receipt_items
receipt_payments
cash_outflows
```

The result is `PASS` only when:

- Every core table is present
- `quick_check` returns exactly `ok`
- No foreign-key violations exist
- Foreign-key enforcement is enabled on the diagnostic connection

Otherwise the result is `FAIL`, with report-friendly issue descriptions.

## Product Cache Check

The Product Cache diagnostic compares `Product_list` with the exact
`PRODUCT_CACHE` dictionary held by the running POS process.

It intentionally does not call:

```text
load_product_cache()
refresh_product_cache()
```

Reloading first would conceal the stale-session condition this check is meant
to detect. Product rows are read using a separate read-only SQLite connection.

The comparison uses the same product-code and display-text canonicalization as
the application cache loader. It records:

- Database product count
- Live cache entry count
- Fully consistent entry count
- Database products missing from the cache
- Cache entries missing from the database
- Name, selling-price, unit, and category mismatches
- Invalid or noncanonical cache keys
- Multiple raw cache keys that normalize to the same code
- Multiple database codes that normalize to the same code

Each value mismatch includes the affected fields and both the expected database
tuple and actual cache tuple.

The result is `PASS` only when every database product has one matching live
cache entry and no invalid, extra, duplicate-normalized, or mismatched entries
exist. An empty live cache therefore fails when products exist in the database.

The standalone developer command remains available:

```text
python dev_tools/diagnostics/check_product_cache_consistency.py
```

That command loads a cache only inside its own standalone process when needed.
The in-application Diagnostics menu never reloads the live cache before checking
it.

## Running State

When OK is selected:

1. At least one enabled checkbox must be selected.
2. OK, Cancel, Close, and the enabled checkboxes are locked.
3. `diagnosticStatusLabel` displays `Diagnostics running...` persistently.
4. Selected checks execute.
5. The completed in-memory result is exported.
6. The dialog closes and the saved report path is shown in the main StatusBar.

The running guard prevents repeated OK submission.

## Shared UI Utilities

The controller follows the same shared-utility conventions used by the Admin
menu:

- `dialog_utils.build_dialog_from_ui` and `build_error_fallback_dialog` provide
  consistent modal construction and UI-load fallback behavior.
- `dialog_utils.require_widgets` detects object-name or UI contract changes.
- `dialog_utils.set_dialog_info` and `set_dialog_error` carry final messages to
  the main StatusBar after the modal closes.
- `dialog_utils.log_exception_traceback_and_postclose_statusBar` logs export
  exceptions with tracebacks and sets the post-close error message.
- `focus_utils.set_initial_focus` places keyboard focus on the first enabled
  diagnostic checkbox.
- `focus_utils.FocusGate` locks the checkbox and action controls while checks
  are running.
- `ui_feedback.set_status_label` and `set_warning_status_label` display
  selection and running feedback inside `diagnosticStatusLabel`.
- `error_logger.log_error_message` records required-widget and handled
  diagnostic failures.

`FieldCoordinator` is intentionally not used because this dialog has no linked
text inputs, lookups, or field-validation sequence.

## Report Export

Every completed run attempts to create a UTF-8 text report under:

```text
~/POS_Exports/Diagnostic
```

Typical Windows location:

```text
C:\Users\<username>\POS_Exports\Diagnostic
```

Filename format:

```text
diagnostic_report_<dd><mon><yyyy>_<hh>-<mm>-<ss>.txt
```

Example:

```text
diagnostic_report_27jul2026_18-30-45.txt
```

If that filename already exists, `_2`, `_3`, and so on are appended instead of
overwriting an earlier report.

The report includes:

- Generation time and overall status
- Selected checks
- Database path, size, and read-only connection state
- Required-table presence
- Table counts
- Complete `quick_check` output
- Foreign-key violations
- Live product-cache totals and consistency count
- Missing, extra, invalid, and duplicate-normalized cache keys
- Per-field cache value mismatches
- Issues that caused a failed result

After a successful export, the StatusBar message is intentionally concise:

```text
Diagnostic report saved to <folder path>
```

When diagnostics find issues, the same concise path message uses error severity;
the issue details remain in the report. If export itself fails, the dialog is
rejected and the export error is reported without claiming that a report was
saved.

## Files

- `ui/menu_frame.ui`: Diagnostics main-menu button
- `assets/icons/diagnose.svg`: main-menu icon
- `ui/diagnostics_menu.ui`: modal selection dialog
- `modules/main_window/menu_controller.py`: icon presentation and click wiring
- `modules/menu/diagnostics_menu.py`: dialog controller and running state
- `modules/menu/diagnostics/common.py`: timestamps and read-only SQLite helpers
- `modules/menu/diagnostics/database_check.py`: database counts and integrity
- `modules/menu/diagnostics/product_cache_check.py`: live cache comparison
- `modules/menu/diagnostics/report_formatter.py`: selected-check text report
- `modules/menu/diagnostics/report_exporter.py`: export folder and file writing
- `modules/menu/diagnostics/__init__.py`: supported package-level imports
- `modules/menu/diagnostics_helper.py`: compatibility-only import facade
- `dev_tools/diagnostics/check_product_cache_consistency.py`: standalone cache comparison
- `assets/qss/dialog.qss`: Diagnostics dialog styling
- `tests/test_diagnostics_helper.py`: database, cache, and report tests
- `tests/test_diagnostics_menu.py`: selection, controller, and export-path tests

## Module Organization

Diagnostic implementations are separated by responsibility under
`modules/menu/diagnostics`. New checks should be added as focused modules in
that package instead of expanding `diagnostics_helper.py`.

`diagnostics_menu.py` imports the package's public entry points and remains
responsible only for checkbox selection, UI state, execution orchestration,
combined status, and export invocation.

`diagnostics_helper.py` is intentionally retained as a small compatibility
facade. Earlier imports continue to work, but it contains no diagnostic
implementation. Developer scripts should import the focused check module they
execute.

## Extension Rules

Future checks should:

- Remain read-only unless a separate repair action is explicitly designed
- Return structured results rather than preformatted UI strings
- Operate on the live session state when the check concerns cache or UI models
- Add their section to the same report without rerunning completed checks
- Preserve the selected-checkbox execution model
- Keep expensive comparisons out of the GUI event path when their runtime
  becomes noticeable
