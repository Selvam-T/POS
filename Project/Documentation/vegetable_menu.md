# Vegetable Menu Dialog Documentation

## Overview
The `VegetableMenuDialog` is a PyQt5 dialog for editing up to 16 vegetable labels, each with a toggle slider and a "NOT USED" indicator. It is designed for complex, stateful UI management, unlike simpler modal dialogs in the project.

## Features
- **Dynamic Rows:** Supports a configurable number of rows (default 16, set via `VEG_SLOTS` in `config.py`). Each row consists of:
  - A `QLineEdit` for entering a vegetable name
  - A `QSlider` acting as a toggle (active/inactive)
  - A `QLabel` showing "NOT USED" when the row is inactive
- **State Management:** Tracks the state of each row (used/unused) and updates widget properties and styles accordingly.
- **Styling:** Uses Qt Style Sheets (`menu.qss`) for consistent appearance. Dynamic properties (`active`, `rightIndicator`) are set in code to trigger QSS effects (e.g., gray background, bold text).
- **Signals:** Emits a `configChanged` signal when the configuration is updated, allowing other parts of the app to react.
- **Validation:** Ensures that custom vegetable labels are not empty before saving.
- **Persistence:** Loads and saves vegetable label mappings using functions from `modules/wrappers/settings.py`.

## UI Behavior
- **Toggle Slider:**
  - Left (active): Input field is editable, label is normal.
  - Right (inactive): Input field is read-only and gray, label is bold and gray.
- **Dynamic Styling:**
  - The dialog sets widget properties (`active`, `rightIndicator`) to control QSS styling.
  - The number of rows is determined by `VEG_SLOTS` in `config.py`. If set incorrectly, some rows may not be initialized or styled.

## Key Implementation Points
- The dialog is loaded from `vegetable_menu.ui`.
- All widgets are found and stored in `_rows` for easy access and state updates.
- The dialog applies the style sheet programmatically after loading the UI.
- The toggle logic and property setting are handled in `_on_toggle_changed` and `_load_and_populate`.
- Comments in the code have been simplified for clarity.

## Example Usage
- Open the dialog to edit vegetable labels.
- Use the toggle to mark a label as used or not used.
- Save changes to update the configuration and emit the signal.

## Notes
- If you add more rows to the UI, update `VEG_SLOTS` in `config.py` to match.
- The dialog is designed for maintainability and clarity, encapsulating all related logic.

---

### Simplified Comments for `vegetable_menu.py`
- Class manages vegetable label editing dialog.
- Initializes UI and finds all widgets.
- Handles toggle changes and updates widget states.
- Loads and applies style sheet.
- Validates and saves configuration.
- Emits signal on config change.
