"""report_menu is the UI controller. 
   It reads the selected report type, builds the request parameters, 
   and decides when to open a viewer.
"""

import os
from pathlib import Path
from PyQt5.QtCore import QObject, QEvent, Qt, QTimer
from PyQt5.QtWidgets import QDialog, QPushButton, QRadioButton, QDateEdit, QLabel
from modules.ui_utils.error_logger import log_error_message
from modules.ui_utils.dialog_utils import set_dialog_info, build_dialog_from_ui, build_error_fallback_dialog, require_widgets
from modules.ui_utils import ui_feedback
from modules.ui_utils.focus_utils import FieldCoordinator
from modules.date_time import (
    clamp_date_range_bounds,
    init_date_range_bounds,
    set_buttons_locked,
    set_dateedit_locked,
    set_locked_property,
)
from modules.menu import report_generator, report_viewers, report_exports
from config import MAIN_STATUS_DURATION_MS, QSS_DIR, STATUS_LABEL_DURATION_MS, UI_DIR

QSS_PATH = os.path.join(QSS_DIR, 'dialog.qss')


def _friendly_openpyxl_message() -> str:
    return 'Excel export unavailable: openpyxl is missing from this Python environment.'

def _apply_role_default_state(dlg: QDialog, *, is_admin: bool) -> None:
    """Apply role defaults and permissions."""
    # Report type selectors use the current QPushButton widget IDs from the UI.
    detail = dlg.findChild(QPushButton, 'salesReportBtn')
    summary = dlg.findChild(QPushButton, 'insightReportBtn')
    chart = dlg.findChild(QPushButton, 'chartReportBtn') or dlg.findChild(QRadioButton, 'chartReportRadioBtn')
    inactivity = dlg.findChild(QPushButton, 'inactivityReportBtn') or dlg.findChild(QRadioButton, 'inactivityReportRadioBtn')
    today = dlg.findChild(QRadioButton, 'todayRadioBtn')
    date_range = dlg.findChild(QRadioButton, 'dateRangeRadioBtn')

    if not all((detail, summary, chart, inactivity, today, date_range)):
        return

    # Role permissions for report/date mode radios.
    # Staff users cannot change report type, but Detail remains the default selected report.
    # Ensure QPushButton selectors are checkable so they behave like radios
    for w in (detail, summary, chart, inactivity):
        try:
            if isinstance(w, QPushButton):
                w.setCheckable(True)
        except Exception:
            pass

    detail.setEnabled(is_admin)
    set_locked_property(detail, not is_admin)
    # Summary is restricted to Admin; Staff users see it disabled/greyed
    summary.setEnabled(is_admin)
    set_locked_property(summary, not is_admin)
    chart.setEnabled(is_admin)
    set_locked_property(chart, not is_admin)
    inactivity.setEnabled(is_admin)
    set_locked_property(inactivity, not is_admin)
    date_range.setEnabled(is_admin)
    set_locked_property(date_range, not is_admin)

    # Both Admin and Staff now land in Detailed report by default.
    detail.setChecked(True)
    today.setChecked(True)

    # Initial focus is assigned later at dialog-level (viewReportBtn).


def _defer_focus(widget) -> None:
    """Set focus on next event-loop tick when widget is enabled."""
    if widget is None:
        return

    def _apply_focus() -> None:
        try:
            if widget.isEnabled():
                widget.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass

    try:
        QTimer.singleShot(0, _apply_focus)
    except Exception:
        _apply_focus()


