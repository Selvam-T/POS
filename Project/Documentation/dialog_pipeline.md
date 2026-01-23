# Standard Dialog Pipeline (Jan 2026)

This document defines a standardized pipeline that all dialogs can follow while still allowing per-dialog differences (e.g., different placeholders, `Qt.NoFocus` fields, optional/required inputs).

## Goals
- Consistent UI load + fallback behavior
- Consistent focus/Enter-key navigation behavior
- Consistent status/error feedback routing
- Keep error logging policy configurable without refactoring dialog logic

Additional UX policy:
- Avoid showing StatusBar messages while a modal dialog is still open (prefer post-close intent)

## Pipeline (Recommended)

### 0) Controller entry (single public constructor)
Each dialog module exposes a single constructor function, used by `MainLoader` via `DialogWrapper`:
- `open_<name>_dialog(host_window, ...) -> QDialog | None`

Guards (preconditions) happen here:
- Examples: table row-limit reached, missing required runtime context, transaction-in-progress policies.
- If a guard fails, either:
	- return `None` (and optionally queue a StatusBar intent/message), or
	- show a small dedicated guard dialog (e.g., “max rows reached”) and then return `None`.

Controller responsibilities:
- Construct and wire the dialog (UI load, widget binding, event connections, validation/handlers).
- Set dialog-local feedback (status labels) during runtime.
- Set **post-close StatusBar intent** on the dialog when appropriate.
- For handled operational failures (soft-fail) that should be supportable/debuggable, write to `log/error.log` *from the controller* using shared helpers while also setting post-close StatusBar intent:
	- DB CRUD returns `(ok=False, msg)` → `log_and_set_post_close(...)` (+ dialog status label)
	- caught exceptions during refresh/lookup → `report_exception_post_close(...)`

Wrapper responsibilities:
- Execute modal lifecycle (overlay/scanner block, geometry, focus restore).
- Display post-close StatusBar messages.
- Catch unexpected exceptions that escape the controller boundary (hard-fail runtime).

### 1) Safe UI load (fallback boundary #1)
Use `modules/ui_utils/dialog_utils.py`:
- `load_ui_strict(ui_path, host_window=..., dialog_name=...) -> QWidget | None`
- or `build_dialog_from_ui(...) -> QDialog | None` (recommended)

Contract:
- UI missing / UI load failure → `None` is returned.
- The controller should return `None` (hard-disable open) unless it intentionally provides a programmatic fallback dialog.

User notification (standard):
- UI failures are logged to `log/error.log`.
- A StatusBar error is queued and then displayed by `DialogWrapper` *after overlay cleanup*.

### 2) Wrap + standard dialog frame
If the UI root is not a `QDialog`, wrap it in a `QDialog` container.
Set modality and frameless flags consistently.

Optional helper:
- `build_dialog_from_ui(ui_path, host_window=..., dialog_name=..., qss_path=...) -> QDialog | None`

### 3) Widget binding (fallback boundary #2)
Bind widgets once, early, and fail fast for required widgets.

Recommended:
- `widgets = require_widgets(dlg, {...}, hard_fail=True)`

Hard-fail guidance:
- Missing required widget objectName/type mismatch is a **programmer/config error**.
- Let `require_widgets(..., hard_fail=True)` raise `ValueError` and allow it to escape to the wrapper.

### 4) Focus policy + “field capability config”
Configure each field’s capabilities and user affordances.

Common patterns:
- Display-only: `setReadOnly(True)` + `setFocusPolicy(Qt.NoFocus)`
- Action buttons: disable QDialog auto-default behavior (avoid unintended accept)
- Comboboxes: optionally disable wheel/mouse focus if required for scanner/keyboard-first flows

If the dialog uses **gating** (unlocking fields only when an upstream field is valid):
- Start gated fields as locked/disabled (and often `Qt.NoFocus`).
- When relocking, clear dependent fields (prevents stale invalid state).

### 5) Gating + field relationships
Use shared utilities so dialogs behave consistently:

- **Exclusive input relationships** (only one of a set active at a time):
	- `enforce_exclusive_lineedits([...])`
- **Gating** (unlock next field only when current field is valid):
	- `FocusGate` and/or controller-level “gate update” functions
	- Must clear gated fields when relocking

Placeholder policy:
- Prefer `.ui` default + placeholder text authored in Qt Designer.
- If you need reactive placeholder changes (e.g., unit hints), do it through a shared pattern (FieldCoordinator placeholder mode or targeted UI code) and keep it consistent.

