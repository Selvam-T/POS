# modules/menu/report_menu.py

import os
from PyQt5 import uic
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QRadioButton, QDateEdit, QLabel
from modules.ui_utils.error_logger import log_error_message
from modules.date_time.date_gating import DateRangeGateController, set_locked_property

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
QSS_PATH = os.path.join(ASSETS_DIR, 'dialog.qss')


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

    # Titlebar close (optional)
    try:
        xbtn: QPushButton = dlg.findChild(QPushButton, 'customCloseBtn')
        if xbtn:
            xbtn.clicked.connect(dlg.reject)
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
    action_buttons = [view_btn, save_pdf_btn, save_excel_btn]
    date_field_labels = [from_label, to_label]

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
        _apply_role_default_state(dlg, is_admin=bool(getattr(host_window, 'current_is_admin', False)))
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

    # Return QDialog for DialogWrapper to execute
    return dlg
