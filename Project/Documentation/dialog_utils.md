# Dialog Utilities (ui_utils/dialog_utils.py)

Updated: January 2026

This document describes the shared dialog utilities in `modules/ui_utils/dialog_utils.py`.
These helpers support the standardized dialog pipeline used by menu dialogs and sales dialogs.

---

## Goals

- Consistent `.ui` loading behavior (hard-fail boundary)
- Consistent error logging + StatusBar messaging
- Avoid StatusBar messages while a modal dialog is still open (prefer post-close intent)
- Consistent dialog construction (wrap non-QDialog roots, apply modality, apply QSS)
- Consistent widget binding (fail fast when required widgets are missing)

---

## Core Concepts

### UI-load fallback boundary

`load_ui_strict(...)` is the recommended boundary for “can this dialog open at all?”.

- If the `.ui` file is missing or fails to load:
  - details are logged via `log_error(...)`
  - a short StatusBar error is **deferred** when a host window is provided (so it isn’t hidden under a modal overlay)
  - `None` is returned so the caller can hard-fail

### Post-close StatusBar messages

Dialogs can request a StatusBar message after they close using:

- `set_dialog_info(dlg, msg)` (non-error)
- `set_dialog_error(dlg, msg)` (error)

The execution wrapper (`DialogWrapper`) reads these attributes after `exec_()` and displays them.

### Modal-safe StatusBar policy

When a modal dialog is open, the overlay is active and the StatusBar is visually “behind” the modal.
To keep UX consistent:

- Prefer setting **post-close** StatusBar intent on the dialog (via `set_dialog_*` helpers).
- Avoid calling `report_to_statusbar(...)` from inside modal dialog handlers.

UI-load failures are a special case:
- `load_ui_strict(...)` queues a pending main-window StatusBar message.
- `DialogWrapper` flushes it if the controller returns `None`.

For exception scenarios during a modal dialog, use the **post-close** exception helper:
- `report_exception_post_close(...)`

For handled (non-exception) failures (e.g., DB CRUD returning `(ok=False, msg)`), use:
- `log_and_set_post_close(...)`

---

## API Reference

### `set_dialog_main_status(dlg, message, *, is_error=False, duration=4000)`

Stores a “post-close message request” on the dialog instance.

Used by wrappers that want consistent messaging even when the dialog rejects/cancels.

### `set_dialog_info(dlg, message, *, duration=4000)`

Convenience wrapper around `set_dialog_main_status(..., is_error=False)`.

### `set_dialog_error(dlg, message, *, duration=5000)`

Convenience wrapper around `set_dialog_main_status(..., is_error=True)`.

### `set_dialog_main_status_max(dlg, message, *, level='info', is_error=None, duration=4000)`

Sets the dialog’s post-close StatusBar intent only if the new message is **at least as severe** as the existing one.

Severity precedence:
- `error` > `warning` > `info`

This supports the rule: “failure/warning takes precedence over success in the StatusBar”.

### `report_to_statusbar(host_window, message, *, is_error=True, duration=4000)`

Best-effort StatusBar helper (delegates to `ui_feedback.show_main_status`).

Note: This shows **immediately**. Use sparingly from modal dialog code.

### `center_dialog_relative_to(dlg, host)`

Best-effort geometry helper: centers a dialog relative to the host window.

### `load_ui_strict(ui_path, *, host_window=None, dialog_name='Dialog') -> QWidget | None`

Strict `.ui` loader:

- missing/invalid `.ui` → logs and returns `None`
- success → returns the loaded root widget

If `host_window` is provided, UI-load failures will queue a pending StatusBar message for the wrapper to display after overlay cleanup.

### `report_exception(host_window, where, exc, *, user_message=None, duration=5000)`

Standardized exception routing:

- logs detailed exception + traceback
- shows a short StatusBar message (best-effort, immediate)

This is intended for unexpected DB/UI failures where users need a quick hint but developers need full traceback.

### `report_exception_post_close(dlg, where, exc, *, user_message, level='error', duration=5000)`

Modal-safe exception routing:

- logs detailed exception + traceback to `log/error.log`
- sets a post-close StatusBar intent on the dialog (so `DialogWrapper` shows it after `exec_()` returns)

### `log_exception_only(where, exc)`

Logs a detailed exception + traceback to `log/error.log` without StatusBar messaging.

### `log_and_set_post_close(dlg, where, details, *, user_message, level='error', duration=5000)`

For non-exception failures (typically DB functions returning `(ok=False, msg)`):

- logs to `log/error.log`
- sets post-close StatusBar intent on the dialog (severity precedence honored)

---


## Fallback Error Dialog Helper

### `build_error_fallback_dialog(host_window, dialog_name, qss_path=None) -> QDialog`

Builds a standardized, themed error dialog programmatically (no .ui file required). This is used as a fallback when a dialog's .ui file fails to load, ensuring the user always sees a clear error message and can close the dialog. The fallback dialog propagates an error message to the main window status bar on close. As of January 2026, `product_menu.py` and other dialogs may call this function if their .ui fails to load.

**Features:**
- 250x250 modal dialog, bold 16pt font
- QSS applied if provided
- Prominent error message and close button
- Sets a post-close error message for the main window status bar

---

## Opt-in Builder Helpers

### `build_dialog_from_ui(ui_path, *, host_window=None, dialog_name='Dialog', qss_path=None, frameless=True, application_modal=True) -> QDialog | None`

Standard dialog builder:

- loads UI using `load_ui_strict(...)`
- if the UI root is not a `QDialog`, wraps it inside a `QDialog` container
- applies modality + optional frameless flags
- applies QSS best-effort

This is used by modern dialog controllers to reduce boilerplate.

### `require_widgets(root, required: dict, *, hard_fail=True) -> dict`

Widget binder:

- resolves widgets via `root.findChild(Class, objectName)`
- returns a dict mapping your logical keys to real widget objects
- when `hard_fail=True`, raises `ValueError` if any required widgets are missing

Recommended use: bind all required widgets once at construction time.

---

## Recommended Usage Pattern

A typical dialog constructor follows this shape:

1. `dlg = build_dialog_from_ui(...)`
2. `widgets = require_widgets(dlg, {...})`
3. configure read-only fields and focus policies
4. wire relationships and Enter navigation (FieldCoordinator)
5. apply gating (FocusGate) if needed
6. connect OK/Cancel handlers

See also: `Documentation/dialog_pipeline.md`.

---

## See Also

- `Documentation/dialog_pipeline.md`
- `Documentation/error_logging_and_fallback.md`
