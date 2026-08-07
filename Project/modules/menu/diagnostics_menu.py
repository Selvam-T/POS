"""Diagnostics menu dialog shell."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QCheckBox, QLabel, QPushButton

import config
from modules.menu.diagnostics import (
    export_diagnostic_report,
    run_category_integrity_diagnostics,
    run_device_readiness_diagnostics,
    run_database_diagnostics,
    run_product_cache_diagnostics,
    run_product_code_diagnostics,
    run_product_derived_ui_diagnostics,
    run_product_name_diagnostics,
    run_product_cost_price_diagnostics,
    run_runtime_assets_diagnostics,
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
    set_dialog_main_status_max,
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
                "cost_price": (QCheckBox, "missingCostPriceCheckBox"),
                "quality": (QCheckBox, "productDerivedUiCheckBox"),
                "categories": (QCheckBox, "categoryIntegrityCheckBox"),
                "runtime": (QCheckBox, "runtimeAssetsCheckBox"),
                "devices": (QCheckBox, "deviceReadinessCheckBox"),
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
    widgets["codes"].setChecked(False)
    widgets["codes"].setEnabled(True)
    widgets["codes"].setFocusPolicy(Qt.StrongFocus)
    widgets["names"].setChecked(False)
    widgets["names"].setEnabled(True)
    widgets["names"].setFocusPolicy(Qt.StrongFocus)
    widgets["cost_price"].setChecked(False)
    widgets["cost_price"].setEnabled(True)
    widgets["cost_price"].setFocusPolicy(Qt.StrongFocus)
    widgets["quality"].setChecked(False)
    widgets["quality"].setEnabled(True)
    widgets["quality"].setFocusPolicy(Qt.StrongFocus)
    widgets["categories"].setChecked(False)
    widgets["categories"].setEnabled(True)
    widgets["categories"].setFocusPolicy(Qt.StrongFocus)
    widgets["runtime"].setChecked(False)
    widgets["runtime"].setEnabled(True)
    widgets["runtime"].setFocusPolicy(Qt.StrongFocus)
    widgets["devices"].setChecked(False)
    widgets["devices"].setEnabled(True)
    widgets["devices"].setFocusPolicy(Qt.StrongFocus)
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
            widgets["codes"],
            widgets["names"],
            widgets["cost_price"],
            widgets["quality"],
            widgets["categories"],
            widgets["runtime"],
            widgets["devices"],
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
            for checkbox in (
                widgets["database"],
                widgets["cache"],
                widgets["codes"],
                widgets["names"],
                widgets["cost_price"],
                widgets["quality"],
                widgets["categories"],
                widgets["runtime"],
                widgets["devices"],
            )
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
        if widgets["codes"].isChecked():
            results["product_codes"] = run_product_code_diagnostics()
        if widgets["names"].isChecked():
            results["product_names"] = run_product_name_diagnostics()
        if widgets["cost_price"].isChecked():
            results["product_cost_prices"] = run_product_cost_price_diagnostics()
        if widgets["quality"].isChecked():
            results["product_derived_ui"] = (
                run_product_derived_ui_diagnostics(
                    product_cache.PRODUCT_CACHE
                )
            )
        if widgets["categories"].isChecked():
            results["category_integrity"] = (
                run_category_integrity_diagnostics()
            )
        if widgets["runtime"].isChecked():
            results["runtime_assets"] = run_runtime_assets_diagnostics()
        if widgets["devices"].isChecked():
            results["device_readiness"] = (
                run_device_readiness_diagnostics(host_window=parent)
            )
        dlg.diagnostics_result = results

        statuses = {
            str(result.get("status") or "FAIL") for result in results.values()
        }
        status = (
            "FAIL"
            if "FAIL" in statuses
            else ("WARNING" if "WARNING" in statuses else "PASS")
        )
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

        message = f"Diagnostic report saved to {report_path.parent}"
        if status == "FAIL":
            for key, non_pass_result in (
                (key, value)
                for key, value in results.items()
                if str(value.get("status") or "FAIL") == "FAIL"
            ):
                try:
                    log_error_message(
                        f"diagnostics_menu: {key} diagnostic "
                        f"{str(non_pass_result.get('status') or 'FAIL').lower()}: "
                        + "; ".join(
                            str(issue)
                            for issue in (non_pass_result.get("issues") or [])
                        )
                    )
                except Exception:
                    pass

        if status == "FAIL":
            set_dialog_error(
                dlg,
                message,
                duration=config.MAIN_STATUS_ERROR_DURATION_MS,
            )
        elif status == "WARNING":
            set_dialog_main_status_max(
                dlg,
                message,
                level="warning",
                duration=config.MAIN_STATUS_LONG_DURATION_MS,
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
