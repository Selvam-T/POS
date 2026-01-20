# Standard Dialog Pipeline (Jan 2026)

This document defines a standardized pipeline that all dialogs can follow while still allowing per-dialog differences (e.g., different placeholders, `Qt.NoFocus` fields, optional/required inputs).

## Goals
- Consistent UI load + fallback behavior
- Consistent focus/Enter-key navigation behavior
- Consistent status/error feedback routing
- Keep error logging policy configurable without refactoring dialog logic

## Pipeline (Recommended)

### 0) Controller entry
Each dialog module exposes a single constructor function:
- `open_<name>_dialog(host_window, ...) -> QDialog | None`

The function should **construct and wire** the dialog and then return it.
The dialog wrapper is responsible for executing it.

### 1) Strict UI load (UI-load fallback boundary)
Use `modules/ui_utils/dialog_utils.py`:
- `load_ui_strict(ui_path, host_window=..., dialog_name=...)`

If it returns `None`, return `None` from the dialog constructor.

### 2) Wrap + standard window configuration
If the UI root is not a `QDialog`, wrap it in a `QDialog` container.
Set modality and frameless flags consistently.

Optional helper:
- `build_dialog_from_ui(ui_path, host_window=..., dialog_name=..., qss_path=...) -> QDialog | None`

### 3) Widget binding
Resolve widgets with `findChild(...)`.

Optional helper:
- `require_widgets(root, {key: (Class, objectName)}, hard_fail=True)`

### 4) Focus policy and per-field capabilities
Set per-field behavior (read-only fields, display-only mapping fields, and focus policy):
- display-only: `setReadOnly(True)` + `setFocusPolicy(Qt.NoFocus)`
- gated fields: start as `Qt.NoFocus` and unlock later

### 5) Coordinator wiring (keyboard + relationships)
Create and attach the coordinator:
- `coord = FieldCoordinator(dlg)`
- `dlg._coord = coord`

Declare navigation + mapping with `coord.add_link(...)`.

Optional behavior:
- `placeholder_mode='reactive'`
- `coord.register_validator(...)` to auto-clear last error state

### 6) OK/Cancel handlers
- OK: validate final clean values using `modules/ui_utils/input_handler.py` (which calls `input_validation.py`).
- On success: set dialog result payload and call `dlg.accept()`.
- Cancel: call `dlg.reject()`.

### 7) Post-close StatusBar message
Set `main_status_msg` using:
- `set_dialog_info(dlg, '...')` or `set_dialog_error(dlg, '...')`

### 8) Execution wrapper
`DialogWrapper` handles:
- overlay/scanner state
- geometry and centering
- focus restore
- reading `main_status_msg` after `exec_()` and showing it in the MainWindow status bar

## Hard-fail vs Soft-disable
- **Hard-fail**: return `None` (don’t show dialog) when the primary task is impossible (missing required widgets, corrupted UI).
- **Soft-disable**: keep dialog usable but disable a feature (missing optional widgets, DB label refresh failure, non-critical actions).

## Error policy (opt-in)
Use `modules/ui_utils/error_policy.py` to centralize “what to log vs what to show” without rewriting dialog wiring:
- `safe_call(where, fn, host_window=..., user_message=..., category=..., fallback=...)`
