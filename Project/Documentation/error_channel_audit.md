# Error Channel Audit

## Scope

This document is an implementation audit of how runtime failures are currently
channeled across the POS codebase.

It is intentionally different from `Documentation/error_logging_and_fallback.md`.
That document defines the general logging and fallback policy. This document maps
actual code paths by file and feature area:

- whether the failure is treated as hard-fail, soft-fail, or best-effort
- whether details are written to `logs/error.log`
- whether the user sees feedback in a dialog-local `*statusLabel`
- whether the user sees feedback in the main window `StatusBar`
- whether the `StatusBar` message is immediate or deferred until after a dialog
  closes
- which display duration constant is used when one is explicit or inherited

This audit covers `main.py` and `modules/**`. It does not classify tests,
developer tools, or existing documentation.

## Duration Constants

Defined in `config.py`:

- `STATUS_LABEL_SHORT_DURATION_MS = 2500`
- `STATUS_LABEL_DURATION_MS = 3500`
- `STATUS_LABEL_LONG_DURATION_MS = 5000`
- `MAIN_STATUS_SHORT_DURATION_MS = 3000`
- `MAIN_STATUS_DURATION_MS = 4000`
- `MAIN_STATUS_EXTENDED_DURATION_MS = 4500`
- `MAIN_STATUS_ERROR_DURATION_MS = 4000`
- `MAIN_STATUS_LONG_DURATION_MS = 5000`
- `PERSISTENT_DURATION_MS = 0`

Shared defaults:

- `ui_feedback.set_status_label(...)` defaults to
  `STATUS_LABEL_DURATION_MS`.
- `ui_feedback.set_warning_status_label(...)` defaults to
  `STATUS_LABEL_SHORT_DURATION_MS`.
- `dialog_utils.report_to_statusbar(...)` defaults to
  `MAIN_STATUS_DURATION_MS`.
- `dialog_utils.report_exception(...)` defaults to
  `MAIN_STATUS_ERROR_DURATION_MS`.
- `dialog_utils.set_dialog_info(...)` defaults to
  `MAIN_STATUS_DURATION_MS`.
- `dialog_utils.set_dialog_error(...)` defaults to
  `MAIN_STATUS_ERROR_DURATION_MS`.
- `dialog_utils.log_exception_traceback_and_postclose_statusBar(...)` defaults
  to `MAIN_STATUS_ERROR_DURATION_MS`.
- `dialog_utils.log_error_message_and_postclose_statusBar(...)` defaults to
  `MAIN_STATUS_ERROR_DURATION_MS`.

## Channel Categories

### 1. Report only to StatusBar post close, no error log

These are mostly normal dialog outcomes or fallback status intents. They set
`dlg.main_status_msg`; `DialogWrapper` displays the message after the modal
dialog closes.

Files and examples:

- `modules/sales/manual_entry.py`
  - Added item: `set_dialog_info(...)`; post-close `StatusBar`;
    `MAIN_STATUS_DURATION_MS`.
  - Cancelled: `set_dialog_info(...)`; post-close `StatusBar`;
    `MAIN_STATUS_DURATION_MS`.
  - Manual-entry fallback UI message: `set_dialog_error(...)`; post-close
    `StatusBar`; `MAIN_STATUS_ERROR_DURATION_MS`; no direct log at this call
    site.
- `modules/sales/clear_cart.py`
  - Sale cancellation aborted/current sale cleared: `set_dialog_main_status_max`;
    post-close `StatusBar`; default `MAIN_STATUS_DURATION_MS`.
  - Missing UI fallback: `set_dialog_error(...)`; post-close `StatusBar`;
    `MAIN_STATUS_ERROR_DURATION_MS`; direct log is only present for mapping
    fallback, not for this exact fallback status.
- `modules/menu/logout_menu.py`
  - Logout cancelled or fallback-mode cancelled: post-close `StatusBar`;
    default `MAIN_STATUS_DURATION_MS`.
  - Missing logout UI fallback: `set_dialog_error(...)`;
    `MAIN_STATUS_ERROR_DURATION_MS`; no direct log at this call site.
