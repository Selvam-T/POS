from pathlib import Path

from modules.menu.diagnostics.report_formatter import format_diagnostic_report
from modules.menu.diagnostics.runtime_assets_check import (
    analyze_runtime_assets,
    run_runtime_assets_diagnostics,
)


def _layout(tmp_path):
    app = tmp_path / "Project"
    client = tmp_path
    ui = app / "ui"
    qss = app / "assets" / "qss"
    icons = app / "assets" / "icons"
    database = tmp_path / "db" / "pos.db"
    export = tmp_path / "exports" / "Diagnostic"
    for folder in (ui, qss, icons, database.parent):
        folder.mkdir(parents=True, exist_ok=True)
    database.write_bytes(b"test")
    return app, client, ui, qss, icons, database, export


def test_complete_runtime_layout_passes_with_informational_disk_space(
    tmp_path,
):
    app, client, ui, qss, icons, database, export = _layout(tmp_path)
    (ui / "required.ui").write_text("<ui/>", encoding="utf-8")
    (qss / "required.qss").write_text("", encoding="utf-8")
    (icons / "required.svg").write_text("<svg/>", encoding="utf-8")

    analysis = analyze_runtime_assets(
        app_dir=app,
        client_root=client,
        ui_dir=ui,
        qss_dir=qss,
        icons_dir=icons,
        database_path=database,
        export_path=export,
        is_packaged=False,
        required_ui_files=("required.ui",),
        required_qss_files=("required.qss",),
        required_icon_files=("required.svg",),
        icon_validator=lambda _path: True,
    )

    assert analysis["missing_ui_files"] == []
    assert analysis["missing_qss_files"] == []
    assert analysis["missing_icon_files"] == []
    assert analysis["invalid_icon_files"] == []
    assert analysis["export_path_ready"] is True
    assert analysis["database_disk_free_bytes"] is not None
    assert analysis["export_disk_free_bytes"] is not None


def test_missing_and_qt_invalid_assets_are_reported(tmp_path, monkeypatch):
    app, client, ui, qss, icons, database, export = _layout(tmp_path)
    (icons / "invalid.svg").write_text("<svg/>", encoding="utf-8")
    monkeypatch.setattr(
        "modules.menu.diagnostics.runtime_assets_check.analyze_runtime_assets",
        lambda **_kwargs: {
            "app_dir_exists": True,
            "client_root_exists": True,
            "ui_dir_exists": True,
            "qss_dir_exists": True,
            "icons_dir_exists": True,
            "database_exists": True,
            "database_readable": True,
            "database_parent_writable": True,
            "export_path_is_directory": True,
            "export_path_ready": True,
            "missing_ui_files": ["missing.ui"],
            "missing_qss_files": ["missing.qss"],
            "missing_icon_files": ["missing.svg"],
            "invalid_icon_files": ["invalid.svg"],
        },
    )

    result = run_runtime_assets_diagnostics(
        database_path=database,
        export_path=export,
    )

    assert result["status"] == "WARNING"
    assert "Missing required UI files: 1" in result["issues"]
    assert "Icons that Qt cannot load: 1" in result["issues"]


def test_report_marks_disk_space_informational_and_omits_error_log_data():
    result = {
        "status": "PASS",
        "database_disk_free_bytes": 10,
        "export_disk_free_bytes": 20,
        "issues": [],
    }
    report = format_diagnostic_report({"runtime_assets": result})

    assert "DISK SPACE (INFORMATIONAL)" in report
    assert "Disk-space values do not affect diagnostic status." in report
    assert "Recent error count" not in report
    assert "Most recent error time" not in report
