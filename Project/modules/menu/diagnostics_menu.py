"""Diagnostics menu dialog shell."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QCheckBox, QLabel, QPushButton

import config
from modules.menu.diagnostics import (
    export_diagnostic_report,
    run_database_diagnostics,
    run_product_cache_diagnostics,
)
from modules.db_operation import product_cache
from modules.runtime.paths import stylesheet_path, ui_path
from modules.ui_utils import ui_feedback
from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui,
    build_error_fallback_dialog,
    log_exception_traceback_and_postclose_statusBar,
    require_widgets,
    set_dialog_error,
    set_dialog_info,
)
from modules.ui_utils.error_logger import log_error_message
from modules.ui_utils.focus_utils import FocusGate, set_initial_focus


UI_PATH = ui_path("diagnostics_menu.ui")
QSS_PATH = stylesheet_path("dialog.qss")


def launch_diagnostics_dialog(parent=None):
    """Build the diagnostics selection dialog.

    Selected diagnostics run and are exported as a UTF-8 text report.
    """
    dlg = build_dialog_from_ui(
        UI_PATH,
        host_window=parent,
        dialog_name="Diagnostics menu",
        qss_path=QSS_PATH,
    )
    if not dlg:
        return build_error_fallback_dialog(parent, "Diagnostics menu", QSS_PATH)

    try:
        widgets = require_widgets(
            dlg,
            {
                "database": (QCheckBox, "databaseIntegrityCheckBox"),
                "cache": (QCheckBox, "productCacheCheckBox"),
                "codes": (QCheckBox, "productCodeCheckBox"),
                "names": (QCheckBox, "duplicateNamesCheckBox"),
                "quality": (QCheckBox, "productQualityCheckBox"),
                "categories": (QCheckBox, "categoryIntegrityCheckBox"),
                "runtime": (QCheckBox, "runtimeAssetsCheckBox"),
                "status": (QLabel, "diagnosticStatusLabel"),
                "ok": (QPushButton, "btnDiagnosticsOk"),
                "cancel": (QPushButton, "btnDiagnosticsCancel"),
                "close": (QPushButton, "customCloseBtn"),
            },
        )
    except Exception as exc:
        log_error_message(f"diagnostics_menu: require_widgets failed: {exc}")
        dlg.deleteLater()
        return build_error_fallback_dialog(parent, "Diagnostics menu", QSS_PATH)

    widgets["database"].setChecked(True)
    widgets["cache"].setChecked(False)
    widgets["cache"].setEnabled(True)
    widgets["cache"].setFocusPolicy(Qt.StrongFocus)
    for key in ("codes", "names", "quality", "categories", "runtime"):
        widgets[key].setChecked(False)
        widgets[key].setEnabled(False)
        widgets[key].setFocusPolicy(Qt.NoFocus)
    set_initial_focus(
        dlg,
        first_widget=widgets["database"],
        select_all=False,
    )

    dlg.diagnostics_result = {}
    dlg._diagnostics_running = False
    running_gate = FocusGate(
        [
            widgets["database"],
            widgets["cache"],
            widgets["ok"],
            widgets["cancel"],
            widgets["close"],
        ],
        lock_enabled=True,
    )
    dlg._diagnostics_running_gate = running_gate

    def _close(message: str, *, accepted: bool) -> None:
        set_dialog_info(dlg, message)
        if accepted:
            dlg.accept()
        else:
            dlg.reject()

    def _run_selected() -> None:
        if dlg._diagnostics_running:
            return
        if not any(
            checkbox.isChecked()
            for checkbox in (widgets["database"], widgets["cache"])
        ):
            ui_feedback.set_status_label(
                widgets["status"],
                "Select at least one diagnostic check.",
                ok=False,
                duration=config.MAIN_STATUS_ERROR_DURATION_MS,
            )
            return

        dlg._diagnostics_running = True
        running_gate.lock()
        widgets["ok"].setText("RUNNING...")
        ui_feedback.set_warning_status_label(
            widgets["status"],
            "Diagnostics running...",
            duration=config.PERSISTENT_DURATION_MS,
        )
        QApplication.processEvents()

        results = {}
        if widgets["database"].isChecked():
            results["database"] = run_database_diagnostics()
        if widgets["cache"].isChecked():
            results["product_cache"] = run_product_cache_diagnostics(
                product_cache.PRODUCT_CACHE
            )
        dlg.diagnostics_result = results

        failed_results = [
            result
            for result in results.values()
            if str(result.get("status") or "FAIL") != "PASS"
        ]
        status = "FAIL" if failed_results else "PASS"
        try:
            report_path = export_diagnostic_report(dlg.diagnostics_result)
            dlg.diagnostics_report_path = str(report_path)
        except Exception as exc:
            dlg.diagnostics_report_path = None
            log_exception_traceback_and_postclose_statusBar(
                dlg,
                "diagnostics_menu export",
                exc,
                user_message=f"Diagnostic report export failed: {exc}",
                level="error",
                duration=config.MAIN_STATUS_ERROR_DURATION_MS,
            )
            dlg.reject()
            return

        if status == "PASS":
            message = f"Diagnostic report saved to {report_path.parent}"
            is_error = False
        else:
            for key, failed_result in (
                (key, value)
                for key, value in results.items()
                if str(value.get("status") or "FAIL") != "PASS"
            ):
                try:
                    log_error_message(
                        f"diagnostics_menu: {key} diagnostic failed: "
                        + "; ".join(
                            str(issue)
                            for issue in (failed_result.get("issues") or [])
                        )
                    )
                except Exception:
                    pass
            message = f"Diagnostic report saved to {report_path.parent}"
            is_error = True

        if is_error:
            set_dialog_error(
                dlg,
                message,
                duration=config.MAIN_STATUS_ERROR_DURATION_MS,
            )
        else:
            set_dialog_info(
                dlg,
                message,
                duration=config.MAIN_STATUS_LONG_DURATION_MS,
            )
        dlg.accept()

    widgets["ok"].clicked.connect(_run_selected)
    widgets["cancel"].clicked.connect(
        lambda: _close("Diagnostics closed.", accepted=False)
    )
    widgets["close"].clicked.connect(
        lambda: _close("Diagnostics closed.", accepted=False)
    )

    return dlg