- `modules/menu/greeting_menu.py`
  - Greeting selected/closed: `set_dialog_main_status(...)`; post-close
    `StatusBar`; default `MAIN_STATUS_DURATION_MS`.
- `modules/payment/refund.py` and `modules/payment/vendor.py`
  - Successful save and cancel paths: `set_dialog_info(...)`; post-close
    `StatusBar`; `MAIN_STATUS_DURATION_MS`.
- `modules/menu/report_menu.py`
  - Dialog closed, report selection cancelled, report viewer success:
    `set_dialog_info(...)`; post-close `StatusBar`;
    `MAIN_STATUS_DURATION_MS`.
- `modules/menu/product_menu.py`
  - Product menu closed: `set_dialog_main_status_max(...)`; post-close
    `StatusBar`; `MAIN_STATUS_DURATION_MS`.

### 2. Report only in StatusLabel

These are usually user-correctable validation failures. They are soft-fails and
are not written to `logs/error.log`.

Files and examples:

- `modules/sales/login.py`
  - Invalid credentials or validation messages use `ui_feedback.set_status_label`;
    dialog-local label only; default `STATUS_LABEL_DURATION_MS`.
- `modules/sales/manual_entry.py`
  - Input `ValueError` from product/quantity validation goes to the dialog
    status label only; default `STATUS_LABEL_DURATION_MS`.
- `modules/sales/hold_sales.py`
  - Invalid customer, no active sale, or no logged-in user goes to
    `holdStatusLabel`; default `STATUS_LABEL_DURATION_MS`.
- `modules/payment/refund.py`
  - Product selection, amount, note, and no-user validation failures go to the
    dialog status label only; default `STATUS_LABEL_DURATION_MS`.
- `modules/payment/vendor.py`
  - Amount/note/no-user validation failures go to the dialog status label only;
    default `STATUS_LABEL_DURATION_MS`.
- `modules/payment/payment_panel.py`
  - Allocation/tender validation messages go to payment-panel status label via
    `_set_status(...)`; default `STATUS_LABEL_DURATION_MS`.
  - Examples: `Invalid amount.`, `Cash tender < CASH payable.`,
    `Payable not fully allocated.`, `overpayment detected, rectify payment
    allocation`.
- `modules/payment/todo.py`
  - Todo input validation and save failures show the todo dialog status label;
    explicit `STATUS_LABEL_DURATION_MS`.
  - Warnings use `set_warning_status_label(...)`; explicit
    `STATUS_LABEL_DURATION_MS`.
- `modules/sales/vegetable_entry.py`
  - Invalid weight and empty vegetable table are label-only soft-fails; default
    `STATUS_LABEL_DURATION_MS`.
- `modules/sales/view_hold.py`
  - Selection/search gating failures such as `Select a receipt.`,
    `Unable to resolve receipt id.`, `No items found for this receipt.`, and
    `Select an action.` go to dialog status label only unless the handler later
    logs an operational failure.
- `modules/menu/receipt_menu.py`
  - Selection warnings and unsupported action warnings, such as selecting no
    receipt or trying to void a non-UNPAID receipt, use status label/warning
    status only; default or explicit `STATUS_LABEL_DURATION_MS`.
- `modules/menu/product_menu.py`
  - Form validation errors and reserved-item checks use tab status labels only;
    default `STATUS_LABEL_DURATION_MS`.
- `modules/menu/admin_menu.py`
  - Password validation errors use focus/status feedback only.
  - Screen 2 setup failure is shown in `screen2Status`; default
    `STATUS_LABEL_DURATION_MS`; it is not logged at that call site.
- `modules/menu/screen2_ads_helper.py`
  - Image capacity, selection, invalid file, and remove failures use the
    Screen 2 status label; default `STATUS_LABEL_DURATION_MS` unless a call
    provides another duration.

### 3. Log and report to StatusBar

These are support-relevant failures where the user needs a main-window message
and details need to reach `logs/error.log`. In modal dialogs, this is often a
post-close status intent. Outside modal dialogs, the `StatusBar` update is
usually immediate.

Files and examples:

- `modules/wrappers/dialog_wrapper.py`
  - Unexpected dialog construction/runtime exception:
    logs `Dialog failed: ...` plus traceback; displays
    `Error: Dialog failed (see error.log)` after cleanup;
    `MAIN_STATUS_LONG_DURATION_MS`.
  - Pending UI-load status messages are flushed after overlay cleanup; duration
    comes from `_pending_main_status_duration`, usually
    `MAIN_STATUS_LONG_DURATION_MS`.
- `modules/ui_utils/dialog_utils.py`
  - `load_ui_strict(...)`: missing/corrupt UI logs and queues pending main
    `StatusBar`; `MAIN_STATUS_LONG_DURATION_MS`.
  - `report_exception(...)`: logs exception details and immediately reports
    main `StatusBar`; default `MAIN_STATUS_ERROR_DURATION_MS`.
- `main.py`
  - Payment processing exception uses `report_exception(...)`; logs traceback
    and reports `Payment failed to update DB. Please retry.`;
    `MAIN_STATUS_LONG_DURATION_MS`.
  - Repeated payment DB failure also reports retry count in `StatusBar`;
    `MAIN_STATUS_LONG_DURATION_MS`; when the retry limit is reached, the lock
    message is persistent via `PERSISTENT_DURATION_MS`.
  - Cash drawer helper failure or false return logs and reports `StatusBar`;
    `MAIN_STATUS_ERROR_DURATION_MS`.
  - Sales table infrastructure failure logs once and later blocks entry points
    with a repeated `StatusBar` message; duration depends on the reporting call.
- `modules/payment/payment_panel.py`
  - Refund/vendor/todo dialog launch failures log and report immediate
    `StatusBar`; `MAIN_STATUS_ERROR_DURATION_MS`.
  - Payment failure receipt print setup failure logs and reports
    `Receipt print failed.`; `MAIN_STATUS_ERROR_DURATION_MS`.
  - Receipt print `ValueError`, `RuntimeError`, or generic exception logs and
    reports immediate `StatusBar`; `MAIN_STATUS_ERROR_DURATION_MS`.
- `modules/payment/keypad_controller.py`
  - Keypad digit/dot/fast-set/backspace/clear/tab/enter exceptions log and
    report immediate `StatusBar`; `MAIN_STATUS_SHORT_DURATION_MS`.
- `modules/payment/recovery_receipt.py`
  - Payment-failure receipt print failure logs and reports immediate
    `StatusBar`; duration is passed in those calls, usually
    `MAIN_STATUS_ERROR_DURATION_MS`.
- `modules/customer_display/customer_display.py`
  - `screen2.ui` load failure logs traceback and reports fallback status;
    `MAIN_STATUS_ERROR_DURATION_MS`.
  - Customer display connect/disconnect reports status only with
    `MAIN_STATUS_SHORT_DURATION_MS`; load/fallback failures are the logged
    variants.
- `modules/status_footer/status_footer.py`
  - Error-log export/clear failures log and report footer `StatusBar`;
    `MAIN_STATUS_ERROR_DURATION_MS`.
- `modules/devices/printer_and_drawer.py` and `modules/devices/print_helper.py`
  - Device-level printer/cash-drawer failures log at the device layer. User
    display happens through callers such as `main.py`, `payment_panel.py`,
    `receipt_menu.py`, and `view_hold.py`, not always inside the device module
    itself.

### 4. Log, report to StatusLabel, and report to StatusBar

These are handled operational failures where the dialog remains coherent enough
to show local feedback, while the main app also receives a support-facing
message after close or immediately.

Files and examples:

- `modules/menu/product_menu.py`
  - Add/remove/update DB failures use
    `log_error_message_and_postclose_statusBar(...)`, then update the tab
    status label.
  - StatusBar duration: `MAIN_STATUS_ERROR_DURATION_MS`.
  - StatusLabel duration: default `STATUS_LABEL_DURATION_MS`.
  - Category add/replace/remove exceptions similarly show `cat_status`, log,
    set post-close `StatusBar`, then reject after a short timer.
