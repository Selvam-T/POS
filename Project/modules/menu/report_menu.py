# modules/menu/report_menu.py

import os
from PyQt5 import uic
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QRadioButton, QDateEdit, QLabel, QWidget
from modules.ui_utils.error_logger import log_error_message
from modules.ui_utils.dialog_utils import set_dialog_info
from modules.date_time.date_gating import DateRangeGateController, set_locked_property

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
QSS_PATH = os.path.join(ASSETS_DIR, 'dialog.qss')

# Placeholder viewer size policy by selected report type.
REPORT_VIEWER_SIZES = {
    'detail': (900, 620),
    'summary': (760, 520),
    'chart': (980, 680),
    'inactivity': (720, 500),
}
DEFAULT_REPORT_VIEWER_SIZE = (760, 520)


def _apply_role_default_state(dlg: QDialog, *, is_admin: bool) -> None:
    """Apply role defaults and permissions."""
    detail = dlg.findChild(QRadioButton, 'detailReportRadioBtn')
    summary = dlg.findChild(QRadioButton, 'summaryReportRadioBtn')
    chart = dlg.findChild(QRadioButton, 'chartReportRadioBtn')
    inactivity = dlg.findChild(QRadioButton, 'inactivityReportRadioBtn')
    today = dlg.findChild(QRadioButton, 'todayRadioBtn')
    date_range = dlg.findChild(QRadioButton, 'dateRangeRadioBtn')

    if not all((detail, summary, chart, inactivity, today, date_range)):
        return

    # Role permissions for report/date mode radios.
    detail.setEnabled(is_admin)
    chart.setEnabled(is_admin)
    inactivity.setEnabled(is_admin)
    date_range.setEnabled(is_admin)

    # Role-aware defaults.
    (detail if is_admin else summary).setChecked(True)
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


def _current_report_type(dlg: QDialog) -> str:
    """Return normalized report type based on selected report radio."""
    try:
        detail = dlg.findChild(QRadioButton, 'detailReportRadioBtn')
        summary = dlg.findChild(QRadioButton, 'summaryReportRadioBtn')
        chart = dlg.findChild(QRadioButton, 'chartReportRadioBtn')
        inactivity = dlg.findChild(QRadioButton, 'inactivityReportRadioBtn')
        if detail is not None and detail.isChecked():
            return 'detail'
        if summary is not None and summary.isChecked():
            return 'summary'
        if chart is not None and chart.isChecked():
            return 'chart'
        if inactivity is not None and inactivity.isChecked():
            return 'inactivity'
    except Exception:
        pass
    return 'summary'


def _open_report_viewer(parent_dlg: QDialog, *, report_type: str) -> None:
    """Open a child modal placeholder viewer above report dialog with dimmed parent."""
    rpt = str(report_type or 'summary').strip().lower()
    size = REPORT_VIEWER_SIZES.get(rpt, DEFAULT_REPORT_VIEWER_SIZE)
    title = f"{rpt.capitalize()} Report Viewer"

    overlay = None
    try:
        overlay = QWidget(parent_dlg)
        overlay.setGeometry(parent_dlg.rect())
        overlay.setStyleSheet('background-color: rgba(0, 0, 0, 120);')
        overlay.show()
        overlay.raise_()
    except Exception:
        overlay = None

    viewer = QDialog(parent_dlg)
    viewer.setModal(True)
    viewer.setWindowModality(Qt.WindowModal)
    viewer.setWindowTitle(title)
    viewer.resize(int(size[0]), int(size[1]))

    lay = QVBoxLayout(viewer)
    lay.setContentsMargins(16, 16, 16, 16)
    lay.setSpacing(12)

    msg = QLabel('No content available.', viewer)
    msg.setAlignment(Qt.AlignCenter)
    msg.setWordWrap(True)
    lay.addWidget(msg)

    close_btn = QPushButton('Close', viewer)
    close_btn.clicked.connect(viewer.accept)
    lay.addWidget(close_btn)

    _defer_focus(close_btn)
    viewer.exec_()

    try:
        if overlay is not None:
            overlay.hide()
            overlay.deleteLater()
    except Exception:
        pass