def _current_report_type(dlg: QDialog) -> str | None:
    """Return normalized report type based on selected report button, or None."""
    try:
        detail = dlg.findChild(QPushButton, 'salesReportBtn')
        summary = dlg.findChild(QPushButton, 'insightReportBtn')
        chart = dlg.findChild(QPushButton, 'chartReportBtn') or dlg.findChild(QRadioButton, 'chartReportRadioBtn')
        inactivity = dlg.findChild(QPushButton, 'inactivityReportBtn') or dlg.findChild(QRadioButton, 'inactivityReportRadioBtn')
        if detail is not None and getattr(detail, 'isChecked', lambda: False)():
            return 'detail'
        if summary is not None and getattr(summary, 'isChecked', lambda: False)():
            return 'summary'
        if chart is not None and getattr(chart, 'isChecked', lambda: False)():
            return 'chart'
        if inactivity is not None and getattr(inactivity, 'isChecked', lambda: False)():
            return 'inactivity'
    except Exception:
        pass
    return None


def _build_report_params(dlg: QDialog, host_window) -> dict:
    """Collect report request params from dialog and host context."""
    from_date = dlg.findChild(QDateEdit, 'reportFromDateEdit')
    to_date = dlg.findChild(QDateEdit, 'reportToDateEdit')
    start_ts = None
    end_ts = None

    try:
        if from_date is not None:
            start_ts = from_date.date().toString('yyyy-MM-dd') + 'T00:00:00'
        if to_date is not None:
            end_ts = to_date.date().toString('yyyy-MM-dd') + 'T23:59:59'
    except Exception:
        pass

    return {
        'from': start_ts,
        'to': end_ts,
        'user_id': getattr(host_window, 'current_user_id', None),
        'username': getattr(host_window, 'current_username', None),
    }


def _build_report_data(dlg: QDialog, host_window, report_type: str) -> dict:
    params = _build_report_params(dlg, host_window)
    rpt = str(report_type).strip().lower() if report_type else ''
    if not rpt:
        return {}
    if rpt == 'detail':
        data = report_generator.get_detailed_report(params)
        if not bool(getattr(host_window, 'current_is_admin', False)):
            data['detail_variant'] = 'minimal'
        return data
    if rpt == 'summary':
        return report_generator.get_summary_report(params)
    if rpt == 'chart':
        return report_generator.get_chart_report(params)
    if rpt == 'inactivity':
        return report_generator.get_inactivity_report(params)
    return {}


