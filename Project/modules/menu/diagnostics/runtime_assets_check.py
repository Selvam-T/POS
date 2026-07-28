"""Runtime filesystem, UI, stylesheet, icon, and export-path diagnostic."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from time import perf_counter
from typing import Callable, Sequence

from PyQt5.QtGui import QIcon

import config
from modules.db_operation.sqlite_runtime import get_db_path
from modules.menu.diagnostics.common import timestamp
from modules.menu.diagnostics.report_exporter import DIAGNOSTIC_EXPORT_ROOT


REQUIRED_UI_FILES = (
    "admin_menu.ui",
    "clear_cart.ui",
    "diagnostics_menu.ui",
    "greeting_menu.ui",
    "hold_sales.ui",
    "login.ui",
    "logout_menu.ui",
    "main_window.ui",
    "manual_entry.ui",
    "menu_frame.ui",
    "payment_frame.ui",
    "product_menu.ui",
    "receipt_menu.ui",
    "refund.ui",
    "report_menu.ui",
    "sales_frame.ui",
    "screen2.ui",
    "todo.ui",
    "vegetable_entry.ui",
    "vegetable_menu.ui",
    "vendor.ui",
    "view_hold.ui",
)
REQUIRED_QSS_FILES = ("dialog.qss", "main.qss", "sales.qss")
REQUIRED_ICON_FILES = (
    "admin.svg",
    "delete.svg",
    "delete_todo.svg",
    "device.svg",
    "diagnose.svg",
    "down_arrow.svg",
    "down_arrow_gray.svg",
    "eye_close.svg",
    "eye_open.svg",
    "greeting.svg",
    "logout.svg",
    "main_background.svg",
    "product.svg",
    "receipt.svg",
    "reports.svg",
    "vegetable.svg",
)


def _nearest_existing_path(path: Path) -> Path | None:
    candidate = path.resolve()
    while not candidate.exists():
        parent = candidate.parent
        if parent == candidate:
            return None
        candidate = parent
    return candidate


def _disk_free_bytes(path: Path) -> int | None:
    existing = _nearest_existing_path(path)
    if existing is None:
        return None
    try:
        return int(shutil.disk_usage(existing).free)
    except OSError:
        return None


def _default_icon_validator(path: Path) -> bool:
    return not QIcon(str(path)).isNull()


def analyze_runtime_assets(
    *,
    app_dir: str | Path,
    client_root: str | Path,
    ui_dir: str | Path,
    qss_dir: str | Path,
    icons_dir: str | Path,
    database_path: str | Path,
    export_path: str | Path,
    is_packaged: bool,
    required_ui_files: Sequence[str] = REQUIRED_UI_FILES,
    required_qss_files: Sequence[str] = REQUIRED_QSS_FILES,
    required_icon_files: Sequence[str] = REQUIRED_ICON_FILES,
    icon_validator: Callable[[Path], bool] = _default_icon_validator,
) -> dict:
    """Analyze resolved runtime paths without creating or modifying files."""
    app = Path(app_dir).resolve()
    client = Path(client_root).resolve()
    ui = Path(ui_dir).resolve()
    qss = Path(qss_dir).resolve()
    icons = Path(icons_dir).resolve()
    database = Path(database_path).resolve()
    export = Path(export_path).resolve()
    export_existing_parent = _nearest_existing_path(export)

    missing_ui_files = sorted(
        name for name in required_ui_files if not (ui / name).is_file()
    )
    missing_qss_files = sorted(
        name for name in required_qss_files if not (qss / name).is_file()
    )
    missing_icon_files = sorted(
        name for name in required_icon_files if not (icons / name).is_file()
    )
    invalid_icon_files = []
    for name in required_icon_files:
        path = icons / name
        if not path.is_file():
            continue
        try:
            if not icon_validator(path):
                invalid_icon_files.append(name)
        except Exception:
            invalid_icon_files.append(name)

    return {
        "is_packaged": bool(is_packaged),
        "app_dir": str(app),
        "client_root": str(client),
        "ui_dir": str(ui),
        "qss_dir": str(qss),
        "icons_dir": str(icons),
        "database_path": str(database),
        "database_parent": str(database.parent),
        "export_path": str(export),
        "export_existing_parent": (
            str(export_existing_parent) if export_existing_parent else ""
        ),
        "app_dir_exists": app.is_dir(),
        "client_root_exists": client.is_dir(),
        "ui_dir_exists": ui.is_dir(),
        "qss_dir_exists": qss.is_dir(),
        "icons_dir_exists": icons.is_dir(),
        "database_exists": database.is_file(),
        "database_readable": database.is_file()
        and os.access(database, os.R_OK),
        "database_parent_writable": database.parent.is_dir()
        and os.access(database.parent, os.W_OK),
        "export_path_exists": export.exists(),
        "export_path_is_directory": not export.exists() or export.is_dir(),
        "export_path_ready": bool(
            export_existing_parent
            and export_existing_parent.is_dir()
            and os.access(export_existing_parent, os.W_OK)
        ),
        "required_ui_total": len(required_ui_files),
        "missing_ui_files": missing_ui_files,
        "required_qss_total": len(required_qss_files),
        "missing_qss_files": missing_qss_files,
        "required_icon_total": len(required_icon_files),
        "missing_icon_files": missing_icon_files,
        "invalid_icon_files": sorted(invalid_icon_files),
        "database_disk_free_bytes": _disk_free_bytes(database.parent),
        "export_disk_free_bytes": _disk_free_bytes(export),
    }


def run_runtime_assets_diagnostics(
    *,
    database_path: str | Path | None = None,
    export_path: str | Path | None = None,
) -> dict:
    """Run runtime asset and path checks for the active POS layout."""
    started_clock = perf_counter()
    result = {
        "check": "Runtime assets and paths",
        "status": "FAIL",
        "started_at": timestamp(),
        "completed_at": None,
        "duration_seconds": 0.0,
        "issues": [],
    }
    try:
        analysis = analyze_runtime_assets(
            app_dir=config.APP_DIR,
            client_root=config.CLIENT_ROOT,
            ui_dir=config.UI_DIR,
            qss_dir=config.QSS_DIR,
            icons_dir=Path(config.ASSETS_DIR) / "icons",
            database_path=database_path or get_db_path(),
            export_path=export_path or DIAGNOSTIC_EXPORT_ROOT,
            is_packaged=config.IS_PACKAGED,
        )
        result.update(analysis)
        boolean_checks = (
            ("app_dir_exists", "Application directory is missing"),
            ("client_root_exists", "Client root is missing"),
            ("ui_dir_exists", "UI directory is missing"),
            ("qss_dir_exists", "QSS directory is missing"),
            ("icons_dir_exists", "Icons directory is missing"),
            ("database_exists", "Database file is missing"),
            ("database_readable", "Database file is not readable"),
            (
                "database_parent_writable",
                "Database parent folder is not writable",
            ),
            (
                "export_path_is_directory",
                "Diagnostic export path exists but is not a directory",
            ),
            (
                "export_path_ready",
                "Diagnostic export path cannot be created or written",
            ),
        )
        for key, issue in boolean_checks:
            if not result[key]:
                result["issues"].append(issue)
        for key, label in (
            ("missing_ui_files", "Missing required UI files"),
            ("missing_qss_files", "Missing required QSS files"),
            ("missing_icon_files", "Missing required icon files"),
            ("invalid_icon_files", "Icons that Qt cannot load"),
        ):
            if result[key]:
                result["issues"].append(f"{label}: {len(result[key])}")
        result["status"] = "WARNING" if result["issues"] else "PASS"
    except Exception as exc:
        result["issues"].append(
            f"{type(exc).__name__}: "
            f"{str(exc) or 'Runtime assets diagnostic failed'}"
        )
    finally:
        result["completed_at"] = timestamp()
        result["duration_seconds"] = round(perf_counter() - started_clock, 3)
    return result
