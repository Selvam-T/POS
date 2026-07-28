# Diagnostics Menu

Updated: July 28, 2026

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
5. Product search lists and vegetable slots
6. Category integrity
7. Runtime assets and paths

The Database, Product Cache, Suspicious Product Code, Duplicate Product Name,
and Product Search Lists and Vegetable Slots checks are enabled. The remaining
two checks are visible, disabled, and marked `Coming soon`.

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

## Suspicious or Incomplete Product Codes

This diagnostic reads product codes and names from `Product_list` using the
same separate read-only connection. It identifies review candidates without
declaring that either product is automatically wrong.

The check targets numeric barcode-like codes of at least five characters.
Codes shorter than five characters are treated as intentional keyboard
shortcuts and ignored. Automated vegetable codes matching `VEG01` or
`VEG-01` through `VEG99` are also explicitly ignored. Other alphanumeric
internal codes are ignored because they are not scanner barcodes.

Candidate matching models premature scanner termination only. A candidate
exists when a shorter database code is an exact prefix of another database
code:

- One missing tail character is reported as high confidence.
- Two or three missing tail characters are reported as lower confidence.
- More than three missing tail characters are not compared.

Middle-character deletion, single-character substitution, and adjacent
character transposition are intentionally not checked. Those errors are
plausible during manual typing but do not represent the barcode-scanner failure
observed in this POS.

Same-length 80 percent similarity is also intentionally excluded. Retail
barcodes from the same manufacturer or product family commonly share most of
their digits, while later digits distinguish legitimate variants, package
sizes, or individual products. For example, two valid products can be more
than 90 percent similar without either code being incorrect. A generic
similarity threshold therefore creates many false positives; exact tail-prefix
matching is materially stronger evidence of an incomplete scan.

The result is `PASS` when no candidates are found, `WARNING` when review
candidates or normalized duplicate codes are found, and `FAIL` only when the
check cannot complete. A warning does not modify, merge, or delete products.
The report lists the number of missing tail characters, confidence, prefix
coverage, both codes, and both product names for manual review.

Review candidates are written only to the diagnostic report and are not added
to `error_log`. Actual failures, such as an unreadable database or failed
report export, continue to use the application error logger.

The product-code section separates configuration from results:

```text
CHECK SETTINGS
- Minimum barcode length checked: 5 characters
- Tail truncation range checked: 1 to 3 missing characters
- Matching rule: shorter code must exactly match the start of a longer code

SCAN SUMMARY
- Product codes read from database: <count>
- Numeric barcode codes checked: <count>
- Codes excluded from comparison: <count>
  - Short keyboard shortcut codes: <count>
  - Automated vegetable codes: <count>
  - Other nonnumeric/internal codes: <count>

FINDINGS
- Suspicious product codes: <unique-code count>
- Suspicious tail-truncation pairs found: <count>
  - High-confidence pairs: <count>
  - Lower-confidence pairs: <count>

REVIEW CANDIDATES
- None
```

`CHECK SETTINGS` describes what the diagnostic was configured to search for;
it does not describe a finding. `SCAN SUMMARY` records the examined and
excluded populations. Only `FINDINGS` counts suspected pairs, and only actual
findings produce product details under `REVIEW CANDIDATES`.

`Suspicious product codes` counts unique individual product codes involved in
the findings. `Suspicious tail-truncation pairs found` counts relationships
between a shorter and longer code. One product code can participate in more
than one pair, so the two totals do not necessarily match.

## Duplicate Product Names

This diagnostic reads product codes and names from `Product_list` using a
separate read-only connection. It groups names only after limited,
deterministic normalization:

- Leading and trailing whitespace is removed.
- Repeated whitespace, including spaces and tabs, is collapsed to one space.
- Letter case is ignored.
- Punctuation is preserved.

For example, these names are reported as one duplicate group:

```text
Fresh  Milk
fresh milk
```

These names are not grouped:

```text
Fresh-Milk
Fresh Milk
Fresh Mil
```

The first two differ by punctuation, and the third is merely similar. The
diagnostic intentionally performs no punctuation removal, spelling correction,
edit-distance calculation, or other near-duplicate matching.

The result is `PASS` when no duplicate groups exist, `WARNING` when one or more
groups require review, and `FAIL` only when the check cannot complete. Empty
names are counted as skipped rather than treated as duplicates; missing-name
validation belongs to the separate Product Data Quality check.

The report records the duplicate group count, total products participating in
duplicate groups, the normalized comparison name, and every product code and
stored name in each group. Findings are report-only and do not modify products
or write warning findings to `error_log`.

