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
This documentation is True and highly relevant to the product_menu.py you provided. It is not corrupt; it describes the design patterns we implemented to keep your UI predictable.
Here is how those documentation points are specifically applied in your code:

1. **Exclusive Input Relationships**
	 - **Documentation:** `enforce_exclusive_lineedits([...])`
	 - **Reality in Code:** TRUE.
		 - In the REMOVE and UPDATE tabs, you have both a "Product Code" field and a "Name Search" field.
		 - Your code (Lines 1118–1130) uses this utility to ensure that if a user types in the Code field, the Name Search is cleared/disabled, and vice versa. This prevents the user from trying to search for two different things at once.

2. **Gating (Unlock when valid)**
	 - **Documentation:** FocusGate and/or controller-level “gate update” functions
	 - **Reality in Code:** TRUE.
		 - ADD Tab: Uses a controller-level function _update_add_gate (Lines 1201–1221). It monitors textChanged on the product code and only calls add_gate.set_locked(False) when the code passes all policy checks.
		 - UPDATE Tab: Uses upd_gate.set_locked(False) inside the _on_upd_sync callback (Line 1079), unlocking the fields only after a successful database lookup.

3. **Clear on Relock**
	 - **Documentation:** Must clear gated fields when relocking
	 - **Reality in Code:** TRUE.
		 - In _update_add_gate (Lines 1205–1209), if the code becomes invalid (e.g., the user deletes a character), it immediately loops through the Name, Price, and Supplier fields and calls .clear().
		 - This prevents "ghost data" from a previous entry from staying on the screen when the gate closes.

4. **Placeholder Policy**
	 - **Documentation:** Prefer .ui default + placeholder text authored in Qt Designer.
	 - **Reality in Code:** TRUE.
		 - You have a specific mechanism (_remember_ui_for_lineedit and _ui_placeholders) at Lines 931–943.
		 - This implements the policy perfectly: instead of hardcoding "Enter Name" in the Python code, your script takes a snapshot of what you wrote in Qt Designer and restores it when the field is unlocked. This allows you to change the UI look in Designer without touching the Python logic.

**Summary**
The documentation is a "Policy Manual," and your product_menu.py is a "Perfect Implementation" of those rules. Using these shared patterns is exactly why your new code is so much shorter and more robust than the 1200-line version.

### 6) Coordinator wiring (standard interaction engine)
Use `FieldCoordinator` (and related focus utils) to standardize:
- Enter-key navigation
- “link graph” from one field to the next
- optional validation hooks that clear previous error state on new input

**Auto-clear-on-correction**

**The Goal: Automated Error Cleanup**
The objective is to eliminate "stale" error messages. Instead of making the programmer write manual code to clear a label every time a user types, the Coordinator watches the input. As soon as the user provides a value that passes the validation rules, the red error message vanishes instantly. This keeps the UI feeling responsive and "smart" without cluttering the controller with repetitive clearing logic.

**The Note: Architectural Flexibility**
This acknowledges that you don’t have to force every single widget into the FieldCoordinator "link graph."
When to skip it: If a field only needs a simple focus jump (like moving from Supplier to Category) and doesn't require a database lookup or complex state changes, standard PyQt tab-ordering is fine.

**The Requirement:** If you choose to skip the coordinator for a specific flow, ensure you stay consistent. Don't make the Enter-key behave one way on Tab A and a completely different way on Tab B, or the user will get frustrated.

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
