## Dialog Size Ratios
- `DIALOG_RATIOS`: Dictionary mapping dialog names to (width_ratio, height_ratio) tuples, as a fraction of the main window size. Used to ensure consistent dialog sizing across the application. Example:

	'vegetable_entry': (0.5, 0.9)
	'manual_entry': (0.4, 0.3)
	...

Import from config.py wherever dialog sizing is needed.

- Product Menu uses only `DIALOG_RATIOS['product_menu']`, currently
  `(0.45, 0.90)`. The shared dialog wrapper applies this ratio once; switching
  among ADD, REMOVE, UPDATE / VIEW, and CATEGORY does not change the dialog
  size. There is no Product Menu per-tab ratio configuration.

## Shared Report Viewer Size Ratio
- `REPORT_VIEWER_RATIOS`: Shared `(width_ratio, height_ratio)` tuple used by
	the report viewer shell for `detail`, `summary`, `chart`, and `inactivity`
	reports.
- Current default: `(0.6, 0.85)`.
- The report viewer applies this one shared size policy for all report types,
	with a pixel fallback if the tuple is missing or invalid.
# config.py — POS System Configuration

This file centralizes key configuration values for the POS application. It is imported by multiple modules to ensure consistent settings across the project.

## Contents
- Table row colors
- Icon paths
- Date/time formats
- Company name
- Database path
- Debug flags
- App data directory
- Feature constants
- Greeting message options
# Greeting Message Options
- `GREETING_STRINGS`: List of preset greeting messages for the greeting dialog. Import from config.py wherever needed.

---

## Table Row Colors
- `ROW_COLOR_EVEN`: Color for even-numbered sales table rows.
- `ROW_COLOR_ODD`: Color for odd-numbered sales table rows.
- `ROW_COLOR_DELETE_HIGHLIGHT`: Highlight color for row deletion preview.

## Icon Paths
- `ICON_DELETE`, `ICON_ADMIN`, `ICON_REPORTS`, `ICON_VEGETABLE`, `ICON_PRODUCT`, `ICON_GREETING`, `ICON_RECEIPT`, `ICON_LOGOUT`: Relative paths to SVG icon files used in the UI.

## Date/Time Formats
- `DATE_FMT`: Format for displaying dates (e.g., `3 Nov 2025`).
- `DAY_FMT`: Format for displaying day names (e.g., `Fri`).
- `TIME_FMT`: Format for displaying times (e.g., `12:22 am`).

## Company Name
- `COMPANY_NAME`: The company name shown in the application header.

## Database Path
- `DB_PATH`: Absolute path to the SQLite database. Computed relative to the project root so it works on any machine.

## Development / Production Switchboard
These flags are grouped together in `config.py` so development and production behavior can be reviewed from one place.

- Login and access:
  - `LOGIN_ON`: `False` bypasses login for development; production should normally require login.
  - `AUTO_LOGIN_UID`, `AUTO_LOGIN_USERNAME`, `AUTO_LOGIN_IS_ADMIN`: User identity injected only when `LOGIN_ON` is `False`.
- Trial build gate:
  - `TRIAL_BUILD_ENABLED`: Enables trial expiry enforcement for trial executables.
- Vegetable scale fallback:
  - `VEG_KG_MANUAL_GRAMS_FALLBACK`: Enables manual whole-gram entry for KG vegetables when scale hardware is unavailable.
- Printer and cash drawer:
  - `ENABLE_PRINTER_PRINT`: Enables network printer output.
  - `ENABLE_CASH_DRAWER`: Enables cash drawer pulse after successful cash payment.
- Customer display launch mode:
  - `CUSTOMER_DISPLAY_ENABLED`: Creates or skips the customer-facing display.
  - `CUSTOMER_DISPLAY_TEST_MODE`: Opens the customer display as a normal test window.
  - `CUSTOMER_DISPLAY_FULLSCREEN`: Uses fullscreen customer display.
  - `CUSTOMER_DISPLAY_AUTO_DETECT`: Enables target-screen auto-detection when test mode is off.
