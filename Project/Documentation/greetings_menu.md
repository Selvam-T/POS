# Greeting Menu

## Purpose
- Provides a quick way for the cashier to pick a holiday or event greeting that the rest of the POS UI can show (e.g. status bar, printed receipts).
- Runs as a modal dialog from the right-hand menu (the `Greeting` button in `menu_frame.ui`).

## Runtime flow
1. `MainLoader.open_greeting_menu_dialog()` triggers the dialog through `DialogWrapper.open_dialog_scanner_blocked()` so scanner input is blocked while the customer-facing selection is happening.
2. `modules/menu/greeting_menu.py` loads `greeting_menu.ui`, populates the combo box from `config.GREETING_STRINGS`, and initializes the default selection from `config.GREETING_SELECTED`.
3. When the dialog closes with `OK`, it stores the chosen greeting in `dlg.greeting_result` and the `MainLoader` `on_finish` handler reads that value.
4. The handler assigns the selection to `config.GREETING_SELECTED` (so successive dialogs and other widgets read the new message) and delegates to `modules/ui_utils/greeting_state.py` to persist it.

## Persistence detail
- `modules/ui_utils/greeting_state.py` serializes `{ "selected": "Your Message" }` into `AppData/greeting.json` (relative to `config.APPDATA_DIR`, via `modules.wrappers.settings.appdata_path`).
- On startup `main.py` loads the JSON and overwrites `config.GREETING_SELECTED` so the saved greeting survives restarts without modifying source files.

### Why AppData instead of editing config.py
- `config.py` is treated as part of the source code, so writing back to it at runtime would require touching tracked files, break in packaged builds, and make upgrades/rollbacks harder.
- Storing the latest greeting in AppData keeps user selections local to the install, writable, and isolated from the code. Keeping `config.GREETING_SELECTED` as a default ensures there is still a safe fallback value when no AppData file exists.

## Customization notes
- Add/remove strings via `config.GREETING_STRINGS` and adjust the default in `config.GREETING_SELECTED`.
- The stored greeting is local to the machine; copying `AppData/greeting.json` between installs preserves the last choice.