def launch_reports_dialog(host_window):
    """Open Reports dialog (ui/report_menu.ui) as a modal frameless panel.
    
    DialogWrapper handles: overlay, sizing, centering, scanner blocking, cleanup, and focus restoration.
    This function only creates and returns the QDialog.
    
    Args:
        host_window: Main window instance
    
    Returns:
        QDialog instance ready for DialogWrapper.open_dialog_scanner_blocked() to execute
    """
    # Use shared dialog builder for consistent error handling and logging
    ui_path = os.path.join(UI_DIR, 'report_menu.ui')
    dlg = build_dialog_from_ui(ui_path, host_window=host_window, dialog_name='report_menu', qss_path=QSS_PATH)
    if dlg is None:
        return build_error_fallback_dialog(host_window, 'Reports', QSS_PATH)

    # Resolve required widgets (hard-fail if UI changed)
    try:
        require_widgets(dlg, {
            'detail': (QPushButton, 'salesReportBtn'),
            'summary': (QPushButton, 'insightReportBtn'),
            'chart': (QPushButton, 'chartReportBtn'),
            'inactivity': (QPushButton, 'inactivityReportBtn'),
            'today': (QRadioButton, 'todayRadioBtn'),
            'date_range': (QRadioButton, 'dateRangeRadioBtn'),
            'from_date': (QDateEdit, 'reportFromDateEdit'),
            'to_date': (QDateEdit, 'reportToDateEdit'),
            'view_btn': (QPushButton, 'viewReportBtn'),
            'save_pdf_btn': (QPushButton, 'savePdfReportBtn'),
            'save_excel_btn': (QPushButton, 'saveExcelReportBtn'),
            'reset_btn': (QPushButton, 'resetReportBtn'),
            'cancel_btn': (QPushButton, 'btnReportCancel'),
            'status_lbl': (QLabel, 'reportStatusLabel'),
        }, hard_fail=True)
    except Exception as e:
        try:
            log_error_message(f"report_menu: require_widgets failed: {e}")
        except Exception:
            pass
        return dlg

    is_admin_user = bool(getattr(host_window, 'current_is_admin', False))

    # Preserve original reject so handlers can bypass wrapper when needed.
    try:
        orig_reject = getattr(dlg, 'reject', None)
    except Exception:
        orig_reject = None

    # Wrap reject to provide a default post-close status message.
    try:
        if callable(orig_reject):
            def _reject_with_default_msg():
                try:
                    if not getattr(dlg, 'main_status_msg', None):
                        set_dialog_info(dlg, 'Report dialog closed.', duration=MAIN_STATUS_DURATION_MS)
                except Exception:
                    pass
                try:
                    orig_reject()
                except Exception:
                    pass
            dlg.reject = _reject_with_default_msg
    except Exception:
        pass

    # Titlebar close (optional)
    try:
        xbtn: QPushButton = dlg.findChild(QPushButton, 'customCloseBtn')
        if xbtn:
            # Match admin-menu behavior: resolve the current reject at click time.
            xbtn.clicked.connect(lambda: dlg.reject())
    except Exception:
        pass

    # OK/Cancel wiring (optional names, robust to missing widgets)
    ok = dlg.findChild(QPushButton, 'btnOk') or dlg.findChild(QPushButton, 'okButton')
    cancel = dlg.findChild(QPushButton, 'btnCancel') or dlg.findChild(QPushButton, 'cancelButton')
    if ok:
        ok.clicked.connect(dlg.accept)
    if cancel:
        cancel.clicked.connect(dlg.reject)

    # Report action/date widgets for gating flow
    date_range = dlg.findChild(QRadioButton, 'dateRangeRadioBtn')
    inactivity = dlg.findChild(QPushButton, 'inactivityReportBtn') or dlg.findChild(QRadioButton, 'inactivityReportRadioBtn')
    today = dlg.findChild(QRadioButton, 'todayRadioBtn')
    from_date = dlg.findChild(QDateEdit, 'reportFromDateEdit')
    to_date = dlg.findChild(QDateEdit, 'reportToDateEdit')
    from_label = dlg.findChild(QLabel, 'reportFromDateFieldLbl')
    to_label = dlg.findChild(QLabel, 'reportToDateFieldLbl')
    view_btn = dlg.findChild(QPushButton, 'viewReportBtn')
    save_pdf_btn = dlg.findChild(QPushButton, 'savePdfReportBtn')
    save_excel_btn = dlg.findChild(QPushButton, 'saveExcelReportBtn')
    reset_btn = dlg.findChild(QPushButton, 'resetReportBtn')
    report_cancel_btn = dlg.findChild(QPushButton, 'btnReportCancel')
    report_status_lbl = dlg.findChild(QLabel, 'reportStatusLabel')
    action_buttons = [view_btn, save_pdf_btn, save_excel_btn]
    date_field_labels = [from_label, to_label]
    fc = FieldCoordinator(dlg)

    def _set_report_status(message: str, *, ok: bool) -> None:
        try:
            ui_feedback.set_status_label(report_status_lbl, message, ok=ok, duration=STATUS_LABEL_DURATION_MS)
        except Exception:
            pass

    def _set_report_warning(message: str) -> None:
        try:
            ui_feedback.set_warning_status_label(report_status_lbl, message, duration=STATUS_LABEL_DURATION_MS)
        except Exception:
            pass

    def _link_report_status(widget) -> None:
        if widget is None:
            return
        try:
            fc.add_link(widget, target_map={}, status_label=report_status_lbl)
        except Exception:
            pass

    for _widget in (from_date, to_date, today, date_range, view_btn, save_pdf_btn, save_excel_btn, reset_btn, report_cancel_btn):
        _link_report_status(_widget)

    # report cancel button.
    try:
        if report_cancel_btn is not None:
            def _on_report_cancel():
                try:
                    set_dialog_info(dlg, 'Report selection cancelled.', duration=MAIN_STATUS_DURATION_MS)
                except Exception:
                    pass
                try:
                    if callable(orig_reject):
                        orig_reject()
                    else:
                        dlg.reject()
                except Exception:
                    pass

            report_cancel_btn.clicked.connect(_on_report_cancel)
    except Exception:
        pass

    normal_date_mode = {'radio': 'today'}

    def _set_report_gate_locked(locked: bool) -> None:
        set_buttons_locked(action_buttons, bool(locked))
        try:
            if save_excel_btn is not None:
                save_excel_btn.setProperty('reportGateLocked', bool(locked))
        except Exception:
            pass

    def _selected_normal_date_mode() -> str:
        try:
            if date_range is not None and date_range.isChecked() and date_range.isEnabled():
                return 'date_range'
        except Exception:
            pass
        return 'today'

    def _remember_normal_date_mode() -> None:
        try:
            if inactivity is not None and inactivity.isChecked():
                return
        except Exception:
            pass
        normal_date_mode['radio'] = _selected_normal_date_mode()

    def _apply_date_gate_state() -> None:
        try:
            date_range_active = bool(
                date_range is not None
                and date_range.isEnabled()
                and date_range.isChecked()
            )
        except Exception:
            date_range_active = False

        labels_locked = not date_range_active
        for lbl in date_field_labels:
            set_locked_property(lbl, labels_locked)

        set_dateedit_locked(from_date, not date_range_active)
        set_dateedit_locked(to_date, not date_range_active)
        _set_report_gate_locked(False)

    def _restore_normal_date_mode() -> None:
        try:
            if normal_date_mode.get('radio') == 'date_range' and date_range is not None and date_range.isEnabled():
                date_range.setChecked(True)
            elif today is not None:
                today.setChecked(True)
        except Exception:
            pass

    def _sync_report_mode_state() -> None:
        """Shared report-mode sync for the report/date gating state."""
        try:
            if inactivity is not None and inactivity.isChecked():
                normal_date_mode['radio'] = _selected_normal_date_mode()
                if date_range is not None:
                    date_range.setEnabled(False)
                    set_locked_property(date_range, True)
                if today is not None:
                    today.setText('Upto Today')
                    today.setChecked(True)
            else:
                if date_range is not None:
                    date_range.setEnabled(is_admin_user)
                    set_locked_property(date_range, not is_admin_user)
                    _restore_normal_date_mode()
                if today is not None:
                    today.setText('Today')

            _apply_date_gate_state()
            _defer_focus(view_btn)
        except Exception:
            pass

    if all((today, date_range, from_date, to_date)):
        class _ReportDateEnterFilter(QObject):
            def eventFilter(self, obj, event):
                try:
                    if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
                        from_line = from_date.lineEdit() if from_date is not None else None
                        to_line = to_date.lineEdit() if to_date is not None else None
                        if obj is from_date or obj is from_line:
                            clamp_date_range_bounds(from_date, to_date)
                            to_date.setFocus(Qt.OtherFocusReason)
                            return True
                        if obj is to_date or obj is to_line:
                            clamp_date_range_bounds(from_date, to_date)
                            _defer_focus(view_btn)
                            return True
                except Exception:
                    pass
                return False

        _date_enter_filter = _ReportDateEnterFilter(dlg)
        dlg._report_date_enter_filter = _date_enter_filter

        try:
            from_date.dateChanged.connect(lambda _date: (clamp_date_range_bounds(from_date, to_date), _apply_date_gate_state()))
            to_date.dateChanged.connect(lambda _date: (clamp_date_range_bounds(from_date, to_date), _apply_date_gate_state()))
            today.toggled.connect(lambda checked: checked and (_remember_normal_date_mode(), _apply_date_gate_state(), _defer_focus(view_btn)))
            date_range.toggled.connect(lambda checked: checked and (_remember_normal_date_mode(), _apply_date_gate_state(), _defer_focus(from_date)))
            from_date.installEventFilter(_date_enter_filter)
            to_date.installEventFilter(_date_enter_filter)
            if from_date.lineEdit() is not None:
                from_date.lineEdit().installEventFilter(_date_enter_filter)
            if to_date.lineEdit() is not None:
                to_date.lineEdit().installEventFilter(_date_enter_filter)
        except Exception as e:
            try:
                log_error_message(f"Failed to init report date gate wiring: {e}")
            except Exception:
                pass

        try:
            _sync_report_mode_state()
        except Exception:
            pass

    def _report_save_status(file_path, kind: str) -> None:
        try:
            out_dir = Path(file_path).parent if file_path is not None else ''
            message = f'{kind} file exported to {out_dir}'
            _report_success_status(message)
        except Exception:
            pass

    def _report_success_status(message: str) -> None:
        try:
            def _apply_success() -> None:
                try:
                    _set_report_status(message, ok=True)
                    set_dialog_info(dlg, message, duration=MAIN_STATUS_DURATION_MS)
                except Exception:
                    pass

            QTimer.singleShot(50, _apply_success)
        except Exception:
            pass 

    def _handle_pdf_error(message: str) -> None:
        """Updates UI with error status."""
        _set_report_status(message, ok=False)

    def _handle_viewer_error(message: str) -> None:
        """Updates UI with error status for viewer."""
        _set_report_status(message, ok=False)

    def _handle_export_error(message: str, exc: Exception = None) -> None:
        """Helper to unify UI feedback and logging for export failures.

        Shows a failure message in the status label and logs the error with
        exception context when available.
        """
        try:
            _set_report_status(message, ok=False)
        except Exception:
            pass
        try:
            if exc is not None:
                log_error_message(f"Failed to save report Excel: {message} -- {repr(exc)}")
            else:
                log_error_message(f"Failed to save report Excel: {message}")
        except Exception:
            pass

    def _pdf_too_large_message() -> str:
        return getattr(report_exports, 'PDF_TOO_LARGE_MESSAGE', 'PDF export skipped: the selected report is too large to render safely.')

    try:
        _apply_role_default_state(dlg, is_admin=is_admin_user)
        normal_date_mode['radio'] = 'today'
        init_date_range_bounds(from_date, to_date)
        try:
            from_date.setCalendarPopup(True)
            to_date.setCalendarPopup(True)
        except Exception:
            pass
        _sync_report_mode_state()

        # Default landing focus for both Admin and Staff.
        if view_btn is not None and view_btn.isEnabled():
            _defer_focus(view_btn)
    except Exception as e:
        try:
            log_error_message(f"Failed to apply report role defaults: {e}")
        except Exception:
            pass

    def _reset_report_selection() -> None:
        try:
            normal_date_mode['radio'] = 'today'
            _apply_role_default_state(dlg, is_admin=is_admin_user)
            if today is not None:
                today.setText('Today')
            init_date_range_bounds(from_date, to_date)
            _sync_report_mode_state()
            _defer_focus(view_btn)
        except Exception as e:
            try:
                log_error_message(f"Failed to reset report selection: {e}")
            except Exception:
                pass

    def _on_export_pdf_clicked() -> None:
        try:
            rpt = _current_report_type(dlg)
            if not rpt:
                _set_report_warning('Select a report type first.')
                return

            # 1. Data Preparation
            try:
                data = _build_report_data(dlg, host_window, rpt)
            except Exception as e:
                _handle_pdf_error(f'Report data build failed: {e}')
                return

            # 2. Validation (Pre-export check)
            allowed, blocked_message = report_exports.validate_pdf_export(rpt, data)
            if not allowed:
                msg = blocked_message or _pdf_too_large_message()
                _set_report_warning(msg)
                return

            # 3. Export Execution
            out_path = report_exports.save_report_pdf(rpt, report_data=data)

            # 4. Success UI Updates
            _report_save_status(out_path, 'PDF report')
            _defer_focus(save_pdf_btn)

        except Exception as e:
            # 5. Centralized Exception Handling
            err_msg = str(e).lower()
            if 'too large' in err_msg or 'render safely' in err_msg:
                msg = _pdf_too_large_message()
                _set_report_warning(msg)
            else:
                _handle_pdf_error(f'PDF export failed: {e}')

    def _on_export_excel_clicked() -> None:
        try:
            rpt = _current_report_type(dlg)
            if not rpt:
                _set_report_warning('Select a report type first.')
                return
            if rpt == 'chart':
                message = 'Chart saving to Excel is not available.'
                _set_report_warning(message)
                return
            try:
                data = _build_report_data(dlg, host_window, rpt)
            except Exception as e:
                _handle_export_error(f'Report data build failed: {e}', e)
                return
            out_path = report_exports.save_report_xlsx(rpt, report_data=data)
            _report_save_status(out_path, 'Excel report')
            _defer_focus(save_excel_btn)
        except Exception as e:
            try:
                error_str = str(e).lower()
                message = _friendly_openpyxl_message() if 'openpyxl' in error_str else f'Excel export failed: {e}'
                _handle_export_error(message, e)
            except Exception:
                pass

    def _on_view_report_clicked() -> None:
        try:
            rpt = _current_report_type(dlg)
            if not rpt:
                _set_report_warning('Select a report type first.')
                return

            # 1. Data Preparation
            try:
                data = _build_report_data(dlg, host_window, rpt)
            except Exception as e:
                _handle_viewer_error(f'Report data build failed: {e}')
                return

            # 2. Viewer Execution
            report_viewers.open_report_viewer(dlg, report_type=rpt, report_data=data)

            # 3. Success UI Updates
            _report_success_status('Report viewer opened successfully.')
            _defer_focus(view_btn)

        except Exception as e:
            # 4. Centralized Exception Handling
            _handle_viewer_error(f'Report viewer failed: {e}')

    try:
        if reset_btn is not None:
            reset_btn.clicked.connect(_reset_report_selection)
    except Exception:
        pass

    try:
        if view_btn is not None:
            view_btn.clicked.connect(_on_view_report_clicked)
    except Exception:
        pass

    try:
        if save_pdf_btn is not None:
            save_pdf_btn.clicked.connect(_on_export_pdf_clicked)
    except Exception:
        pass

    try:
        if save_excel_btn is not None:
            save_excel_btn.clicked.connect(_on_export_excel_clicked)
    except Exception:
        pass

    try:
        # Use the current QPushButton selectors defined in the UI.
        detail = dlg.findChild(QPushButton, 'salesReportBtn')
        summary = dlg.findChild(QPushButton, 'insightReportBtn')
        chart = dlg.findChild(QPushButton, 'chartReportBtn') or dlg.findChild(QRadioButton, 'chartReportRadioBtn')
        inactivity = dlg.findChild(QPushButton, 'inactivityReportBtn') or dlg.findChild(QRadioButton, 'inactivityReportRadioBtn')

        selectors = [w for w in (detail, summary, chart, inactivity) if w is not None]

        # Ensure QPushButton selectors are checkable and wire exclusive behavior
        for w in selectors:
            try:
                if isinstance(w, QPushButton):
                    w.setCheckable(True)
            except Exception:
                pass

        def _on_selector_checked(selected_widget):
            try:
                for w in selectors:
                    if w is None or w is selected_widget:
                        continue
                    try:
                        w.blockSignals(True)
                        # Uncheck only if widget supports setChecked
                        try:
                            w.setChecked(False)
                        except Exception:
                            pass
                        w.blockSignals(False)
                    except Exception:
                        pass
                _sync_report_mode_state()
            except Exception:
                pass

        for w in selectors:
            try:
                w.toggled.connect(lambda checked, obj=w: checked and _on_selector_checked(obj))
            except Exception:
                pass

        for _widget in selectors:
            _link_report_status(_widget)
    except Exception:
        pass

    # Return QDialog for DialogWrapper to execute
    return dlg