- `modules/sales/view_hold.py`
  - Receipt item load exceptions use
    `log_exception_traceback_and_postclose_statusBar(...)`, plus local status
    label; `MAIN_STATUS_ERROR_DURATION_MS`.
  - Loading held receipt into the sales table can mark the sales table
    unavailable, set a local label, and set post-close `StatusBar`;
    `MAIN_STATUS_LONG_DURATION_MS`.
  - Cancelling the held receipt after loading logs exception or handled false
    return, shows local label, and queues post-close `StatusBar`;
    `MAIN_STATUS_ERROR_DURATION_MS`.
  - Print failure logs handled printer result or exception, shows label, and
    queues post-close `StatusBar`; `MAIN_STATUS_ERROR_DURATION_MS`.
  - Void exception logs traceback, shows label, and queues post-close
    `StatusBar`; `MAIN_STATUS_ERROR_DURATION_MS`.
  - Void false return shows label and immediate `StatusBar`, but does not log at
    that specific branch.
- `modules/menu/receipt_menu.py`
  - Receipt search exception clears table, shows label, logs traceback, and
    queues post-close `StatusBar`; `MAIN_STATUS_ERROR_DURATION_MS`.
  - Print failure or printer false return shows label, logs, and queues
    post-close `StatusBar`; `MAIN_STATUS_ERROR_DURATION_MS`.
  - Void false return or exception shows label, logs, and queues post-close
    `StatusBar`; `MAIN_STATUS_ERROR_DURATION_MS`.
- `modules/sales/vegetable_entry.py`
  - Scale exception, staging-table exception, and prepare-result exception call
    `_report_vegetable_runtime_failure(...)`.
  - This shows local status label, logs traceback, and queues post-close
    `StatusBar`; `MAIN_STATUS_LONG_DURATION_MS`.
- `modules/sales/hold_sales.py`
  - Commit exception tries to print a snapshot/fallback receipt, logs the
    original exception with traceback, and queues post-close `StatusBar`;
    `MAIN_STATUS_LONG_DURATION_MS`.
  - Snapshot print generation failure is also logged with
    `log_error_message(...)` and status intent is set with
    `MAIN_STATUS_ERROR_DURATION_MS`.
- `modules/payment/refund.py` and `modules/payment/vendor.py`
  - Save exceptions log traceback and queue post-close `StatusBar`;
    `MAIN_STATUS_LONG_DURATION_MS`.
  - They reject immediately rather than also showing a local label in the
    exception branch, so they are closer to category 3 for unexpected DB/runtime
    failure and category 2 for validation failure.
- `modules/menu/admin_menu.py`
  - Password update exception logs traceback and queues post-close `StatusBar`;
    default `MAIN_STATUS_ERROR_DURATION_MS`.
  - Validation failures remain label-only.

## Log-only Or Silenced Sites

Some caught exceptions are intentionally not user-facing because they are
best-effort UI, cleanup, focus, styling, cache, or fallback support work.

Log-only examples:

- `main.py`
  - QSS load failure, cash-outflow table ensure failure, menu-button wiring,
    customer display init, Qt handler messages, product cache load, and sales
    table clear failures are logged. Some related user-facing state may happen
    elsewhere, but the logging call itself does not always display a message.
- `modules/sales/sales_panel.py`
  - `sales.qss` load failure logs only.
  - Sales frame initialization logs directly or delegates to main-window sales
    table unavailable handling.
- `modules/menu/report_menu.py`
  - Widget requirement failure, report date-gate wiring, role defaults, and
    selection reset failures are logged only.
  - Export/viewer user errors are usually reported through the report status
    label.
- `modules/menu/admin_menu.py`
  - Export failures are logged and reported through export status label, not
    through main `StatusBar`.
- `modules/menu/receipt_menu.py`
  - Product cache load, preview failure, table fill failure, and signal wiring
    failures are logged. Preview failure also shows dialog status label.
- `modules/ui_utils/category_state.py` and
  `modules/ui_utils/category_service.py`
  - Category archive/backup/reorder/replacement support failures log only or
    return failure to callers that decide display.
- `modules/ui_utils/todo_state.py`
  - Todo JSON load/validation failures log and store last-load error. The todo
    dialog later displays that stored load error in both dialog label and
    post-close `StatusBar`.