## Product Search Lists and Vegetable Slots

Manual entry, Refund, Receipt, and Product Menu previously constructed their
product-name suggestions with separate list-building code. They now call the
shared:

```text
modules.ui_utils.product_choices.build_product_name_choices(PRODUCT_CACHE)
```

The builder returns one choice for every nonempty cache record. It trims only
surrounding whitespace, preserves internal whitespace, casing, punctuation,
and duplicate entries, then sorts the complete list case-insensitively by
product name. It does not rely on cache insertion or product-code order.

The refactor changes only the construction of displayed choices. It does not
change the existing shared input-handler or Product Menu name-lookup rules.
When duplicate names exist, the current first matching `PRODUCT_CACHE` record
is used. This temporary ambiguity remains visible rather than being concealed
by the builder; the Duplicate Product Names diagnostic and database-level
duplicate prevention address the underlying condition.

This diagnostic operates on the exact live `PRODUCT_CACHE` object. It does not
reload the cache or repeat the database-versus-cache comparison performed by
the Product Cache diagnostic. It verifies:

- The shared choice output contains one entry for every usable cache name,
  including duplicates.
- The choice output has no missing or extra entries.
- The choice output is sorted.
- Empty product names and malformed cache records are reported.
- Fixed slot identifiers range from `VEG01` through `VEG16`; unpopulated slots
  are counted informationally and are not issues.
- Reserved-looking `VEGxx` or `VEG-xx` codes outside that range are reported.
- Each populated fixed slot has a usable name, positive selling price, unit,
  and `Vegetable` category value.

Products in the Vegetable category with ordinary scanned barcodes are
legitimate and are ignored by the fixed-slot check. The diagnostic examines
only reserved-looking `VEG` codes.

The report explicitly records this limitation:

> The check validates the shared cache-derived data pipeline. It does not
> inspect unopened dialog widgets or confirm that an already-open widget model
> refreshed after a product change.

Dialogs construct their completer/model when opened. Product Menu also rebuilds
its Remove and Update completers after its successful Add, Remove, and Update
refresh pipeline. Runtime widget synchronization remains an integration-test
responsibility rather than a claim made by this read-only operator diagnostic.

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
- Tail-truncated product-code candidates and confidence
- Duplicate product-name groups with product codes and stored names
- Shared product-name choice and fixed vegetable-slot findings
- Issues that caused a failed result

After a successful export, the StatusBar message is intentionally concise:

```text
Diagnostic report saved to <folder path>
```

When diagnostics find review candidates, the same concise path message uses
warning severity. Error severity is reserved for a check or export that fails
to complete. The issue details remain in the report. If export itself fails,
the dialog is rejected and the export error is reported without claiming that
a report was saved.

## Files

- `ui/menu_frame.ui`: Diagnostics main-menu button
- `assets/icons/diagnose.svg`: main-menu icon
- `ui/diagnostics_menu.ui`: modal selection dialog
- `modules/main_window/menu_controller.py`: icon presentation and click wiring
- `modules/menu/diagnostics_menu.py`: dialog controller and running state
- `modules/menu/diagnostics/common.py`: timestamps and read-only SQLite helpers
- `modules/menu/diagnostics/database_check.py`: database counts and integrity
- `modules/menu/diagnostics/product_cache_check.py`: live cache comparison
- `modules/menu/diagnostics/product_code_check.py`: suspicious code matching
- `modules/menu/diagnostics/product_name_check.py`: duplicate-name grouping
- `modules/menu/diagnostics/product_derived_ui_check.py`: shared choices and fixed slots
- `modules/ui_utils/product_choices.py`: canonical product-name choice builder
- `modules/menu/diagnostics/report_formatter.py`: selected-check text report
- `modules/menu/diagnostics/report_exporter.py`: export folder and file writing
- `modules/menu/diagnostics/__init__.py`: supported package-level imports
- `modules/menu/diagnostics_helper.py`: compatibility-only import facade
- `dev_tools/diagnostics/check_product_cache_consistency.py`: standalone cache comparison
- `assets/qss/dialog.qss`: Diagnostics dialog styling
- `tests/test_diagnostics_helper.py`: database, cache, and report tests
- `tests/test_diagnostics_menu.py`: selection, controller, and export-path tests
- `tests/test_product_code_diagnostics.py`: code matching and reporting tests
- `tests/test_product_name_diagnostics.py`: name normalization and report tests
- `tests/test_product_derived_ui_diagnostics.py`: shared choices and slot tests

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
