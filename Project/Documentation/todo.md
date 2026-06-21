# TODO Dialog

Summary
- Purpose: Small in-app todo modal for operator notes and quick tasks.
- UI: `ui/todo.ui`
- Launcher: `modules/payment/todo.py::launch_todo_dialog`
- Invoked from: `modules/payment/payment_panel.py::_open_todo_dialog` via the app's `DialogWrapper`.

Behavior
- Built frameless so the UI's `customTitleBar` replaces the default title bar.
- `DialogWrapper.open_dialog_scanner_blocked(...)` shows the dialog and blocks scanner input while the modal is open.
- Styling: `assets/qss/dialog.qss` is applied, including TODO input-frame and row styles.
- The table shows 3 columns (index, text, delete), hides unused rows, and uses compact rows.
- Add: validates and canonicalizes input, appends the accepted text, saves JSON, clears input, and refocuses.
- Delete: removes the row, compacts the list, and saves JSON.
- Close: posts "todo item added" if any item was added, otherwise "todo dialog closed".
- Validation: `input_handler.handle_todo_input` + `input_validation.validate_todo_item(s)`.
- Limits: `config.TODO_ROWS` controls max rows; `config.TODO_ITEM_MAX_LEN` is currently 40 characters.
- Long input: pressing Enter validates without changing `todoInputLineEdit`; clicking ADD saves the truncated text and shows a timed warning with the allowed size.
- Persistence: `modules/ui_utils/todo_state.py` stores JSON under external `data/json/` using atomic writes.

Files modified/added
- `modules/payment/todo.py`: dialog controller, add/delete wiring, table rendering, status messaging.
- `modules/ui_utils/todo_state.py`: JSON load/save with validation.
- `modules/ui_utils/input_validation.py`: todo validation helpers.
- `modules/ui_utils/input_handler.py`: todo input canonicalization and truncation warning flag.
- `modules/payment/payment_panel.py`: opens the TODO dialog via the wrapper.
- `ui/todo.ui`: dialog layout.
- `assets/qss/dialog.qss`: TODO input-frame styling and compact row/delete-button styling.
- `assets/icons/delete_todo.svg`: TODO-specific delete icon with tighter viewBox usage.
- `config.py`: `TODO_ROWS` and `TODO_ITEM_MAX_LEN`.
- `Documentation/todo.md`: this document.

Next steps
- Add tests for `todo_state` validation and dialog add/delete behavior.
- Consider a "clear all" action if operators request it.
