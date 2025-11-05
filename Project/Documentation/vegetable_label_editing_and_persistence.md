# Vegetable Label Editing & Persistence

This document describes the Vegetable Menu dialog that lets users edit the 14 vegetable labels used by the Vegetable Entry screen, and how those labels are validated, saved, and applied across the app.

## Overview

- Dialog lets you configure up to 14 vegetable labels.
- Each row has: “Vegetable N:” label, a text input (15-char limit), a compact toggle (left/right), and a “NOT USED” indicator.
- Inline validation errors appear inside the dialog (no modal popups).
- On save, labels are validated, sorted A→Z, persisted to JSON, and broadcast to the app for live updates.

## Files and Modules

- UI: `ui/vegetable_menu.ui` — layout for the editor dialog (14 rows + inline message + custom title bar).
- Logic: `modules/menu/vegetable_menu.py` — controller for validation, styling state, load/save, and OK/Cancel handling.
- Styles: `assets/vegetable_menu.qss` — dialog-specific QSS for sliders, inputs, scrollbars, title bar, and inline messages.
- Config: `config.py` — will expose app data roots and constants (e.g., VEG_SLOTS=14) used by the settings wrapper. (Pending)
- Settings API: `modules/wrappers/settings.py` — wrapper for JSON persistence: `veg_slots()`, `load_vegetables()`, `save_vegetables()`. (Pending)
- Consumer: `ui/vegetable_entry.ui` + its controller — reads saved mapping to set button texts and disable “unused” slots. (Wiring pending)

## User Experience & Behavior

- Title: Single centered title in a custom frameless title bar.
- Rows:
  - Label text: “Vegetable N” (1..14)
  - Input: placeholder “Enter Vegetable,” max length 15, visually constrained width so it doesn’t crowd the toggle.
  - Toggle: compact slider (52×20). Left = editable/custom; Right = NOT USED.
  - NOT USED label: left-aligned to reduce excess gap.
- Scroll area: Sized to just cover content; scrolls only enough to reveal Vegetable 14 (no extra blank space).
- Inline message area: Appears above OK/Cancel. Used for errors/info/success; centered.

## Visual States (QSS)

- Slider states:
  - `slider[active="true"]` → green background (left/on).
  - `slider[active="false"]` → gray background (right/off).
- Input border:
  - No focus-based border changes.
  - `QLineEdit[active="true"]` gets a blue border only when its toggle is on the editable (left) side.
- Message label:
  - `messageLabel[kind="error"|"info"|"success"]` controls color.

These states are applied via dynamic properties set in `vegetable_menu.py`, then refreshed (unpolish/polish) to apply QSS immediately.

## Validation Rules

- Non-empty: If a row’s toggle is left (editable/custom), its text must not be empty.
  - Error copy: “Vegetable X cannot be empty.” (X = row number)
- No duplicates: Case-insensitive comparison; duplicates are rejected.
- Sorting: Collected labels are sorted A→Z (case-insensitive) and reassigned left-to-right into veg1..vegN; remaining slots become unused.
- Feedback: Errors show inline in the message area; invalid fields get focus.

## Data Model & Persistence

- Mapping shape (Python dict → JSON):
  ```json
  {
    "veg1": {"state": "custom", "label": "Tomato"},
    "veg2": {"state": "custom", "label": "Onion"},
    ...
    "veg14": {"state": "unused", "label": "unused"}
  }
  ```
- States: `custom` (active/left) or `unused` (inactive/right).
- Defaults: All entries default to `{"state": "unused", "label": "unused"}`.
- Location: Stored under the app’s data directory (exact path provided by `config.py` + settings wrapper). The wrapper will auto-create the JSON with defaults on first run. (Pending implementation)

## Settings Wrapper API (planned)

- `veg_slots() -> int`
  - Returns the configured number of vegetable slots (currently 14 via `config.py`).
