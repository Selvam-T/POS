# Dialog Utilities (ui_utils/dialog_utils.py)

Updated: January 2026

This document describes the shared dialog utilities in `modules/ui_utils/dialog_utils.py`.
These helpers support the standardized dialog pipeline used by menu dialogs and sales dialogs.

---

## Goals

- Consistent `.ui` loading behavior (hard-fail boundary)
- Consistent error logging + StatusBar messaging
- Consistent dialog construction (wrap non-QDialog roots, apply modality, apply QSS)
- Consistent widget binding (fail fast when required widgets are missing)

---

## Core Concepts

### UI-load fallback boundary

`load_ui_strict(...)` is the recommended boundary for “can this dialog open at all?”.

- If the `.ui` file is missing or fails to load:
  - details are logged via `log_error(...)`
  - a short StatusBar error is shown (best-effort) when a host window is provided
  - `None` is returned so the caller can hard-fail

### Post-close StatusBar messages

Dialogs can request a StatusBar message after they close using:

- `set_dialog_info(dlg, msg)` (non-error)
- `set_dialog_error(dlg, msg)` (error)

The execution wrapper (`DialogWrapper`) reads these attributes after `exec_()` and displays them.

---

## API Reference

### `set_dialog_main_status(dlg, message, *, is_error=False, duration=4000)`

Stores a “post-close message request” on the dialog instance.

Used by wrappers that want consistent messaging even when the dialog rejects/cancels.

### `set_dialog_info(dlg, message, *, duration=4000)`

Convenience wrapper around `set_dialog_main_status(..., is_error=False)`.

### `set_dialog_error(dlg, message, *, duration=5000)`

Convenience wrapper around `set_dialog_main_status(..., is_error=True)`.

### `report_to_statusbar(host_window, message, *, is_error=True, duration=4000)`

Best-effort StatusBar helper (delegates to `ui_feedback.show_main_status`).

### `center_dialog_relative_to(dlg, host)`

Best-effort geometry helper: centers a dialog relative to the host window.

### `load_ui_strict(ui_path, *, host_window=None, dialog_name='Dialog') -> QWidget | None`

Strict `.ui` loader:

- missing/invalid `.ui` → logs and returns `None`
- success → returns the loaded root widget

### `report_exception(host_window, where, exc, *, user_message=None, duration=5000)`

Standardized exception routing:

- logs detailed exception + traceback
- shows a short StatusBar message (best-effort)

This is intended for unexpected DB/UI failures where users need a quick hint but developers need full traceback.

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
