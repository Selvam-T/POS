# Vegetable Entry Dialog and Selection Workflow

This document describes the workflow for the Vegetable Entry dialog, where users select a vegetable, place it on the scale, and input its weight. It also covers how button names are updated from the Vegetable Menu editor, and how selection, weighing, and entry are handled in the POS system.

## Key Components

- **UI File:** `ui/vegetable_entry.ui` — layout for the entry dialog (table, keypad buttons, message label).
- **Logic:** `modules/sales/vegetable_entry.py` — controller for dialog, table setup, button selection, and scale input.
- **Settings:** `modules/wrappers/settings.py` — manages vegetable label configuration and persistence (used by the Vegetable Menu editor).

## Table Setup and Header Configuration

- The table widget in the UI file must have the objectName set to `vegEntryTable`.
- The dialog controller locates the table using `content.findChild(QTableWidget, 'vegEntryTable')`.
- The table is configured with 5 columns and custom header labels: `['No.', 'Item', 'Weight (KG)', 'Total', 'Del']`.
- Column widths and resize modes are set programmatically for consistent appearance.

## QSS Styling

- Dialog-specific styles are loaded from `assets/sales.qss` and applied to the dialog.
- Styles for buttons, labels, and table headers are modularized for maintainability.

## Debugging and Verification

- Debug print statements were previously used to verify table discovery and header setup, but have now been removed for production use.
- If the table is not found, ensure the objectName in the `.ui` file matches `vegEntryTable`.

## Button Label Mapping and Selection

- The controller maps vegetable labels from settings to keypad buttons (`btnVeg1` to `btnVeg14`).
- When a button is pressed, the corresponding vegetable is selected for weighing.
- Disabled buttons display 'Not Used'; enabled buttons show the custom label.
- Button states and labels are updated dynamically based on settings.

## Persistence

- Changes to vegetable labels are saved via the settings module and reflected in the dialog on next open.

## Recent Changes (Dec 2025)

- Table widget objectName updated to `vegEntryTable` for consistency.
- Debug print statements for table discovery and header setup removed.
- Documentation and code updated to reflect new table name and logic.

## Quick Reference

- Entry dialog: `modules/sales/vegetable_entry.py: open_vegetable_entry_dialog`
- Stylesheet: `assets/sales.qss`
- UI file: `ui/vegetable_entry.ui`