- `load_vegetables() -> dict`
  - Reads JSON from the settings path; if missing/corrupt, returns default mapping and auto-writes a fresh file.
- `save_vegetables(mapping: dict) -> None`
  - Validates shape and persists to JSON atomically.
- Optional helpers:
  - `settings_dir() -> Path` and/or `vegetables_path() -> Path` to expose resolved paths.

## Wiring & Flow

- Opening the editor:
  - A main/menu action opens `VegetableMenuDialog`.
- On load:
  - Dialog uses the settings wrapper to read the current mapping and populate rows (left/right state + text).
- On OK:
  - Collects and validates active labels, sorts A→Z, constructs the mapping, saves via settings API.
  - Emits `configChanged(mapping)` then closes.
- Consumer (Vegetable Entry):
  - At startup: load mapping and set button texts/enable state.
  - Live update: listen to `VegetableMenuDialog.configChanged` to refresh buttons immediately without restarting.

## Edge Cases & Notes

- Empty-only rows: Allowed only if toggle is right (unused). Left (custom) requires text.
- Case-insensitive duplicates: "Tomato" and "tomato" are considered the same.
- Length limit: 15 characters; UI enforces this in the line edits.
- Robustness: If stylesheet fails to load, logic still works with default Qt styles.

## Testing & QA

- UI sanity check (recommended): Lightweight check that instantiates `VegetableMenuDialog` to catch `.ui` XML regressions early.
- Validation tests (recommended):
  - Happy path: distinct non-empty labels save successfully.
  - Empty error: toggled-left row with empty text shows inline error and focuses the field.
  - Duplicate error: two identical labels (case-insensitive) show inline error.
  - Sorting: Input labels save in sorted order and reassign to veg1..vegN.

## Status

- Completed:
  - Dialog UI with 14 rows, inline message area, centered custom title bar.
  - Controller logic: dynamic properties for state visuals, inline validation/messages, A→Z sorting, JSON save integration point, and `configChanged` emission.
  - QSS: compact green/gray toggles, input border tied to active state, centered message styles, cleaned chrome.
- Next:
  - Implement `modules/wrappers/settings.py` (load/save/slots + default handling under AppData).
  - Update `config.py` with VEG_SLOTS and data root paths used by the settings wrapper.
  - Wire main/menu to open the dialog (if not already) and refresh Vegetable Entry on accept.
  - In the Vegetable Entry controller, read mapping at startup and apply to buttons; disable/hide unused.
  - Add a simple UI load test for `ui/vegetable_menu.ui`.

## Quick Reference

- Editor class: `modules/menu/vegetable_menu.py: VegetableMenuDialog`
- Stylesheet: `assets/vegetable_menu.qss`
- UI file: `ui/vegetable_menu.ui`
- Settings wrapper (pending): `modules/wrappers/settings.py`
- Config constants (pending): `config.py`
# Vegetable Label Editing and Persistence

This document summarizes the agreed design for editable vegetable buttons, runtime behavior, persistence strategy, and file layout conventions.

## Scope and UX
- Vegetable Entry dialog shows buttons `veg1..vegN` (OK and CANCEL unchanged).
- A “Vegetable Menu” dialog lets the user edit button labels.
- Two per-slot options:
  - custom: user types a name (e.g., "Tomato").
  - unused: the button is labeled "unused", grayed, and not clickable.

## Validation and Sorting
- Validation (on save or per field):
  - Trim input.
  - Reject empty/whitespace labels.
  - Reject duplicates (case-insensitive).
  - Keep focus and show an error until the value is valid or the user cancels.
- Sorting and assignment:
  - Collect all valid custom labels; sort A→Z.
  - Fill slots left-to-right: `veg1, veg2, ...` with sorted labels.
  - Any remaining slots are set to `unused` (disabled/grayed).
  - Persist the post-sort assignment so it loads the same next time.

