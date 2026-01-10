## Dialog Size Ratios
- `DIALOG_RATIOS`: Dictionary mapping dialog names to (width_ratio, height_ratio) tuples, as a fraction of the main window size. Used to ensure consistent dialog sizing across the application. Example:

	'vegetable_entry': (0.5, 0.9)
	'manual_entry': (0.4, 0.3)
	...

Import from config.py wherever dialog sizing is needed.
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
- `ICON_DELETE`, `ICON_ADMIN`, `ICON_REPORTS`, `ICON_VEGETABLE`, `ICON_PRODUCT`, `ICON_GREETING`, `ICON_HISTORY`, `ICON_LOGOUT`: Relative paths to SVG icon files used in the UI.

## Date/Time Formats
- `DATE_FMT`: Format for displaying dates (e.g., `3 Nov 2025`).
- `DAY_FMT`: Format for displaying day names (e.g., `Fri`).
- `TIME_FMT`: Format for displaying times (e.g., `12:22 am`).

## Company Name
- `COMPANY_NAME`: The company name shown in the application header.

## Database Path
- `DB_PATH`: Absolute path to the SQLite database. Computed relative to the project root so it works on any machine.

## Debug Flags
- `DEBUG_SCANNER_FOCUS`: Print scanner focus widget for debugging.
- `DEBUG_FOCUS_CHANGES`: Log every Qt focus change (very verbose).
- `DEBUG_CACHE_LOOKUP`: Log cache lookup result for every scanned code.

## App Data Directory
- `APPDATA_DIR`: Path to the writable folder for JSON-based settings (e.g., `vegetables.json`).

## Feature Constants
- `VEG_SLOTS`: Number of vegetable buttons/slots in the vegetable entry UI (default: 16).

---

**Edit this file to change global settings, colors, or paths.**

*Last updated: January 10, 2026*
