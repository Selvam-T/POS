import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QCheckBox, QDialog, QLabel, QPushButton

from modules.menu import diagnostics_menu


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication([])
    return _APP


def _pass_result():
    return {
        "status": "PASS",
        "table_counts": {"Product_list": 10, "Category": 3},
        "issues": [],
    }


def test_ok_runs_and_exports_selected_diagnostic(monkeypatch, tmp_path):
    _app()
    report_path = tmp_path / "diagnostic_report.txt"
    calls = []

    monkeypatch.setattr(
        diagnostics_menu,
        "run_database_diagnostics",
        lambda: calls.append("run") or _pass_result(),
    )
    monkeypatch.setattr(
        diagnostics_menu,
        "export_diagnostic_report",
        lambda results: calls.append(("export", results)) or report_path,
    )

    dlg = diagnostics_menu.launch_diagnostics_dialog(None)
    dlg.findChild(QPushButton, "btnDiagnosticsOk").click()

    assert dlg.result() == QDialog.Accepted
    assert calls[0] == "run"
    assert calls[1][0] == "export"
    assert dlg.diagnostics_result["database"]["status"] == "PASS"
    assert dlg.diagnostics_report_path == str(report_path)
    assert dlg.main_status_msg == f"Diagnostic report saved to {report_path.parent}"
    assert dlg.main_status_is_error is False


def test_status_label_handles_missing_selection(monkeypatch):
    _app()
    monkeypatch.setattr(
        diagnostics_menu,
        "run_database_diagnostics",
        lambda: (_ for _ in ()).throw(
            AssertionError("Diagnostic should not run")
        ),
    )

    dlg = diagnostics_menu.launch_diagnostics_dialog(None)
    dlg.findChild(QCheckBox, "databaseIntegrityCheckBox").setChecked(False)
    dlg.findChild(QPushButton, "btnDiagnosticsOk").click()
    status = dlg.findChild(QLabel, "diagnosticStatusLabel")

    assert dlg.result() == 0
    assert status.text() == "Select at least one diagnostic check."
    assert status.property("status") == "error"


def test_cache_only_selection_uses_live_product_cache(monkeypatch, tmp_path):
    _app()
    report_path = tmp_path / "cache_report.txt"
    live_cache = {"1001": ("Test Product", 1.5, "Each", "Other")}
    observed = []

    monkeypatch.setattr(
        diagnostics_menu.product_cache,
        "PRODUCT_CACHE",
        live_cache,
    )
    monkeypatch.setattr(
        diagnostics_menu,
        "run_database_diagnostics",
        lambda: (_ for _ in ()).throw(
            AssertionError("Database check was not selected")
        ),
    )
    monkeypatch.setattr(
        diagnostics_menu,
        "run_product_cache_diagnostics",
        lambda cache: observed.append(cache) or {
            "status": "PASS",
            "issues": [],
        },
    )
    monkeypatch.setattr(
        diagnostics_menu,
        "export_diagnostic_report",
        lambda results: report_path,
    )

    dlg = diagnostics_menu.launch_diagnostics_dialog(None)
    dlg.findChild(QCheckBox, "databaseIntegrityCheckBox").setChecked(False)
    cache_box = dlg.findChild(QCheckBox, "productCacheCheckBox")
    assert cache_box.isEnabled()
    cache_box.setChecked(True)
    dlg.findChild(QPushButton, "btnDiagnosticsOk").click()

    assert dlg.result() == QDialog.Accepted
    assert observed == [live_cache]
    assert set(dlg.diagnostics_result) == {"product_cache"}


def test_product_code_only_selection_runs_third_check(monkeypatch, tmp_path):
    _app()
    report_path = tmp_path / "code_report.txt"
    observed = []
    monkeypatch.setattr(
        diagnostics_menu,
        "run_product_code_diagnostics",
        lambda: observed.append("codes") or {
            "status": "WARNING",
            "issues": ["One suspicious pair"],
        },
    )
    monkeypatch.setattr(
        diagnostics_menu,
        "export_diagnostic_report",
        lambda results: report_path,
    )

    dlg = diagnostics_menu.launch_diagnostics_dialog(None)
    dlg.findChild(QCheckBox, "databaseIntegrityCheckBox").setChecked(False)
    codes_box = dlg.findChild(QCheckBox, "productCodeCheckBox")
    assert codes_box.isEnabled()
    codes_box.setChecked(True)
    dlg.findChild(QPushButton, "btnDiagnosticsOk").click()

    assert dlg.result() == QDialog.Accepted
    assert observed == ["codes"]
    assert set(dlg.diagnostics_result) == {"product_codes"}
    assert dlg.main_status_is_error is False
    assert dlg._main_status_severity == 1


def test_export_failure_rejects_dialog_and_reports_error(monkeypatch):
    _app()
    logged = []

    monkeypatch.setattr(
        diagnostics_menu,
        "run_database_diagnostics",
        _pass_result,
    )

    def _fail_export(_results):
        raise OSError("Export folder is unavailable")

    monkeypatch.setattr(
        diagnostics_menu,
        "export_diagnostic_report",
        _fail_export,
    )
    monkeypatch.setattr(
        diagnostics_menu,
        "log_exception_traceback_and_postclose_statusBar",
        lambda dlg, where, exc, **kwargs: (
            logged.append((where, str(exc))),
            diagnostics_menu.set_dialog_error(
                dlg,
                kwargs["user_message"],
                duration=kwargs["duration"],
            ),
        ),
    )

    dlg = diagnostics_menu.launch_diagnostics_dialog(None)
    dlg.findChild(QPushButton, "btnDiagnosticsOk").click()

    assert dlg.result() == QDialog.Rejected
    assert dlg.diagnostics_report_path is None
    assert "Diagnostic report export failed" in dlg.main_status_msg
    assert "Export folder is unavailable" in dlg.main_status_msg
    assert dlg.main_status_is_error is True
    assert logged == [
        ("diagnostics_menu export", "Export folder is unavailable")
    ]