## Runtime Behavior
- On dialog show and on configChanged:
  - Apply labels to buttons.
  - If label == `unused`, disable the button (Qt default disabled state grays it out).
  - Optional: set a property (e.g., `unused=true`) to target styling in `assets/style.qss`.
- The editor dialog emits `configChanged(mapping)` after a successful save so the entry dialog updates immediately.

## Persistence Strategy
Two options were considered; we will use JSON now and keep QSettings as an alternative.

### Chosen: JSON (transparent and simple)
- Data file: `Project/AppData/vegetables.json` (mutable runtime data, not an asset).
- Example schema:
  ```json
  {
    "veg1": {"state": "custom", "label": "Tomato"},
    "veg2": {"state": "unused", "label": "unused"}
  }
  ```
- Notes:
  - Create `Project/AppData/` on first run if missing.
  - Consider `.gitignore` for `Project/AppData/*.json`.
  - If more menus need mappings later, store them in the same folder (e.g., `Project/AppData/<menu>.json`).

### Alternative: QSettings (via PyQt5)
- Available through `from PyQt5.QtCore import QSettings`.
- Storage modes:
  - native (Windows Registry) — no file to manage.
  - ini (text file) — portable and human-readable.
- If adopting later, only the settings wrapper changes; controllers remain unchanged.

## File and Module Layout
- UI files:
  - `ui/vegetable_entry.ui` — displays buttons `veg1..vegN`.
  - `ui/vegetable_menu.ui` — editor dialog for labels (to be provided).
- Controllers:
  - `modules/menu/vegetable_entry.py` — applies labels and enabled state; no persistence.
  - `modules/menu/vegetable_menu.py` — validates input, sorts, saves, emits `configChanged`.
- Settings API (generic wrapper):
  - `modules/wrappers/settings.py` (preferred lowercase path; alternatively `modules/config/settings.py`).
  - Responsibilities:
    - `load_mapping(name: str) -> dict` (returns defaults if file missing)
    - `save_mapping(name: str, data: dict) -> None` (atomic write)
    - `exists(name: str) -> bool`
    - `appdata_path(name: str) -> Path` (e.g., `Project/AppData/<name>.json`)
  - The Vegetable feature will use `name = "vegetables"`.

## Config Constants (`config.py`)
Do not store labels here; store only durable constants used by the settings wrapper and controllers.
- `VEG_SLOTS = <N>` — number of vegetable buttons.
- `APPDATA_DIR = os.path.join(<Project>, 'AppData')` — base directory for JSON files.
- (Optional, future) QSettings identifiers:
  - `ORG_NAME = 'Anumani'`
  - `APP_NAME = 'POS'`
  - `SETTINGS_STORAGE = 'json'`  # or 'qsettings' if switching later
  - If QSettings INI is desired later: `SETTINGS_FILE = os.path.join(APPDATA_DIR, 'app.ini')`

## Data Flow Summary
1. Vegetable Entry opens → settings loads mapping → apply labels and disable `unused`.
2. User opens Vegetable Menu → settings loads mapping → prefill controls.
3. User edits → validate → collect customs → sort A→Z → assign to `veg1..vegN` → rest `unused`.
4. Save → settings writes JSON → emit `configChanged(mapping)`.
5. Entry dialog listens → reapply immediately.

## Naming and Object Names
- Buttons should have stable `objectName`s like `btnVeg1 .. btnVegN`.
- Visible text is independent and set from the mapping.

## Styling (optional)
- Default disabled state grays out `unused` buttons.
- For custom themes, set a dynamic property and add QSS rules in `assets/style.qss`.

## Next Steps
- Provide `ui/vegetable_menu.ui`.
- Implement `modules/wrappers/settings.py` (JSON backend; atomic writes; defaults).
- Wire `modules/menu/vegetable_menu.py` and `modules/menu/vegetable_entry.py` to the settings API.
- Add `APPDATA_DIR` and `VEG_SLOTS` to `config.py`.