def launch_reports_dialog(host_window):
    """Open Reports dialog (ui/report_menu.ui) as a modal frameless panel.
    
    DialogWrapper handles: overlay, sizing, centering, scanner blocking, cleanup, and focus restoration.
    This function only creates and returns the QDialog.
    
    Args:
        host_window: Main window instance
    
    Returns:
        QDialog instance ready for DialogWrapper.open_dialog_scanner_blocked() to execute
    """
    ui_path = os.path.join(UI_DIR, 'report_menu.ui')
    if not os.path.exists(ui_path):
        return None

    # Load the UI file as a QWidget
    content = uic.loadUi(ui_path)
    # Wrap in QDialog if needed
    if isinstance(content, QDialog):
        dlg = content
    else:
        dlg = QDialog(host_window)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(content)

    # Frameless + modal
    dlg.setParent(host_window)
    dlg.setModal(True)
    dlg.setWindowModality(Qt.ApplicationModal)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
    is_admin_user = bool(getattr(host_window, 'current_is_admin', False))

    # Apply stylesheet
    if os.path.exists(QSS_PATH):
        try:
            with open(QSS_PATH, 'r', encoding='utf-8') as f:
                dlg.setStyleSheet(f.read())
        except Exception as e:
            try:
                log_error_message(f"Failed to load dialog.qss: {e}")
            except Exception:
                pass

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
                        set_dialog_info(dlg, 'Report dialog closed.', duration=3000)
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
    action_buttons = [view_btn, save_pdf_btn, save_excel_btn]
    date_field_labels = [from_label, to_label]

    # Match admin-menu behavior for report cancel button.
    try:
        if report_cancel_btn is not None:
            def _on_report_cancel():
                try:
                    set_dialog_info(dlg, 'Report selection cancelled.', duration=3000)
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

    gate_controller = None
    if all((today, date_range, from_date, to_date)):
        def _focus_first_action() -> None:
            _defer_focus(view_btn)

        try:
            gate_controller = DateRangeGateController(
                dlg,
                today_radio=today,
                date_range_radio=date_range,
                from_date_edit=from_date,
                to_date_edit=to_date,
                action_buttons=action_buttons,
                field_labels=date_field_labels,
                on_actions_unlocked=_focus_first_action,
            )
            dlg._report_date_gate_controller = gate_controller
        except Exception as e:
            try:
                log_error_message(f"Failed to init report date gate controller: {e}")
            except Exception:
                pass

    try:
        _apply_role_default_state(dlg, is_admin=is_admin_user)
        # Initialize date/actions gating after role defaults are applied.
        if gate_controller is not None:
            gate_controller.init_date_bounds()
            gate_controller.apply_state()
        else:
            # Safe fallback if gate controller is unavailable.
            for btn in action_buttons:
                set_locked_property(btn, False)

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
            _apply_role_default_state(dlg, is_admin=is_admin_user)
            if gate_controller is not None:
                gate_controller.init_date_bounds()
                gate_controller.apply_state()
            else:
                for btn in action_buttons:
                    set_locked_property(btn, False)
            _defer_focus(view_btn)
        except Exception as e:
            try:
                log_error_message(f"Failed to reset report selection: {e}")
            except Exception:
                pass

    def _on_view_report_clicked() -> None:
        try:
            rpt = _current_report_type(dlg)
            _open_report_viewer(dlg, report_type=rpt)
            _defer_focus(view_btn)
        except Exception as e:
            try:
                log_error_message(f"Failed to open report viewer: {e}")
            except Exception:
                pass

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

    # Return QDialog for DialogWrapper to execute
    return dlg