- `modules/db_operation/__init__.py`
  - Product cache upsert/remove failures after product DB changes are logged as
    secondary cache failures.
- `modules/devices/printer_and_drawer.py`
  - Device import/send/thread failures log at the device layer. User display is
    caller-dependent.

Silenced/best-effort examples:

- `modules/wrappers/dialog_wrapper.py`
  - Overlay, scanner block/unblock, focus restore, barcode override setup/clear,
    and fallback status cleanup errors are swallowed.
- `modules/ui_utils/ui_feedback.py`
  - Status label operations swallow `RuntimeError` when Qt widgets are already
    deleted.
  - `show_temp_status(...)` swallows `StatusBar` display failure.
- `modules/ui_utils/dialog_utils.py`
  - Failure to write a log or set a dialog status intent is swallowed so the
    original failure path can continue.
- `modules/payment/payment_panel.py`
  - Many payment-frame UI setup, focus, and field-formatting failures are
    swallowed as best-effort.
- `modules/sales/view_hold.py`
  - Search/filter UI refresh, focus, optional panel refresh, and note fallback
    parsing have swallowed branches.
- `modules/devices/barcode_manager.py`
  - Scanner timing/override/focus support failures are mostly swallowed; user
    warnings are only shown for targeted scan-location feedback.
- `modules/date_time/*`, `modules/table_ui/*`, `modules/ui_utils/focus_utils.py`
  - Many parse, focus, and table helper failures are defensive no-ops unless a
    caller supplies a status label or status bar.

## Hard-fail Summary

Hard-fail means an unexpected exception crosses a boundary where the app cannot
continue that operation normally.

- Modal dialog hard-fail boundary:
  - Caught by `DialogWrapper.open_dialog_scanner_blocked(...)`.
  - Logs traceback to `logs/error.log`.
  - Shows `Error: Dialog failed (see error.log)` after cleanup.
  - Duration: `MAIN_STATUS_LONG_DURATION_MS`.
- UI-load hard-fail/open-disable boundary:
  - Caught by `load_ui_strict(...)` or `build_dialog_from_ui(...)`.
  - Logs missing/corrupt UI.
  - Queues main `StatusBar` for after overlay cleanup when host exists.
  - Duration: `MAIN_STATUS_LONG_DURATION_MS`.
- Main sales-table infrastructure hard-fail:
  - Main window marks sales table unavailable.
  - Logs once and blocks transaction entry points.
  - Later blocked actions show main `StatusBar`; no duplicate log for each
    blocked attempt.
- Payment processing DB hard-fail:
  - `main.py` logs exception through `report_exception(...)`.
  - Shows retry message and can enter persistent payment failure lock after the
    configured retry limit.

## Soft-fail Summary

Soft-fail means the code expected the failure and can keep the current UI
usable.

- Validation soft-fails:
  - Usually label-only.
  - No `logs/error.log`.
  - Default label duration: `STATUS_LABEL_DURATION_MS`.
- Operational soft-fails:
  - DB CRUD false return, printer false return, receipt search/void/print
    exceptions, category service exceptions, and failed dialog launcher paths.
  - Usually logged and displayed through status label plus post-close or
    immediate `StatusBar`.
  - Error `StatusBar` duration is usually `MAIN_STATUS_ERROR_DURATION_MS`;
    longer operation failures use `MAIN_STATUS_LONG_DURATION_MS`.
- Soft-disable:
  - Non-essential setup or cache/list/completer failures are often logged only
    or surfaced as a local label.
  - The dialog remains available with reduced capability.

## Notable Inconsistencies

- Some fallback UI error messages are displayed post-close without a direct log
  at the exact display call site.
- Some export/report/admin errors log and use local labels but do not report to
  the main `StatusBar`.
- Some device-layer failures log only; display depends on the caller.
- Some unexpected dialog save failures reject immediately after setting only a
  post-close `StatusBar`, so the user may not see a local status label before
  the dialog closes.
- `error_logging_and_fallback.md` mentions ISO-style timestamps in its example,
  but `error_logger.py` currently writes timestamps like
  `01 JUL 2026, 3:04:05 pm`.

