# TODO Dialog

Summary
- Purpose: Small in-app "Todo List" modal for operator notes and quick tasks.
- UI: `ui/todo.ui`
- Launcher: `modules/payment/todo.py::launch_todo_dialog`
- Invoked from: `modules/payment/payment_panel.py::_open_todo_dialog` via the app's `DialogWrapper`.

Behavior
- The dialog is built frameless so the UI's `customTitleBar` replaces the default titlebar.
- The application uses `DialogWrapper.open_dialog_scanner_blocked(...)` to show the dialog; this displays the overlay and blocks barcode scanner input while the modal is open.
- The dialog installs `dlg.barcode_override_handler` which the wrapper honors to prevent scanner text leakage into the main window.
- Styling: `assets/dialog.qss` is applied to the dialog (consistent custom titlebar styles).

Files modified/added
- `modules/payment/todo.py` — new launcher that returns the `QDialog` built from `ui/todo.ui` and sets `barcode_override_handler`.
- `modules/payment/payment_panel.py` — now calls the dialog wrapper to open the TODO dialog.
- `config.py` — added `DIALOG_RATIOS['todo']` for consistent sizing.
- `Documentation/todo.md` — this document (to be expanded).

Next steps
- Implement a persistent backend or controller for saving todos (e.g., small JSON store under `AppData/`).
- Add tests for dialog sizing and scanner blocking behavior.
- Extend UI interactions (Add/Undo/Clear actions) and wire them to a controller.
