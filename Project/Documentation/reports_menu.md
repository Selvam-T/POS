# Reports Menu Functional Notes

## Scope
This document summarizes the current functional design for report-menu wiring, focusing on the active helper functions and behaviors.

## Core Controller Function
### `modules/menu/report_menu.py`
- `launch_reports_dialog(host_window)`
  - Loads and returns the report dialog (`ui/report_menu.ui`) as modal + frameless.
  - Applies shared dialog stylesheet (`assets/dialog.qss`).
  - Wires close/cancel behavior to reject the dialog.
  - Applies role defaults/permissions via `_apply_role_default_state(...)`.
  - Wires shared date gating via `DateRangeGateController`.
  - Sets default landing focus to `viewReportBtn` (deferred to next event loop tick).

- `_apply_role_default_state(dlg, is_admin)`
  - Admin defaults:
    - `detailReportRadioBtn` selected
    - `todayRadioBtn` selected
    - all report-type/date-range radios enabled
  - Staff defaults:
    - `summaryReportRadioBtn` selected
    - `todayRadioBtn` selected
    - `detailReportRadioBtn`, `chartReportRadioBtn`, `inactivityReportRadioBtn`, `dateRangeRadioBtn` disabled

- `_defer_focus(widget)`
  - Utility to apply focus on the next event-loop tick (`QTimer.singleShot(0, ...)`) for reliable focus landing.

## Shared Date Gating Module
### `modules/date_time/date_gating.py`
- `set_locked_property(widget, locked)`
  - Sets dynamic property `locked=true/false` and refreshes style.

- `set_dateedit_locked(date_edit, locked)`
  - Locked state:
    - widget disabled
    - display format forced to blank (`' '`) and line-edit cleared
  - Unlocked state:
    - widget enabled
    - original date display format restored

- `set_buttons_locked(buttons, locked)`
  - Enables/disables button list and applies `locked` style property.

- `DateRangeGateController(...)`
  - Shared progressive gating controller for today/date-range flow.
  - Inputs:
    - `today_radio`, `date_range_radio`
    - `from_date_edit`, `to_date_edit`
    - `action_buttons`
    - optional `field_labels`
    - optional `on_actions_unlocked` callback
  - Behavior:
    - `todayRadioBtn` selected:
      - both date edits locked and visually blank
      - action buttons enabled
    - `dateRangeRadioBtn` selected:
      - focus lands on `from_date_edit`
      - `from_date_edit` unlocked first
      - `to_date_edit` remains locked until Enter on From
      - action buttons remain locked until Enter on To
      - on To Enter unlock, callback can move focus (used for `viewReportBtn`)
    - date consistency:
      - `to_date_edit` minimum date follows selected From date
      - To date auto-clamped if it becomes earlier than From date
    - label lock behavior:
      - when date-range is unavailable/unselected, passed field labels are marked `locked=true`
      - when date-range is selected/active, labels are restored (`locked=false`)

## Styling Hooks (QSS)
### `assets/dialog.qss`
- `QDateEdit[locked="true"]` and nested selectors enforce gray/blank locked date fields.
- `QDateEdit[locked="false"]` restores normal editable visuals.
- `QPushButton[objectName="viewReportBtn|savePdfReportBtn|saveExcelReportBtn"][locked="true"]`
  - disabled/locked action button styling.
- `QPushButton#viewReportBtn:focus`, `#savePdfReportBtn:focus`, `#saveExcelReportBtn:focus`
  - explicit orange focus border for report actions.
- `QRadioButton#dateRangeRadioBtn:disabled` and indicator disabled styles
  - gray disabled date-range radio visuals.
- `QLabel[objectName$="FieldLbl"][locked="true|false"]`
  - gray/restored color for date field labels.

## Current Status
- Role defaults and permissions are implemented.
- Shared date gating is implemented and reusable for future controllers.
- Focus landing and progressive focus jump to `viewReportBtn` are implemented.
- Temporary debug print used during testing has been removed.
- Remaining planned enhancement:
  - wire `resetReportBtn` to re-apply role defaults and date-gating state in one action.