### 6) Coordinator wiring (standard interaction engine)
Use `FieldCoordinator` (and related focus utils) to standardize:
- Enter-key navigation
- “link graph” from one field to the next
- optional validation hooks that clear previous error state on new input

Auto-clear-on-correction rule (recommended where users type to fix errors):
- When you show a coordinator-managed error state (e.g., `coord.set_error(...)`), register validators for the fields you want to auto-clear.
- Use either:
	- `validate_fn=...` on `coord.add_link(...)`, or
	- coordinator validator registration APIs (when available)

Goal: once the user corrects the field and it validates, the dialog clears the previous error without extra controller code.

Note: some flows intentionally avoid coordinator wiring for specific Enter behavior (e.g., Add flow that jumps fields without requiring `add_link` on every widget). That’s fine—be explicit and consistent.

### 7) Input handling pipeline (Enter → parse → validate → feedback)
Standardize the “field action” path:

1) **Input handler** parses user text into a typed value:
- `modules/ui_utils/input_handler.py` (raises `ValueError` for user-fixable issues)

2) **Input validation** checks semantic/business rules:
- `modules/ui_utils/input_validation.py`
- Prefer returning `(ok, msg)` for simple checks; reserve raising for programmer errors.

3) **UI feedback**:
- For user-fixable issues (e.g., `ValueError`):
	- update dialog-local status label with `ui_feedback.set_status_label(..., ok=False)`
	- do **not** write `error.log`
	- do **not** use StatusBar
- For handled operational failures (DB returns `(ok=False, msg)`):
	- set status label (immediate) + `log_and_set_post_close(...)` (post-close StatusBar + error.log)
- For exceptions (unexpected operational errors caught inside controller):
	- Prefer `report_exception_post_close(...)` (error.log + post-close StatusBar intent)
	- `report_exception(...)` is the immediate StatusBar variant; avoid it from modal dialog runtime code unless you intentionally want an immediate message.

### 8) OK/Cancel semantics + post-close message
OK/Cancel/Close should be consistent:

- OK:
	- re-validate mandatory fields (and optional fields if non-empty) to handle “user typed but didn’t press Enter” cases
	- on success: set payload attributes on `dlg` and call `dlg.accept()`
	- set a post-close intent using `set_dialog_info(...)` or `set_dialog_main_status_max(...)`

- Cancel/Close:
	- set an info-level post-close intent (e.g., “<Dialog> closed.”)
	- call `dlg.reject()`

Post-close StatusBar intent APIs:
- `set_dialog_info(dlg, msg)`
- `set_dialog_error(dlg, msg)`
- `set_dialog_main_status_max(dlg, msg, level='info'|'warning'|'error')`

Severity precedence:
- `error > warning > info` (failure/warning overrides success in the StatusBar)

### 9) Outer wrapper responsibilities (standard for all dialogs)
`DialogWrapper` is the single outer layer for dialog execution. It owns:

- Overlay / scanner modal block
- Optional barcode override install/clear convention
- Geometry / centering
- Cleanup / focus restore
- StatusBar display responsibilities:
	- Post-close: shows `dlg.main_status_msg` after `exec_()` returns
	- UI-load failures: shows deferred “UI missing/load failed” message when controller returns `None`
	- Hard-fail runtime: logs traceback to `error.log` and shows a generic StatusBar hint

## Fail taxonomy (use this consistently)

### Hard-fail (open-time)
- UI missing / UI load failure and no fallback dialog provided → controller returns `None`.
- Required widget binding fails (`require_widgets(..., hard_fail=True)` raises) → exception escapes to wrapper.

### Hard-fail (runtime)
- Any unexpected exception escapes controller code → wrapper logs traceback + shows generic StatusBar hint.

### Soft-fail (runtime)
- User-fixable input errors → dialog label only (no StatusBar, no `error.log`).
- Operational failures handled in controller (DB `(ok=False,msg)`, refresh failures, etc.) → log + post-close StatusBar intent.

### Soft-disable
- Dialog still opens but a non-essential feature is disabled (e.g., completer missing). Prefer warning-level post-close intent if user impact is real.

## Error policy (opt-in)
Use `modules/ui_utils/error_policy.py` to centralize “what to log vs what to show” without rewriting dialog wiring:
- `safe_call(where, fn, host_window=..., user_message=..., category=..., fallback=...)`