- Customer display QR rendering:
  - `CUSTOMER_DISPLAY_USE_STATIC_QR_IMAGE`: Uses a QR image from `assets/images` when enabled; otherwise uses generated PayNow QR rendering.
  - `CUSTOMER_DISPLAY_QR_IMAGE_FILENAME`: Static QR image file name, for example `eposQR.png`. If the file is missing or invalid, the app logs the issue and falls back to generated QR rendering.

## Scanner Timing
- `SCANNER_KEY_INTERVAL_SECONDS`: Short scanner-fast gap threshold; it does not reset the retained candidate.
- `SCANNER_CANDIDATE_INACTIVITY_SECONDS`: Longer idle boundary that abandons an unfinished candidate.
- `SCANNER_MAX_AVERAGE_GAP_SECONDS`: Maximum average character gap for scanner-like classification.
- `SCANNER_MIN_FAST_GAP_RATIO`: Minimum scanner-fast gap proportion for short/custom codes.
- `SCANNER_LONG_CODE_MIN_LENGTH`: Length from which a scanner-like average can classify a long code despite individual delayed gaps.
- `SCANNER_UI_SETTLE_MS`: Delay before field restoration or product-code finalization, allowing queued Qt key events to drain.
- `BARCODE_SCANNER_TRACE_ENABLED`, `BARCODE_SCANNER_TRACE_PATH`, rotation limits,
  and `BARCODE_SCANNER_HEALTH_INTERVAL_MS`: temporary production tracing for the
  intermittent lost-scan investigation. The trace is independent of `error.log`
  and the Diagnostics menu; see `barcode_scanner_trace.md`.
- `LOGS_DIR`: Shared live runtime log directory, resolved as
  `<client root>/live_logs`. This is distinct from the user-triggered export
  destination under `~/POS_Exports/Error_Log`.
- `SCANNER_UI_SUPPRESS_SECONDS`: Enter/Return suppression window used by `BarcodeManager` after scanner-fast activity.

## Trial Build Flags
- `TRIAL_BUILD_ENABLED`: Enables trial expiry enforcement.
- `TRIAL_EXPIRY_DATE`: Last UTC date on which login is allowed.
- `TRIAL_EXPIRED_MESSAGE`: Message shown when a trial build is expired or clock rollback is detected.

See `Documentation/trial_build.md`.

## App Data Directory
- `APPDATA_DIR`: External `<CLIENT ROOT>/data/json` folder for writable JSON-based settings (for example, `vegetables.json`).
- `ADS_DIR`: External `<CLIENT ROOT>/data/ads` folder for editable customer-display ads.
- `QSS_DIR`: Runtime `<APP RESOURCES>/assets/qss` folder containing application stylesheets.

## Category Storage

Category master data is stored in SQLite `Category`. Category names, protected
status, and ordering are database data rather than configuration constants.
`--Select Category--` is created by the UI only and is never stored.

## Feature Constants
- `VEG_SLOTS`: Number of vegetable buttons/slots in the vegetable entry UI (default: 16).
- `VEG_KG_MANUAL_GRAMS_FALLBACK`: Temporary vegetable-entry fallback for sites without production-ready weighing scale hardware.
  - Set to `False` when the weighing scale path is available. KG vegetable rows use the scale value, show a read-only quantity, and cannot be manually edited.
  - Set to `True` only when operating without a ready scale. KG vegetable rows start with an empty focused quantity cell, accept whole grams only (for example `1500` for 1.5 kg), and are converted back to kilograms internally for totals, merge, receipts, and reports.
  - EACH vegetable rows are not changed by this flag; they remain editable integer quantities.

---

**Edit this file to change global settings, colors, or paths.**

*Last updated: January 10, 2026*
