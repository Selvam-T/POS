"""Non-invasive device software and configuration readiness diagnostic."""

from __future__ import annotations

import importlib.util
import ipaddress
from pathlib import Path
from time import perf_counter

from PyQt5.QtGui import QGuiApplication

import config
from modules.menu.diagnostics.common import timestamp
from modules.runtime.paths import ui_path


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def _valid_ip(value: object) -> bool:
    try:
        ipaddress.ip_address(str(value or "").strip())
        return True
    except ValueError:
        return False


def _valid_port(value: object) -> bool:
    try:
        return 1 <= int(value) <= 65535
    except (TypeError, ValueError):
        return False


def analyze_device_readiness(
    *,
    host_window=None,
    screen_count: int | None = None,
) -> dict:
    """Inspect device configuration and runtime objects without device actions."""
    scanner_module_available = _module_available("modules.devices.scanner")
    pynput_available = _module_available("pynput")
    barcode_manager = (
        getattr(host_window, "barcode_manager", None)
        if host_window is not None
        else None
    )
    scanner = getattr(barcode_manager, "scanner", None)
    scanner_controller_state = (
        "INITIALIZED"
        if barcode_manager is not None and scanner is not None
        else ("NOT INITIALIZED" if host_window is not None else "NOT INSPECTED")
    )
    scanner_timing = getattr(config, "SCANNER_KEY_INTERVAL_SECONDS", None)
    try:
        scanner_timing_valid = float(scanner_timing) > 0
    except (TypeError, ValueError):
        scanner_timing_valid = False

    printer_enabled = bool(getattr(config, "ENABLE_PRINTER_PRINT", False))
    drawer_enabled = bool(getattr(config, "ENABLE_CASH_DRAWER", False))
    printer_ip = str(getattr(config, "PRINTER_IP", "") or "").strip()
    printer_port = getattr(config, "PRINTER_PORT", None)
    printer_ip_valid = _valid_ip(printer_ip)
    printer_port_valid = _valid_port(printer_port)
    escpos_available = _module_available("escpos")
    printer_module_available = _module_available(
        "modules.devices.printer_and_drawer"
    )

    drawer_pin = getattr(config, "CASH_DRAWER_PIN", None)
    drawer_timeout = getattr(config, "CASH_DRAWER_TIMEOUT", None)
    try:
        drawer_pin_valid = int(drawer_pin) in (2, 5)
    except (TypeError, ValueError):
        drawer_pin_valid = False
    try:
        drawer_timeout_valid = float(drawer_timeout) > 0
    except (TypeError, ValueError):
        drawer_timeout_valid = False

    display_enabled = bool(
        getattr(config, "CUSTOMER_DISPLAY_ENABLED", False)
    )
    display_test_mode = bool(
        getattr(config, "CUSTOMER_DISPLAY_TEST_MODE", False)
    )
    display_module_available = _module_available(
        "modules.customer_display.customer_display"
    )
    screen2_ui_available = Path(ui_path("screen2.ui")).is_file()
    screen_index = getattr(config, "CUSTOMER_SCREEN_INDEX", None)
    try:
        screen_index_valid = int(screen_index) >= 0
    except (TypeError, ValueError):
        screen_index_valid = False
    if screen_count is None:
        app = QGuiApplication.instance()
        detected_screens = len(app.screens()) if app is not None else 0
    else:
        detected_screens = max(0, int(screen_count))
    physical_second_display_detected = detected_screens >= 2

    printer_state = "DISABLED"
    if printer_enabled:
        printer_state = (
            "CONFIGURED"
            if (
                printer_ip_valid
                and printer_port_valid
                and escpos_available
                and printer_module_available
            )
            else "CONFIGURATION WARNING"
        )
    drawer_state = "DISABLED"
    if drawer_enabled:
        drawer_state = (
            "CONFIGURED"
            if (
                printer_ip_valid
                and printer_port_valid
                and drawer_pin_valid
                and drawer_timeout_valid
                and escpos_available
                and printer_module_available
            )
            else "CONFIGURATION WARNING"
        )
    if not display_enabled:
        display_state = "DISABLED"
    elif display_test_mode:
        display_state = "TEST MODE"
    elif physical_second_display_detected:
        display_state = "DETECTED"
    else:
        display_state = "NOT CONNECTED"

    issues = []
    if not scanner_module_available:
        issues.append("Barcode scanner module is unavailable")
    if not pynput_available:
        issues.append("Barcode scanner pynput dependency is unavailable")
    if not scanner_timing_valid:
        issues.append("Barcode scanner timing configuration is invalid")
    if host_window is not None and barcode_manager is None:
        issues.append("Barcode manager is not initialized")
    if printer_enabled:
        if not printer_ip_valid:
            issues.append("Printer IP configuration is invalid")
        if not printer_port_valid:
            issues.append("Printer port configuration is invalid")
        if not escpos_available:
            issues.append("python-escpos dependency is unavailable")
        if not printer_module_available:
            issues.append("Printer and cash-drawer module is unavailable")
    if drawer_enabled:
        if not drawer_pin_valid:
            issues.append("Cash-drawer pin configuration is invalid")
        if not drawer_timeout_valid:
            issues.append("Cash-drawer timeout configuration is invalid")
    if display_enabled:
        if not display_module_available:
            issues.append("Customer-display module is unavailable")
        if not screen2_ui_available:
            issues.append("Customer-display screen2.ui is unavailable")
        if not screen_index_valid:
            issues.append("Customer-display screen index is invalid")

    return {
        "scanner": {
            "state": (
                "SOFTWARE READY"
                if (
                    scanner_module_available
                    and pynput_available
                    and scanner_timing_valid
                )
                else "SOFTWARE WARNING"
            ),
            "module_available": scanner_module_available,
            "pynput_available": pynput_available,
            "controller_state": scanner_controller_state,
            "timing_seconds": scanner_timing,
            "timing_valid": scanner_timing_valid,
            "physical_test": "NOT TESTED",
        },
        "printer": {
            "state": printer_state,
            "enabled": printer_enabled,
            "module_available": printer_module_available,
            "escpos_available": escpos_available,
            "ip": printer_ip,
            "ip_valid": printer_ip_valid,
            "port": printer_port,
            "port_valid": printer_port_valid,
            "physical_test": "NOT TESTED",
        },
        "cash_drawer": {
            "state": drawer_state,
            "enabled": drawer_enabled,
            "pin": drawer_pin,
            "pin_valid": drawer_pin_valid,
            "timeout": drawer_timeout,
            "timeout_valid": drawer_timeout_valid,
            "physical_test": "NOT TESTED",
        },
        "second_monitor": {
            "state": display_state,
            "enabled": display_enabled,
            "test_mode": display_test_mode,
            "module_available": display_module_available,
            "screen2_ui_available": screen2_ui_available,
            "configured_screen_index": screen_index,
            "screen_index_valid": screen_index_valid,
            "detected_screen_total": detected_screens,
            "physical_second_display_detected": (
                physical_second_display_detected
            ),
            "physical_test": "NOT TESTED",
        },
        "physical_verification_message": (
            "Physical operation is not tested by this diagnostic. "
            "Verify devices through normal application workflows."
        ),
        "issues": issues,
    }


def run_device_readiness_diagnostics(*, host_window=None) -> dict:
    """Run non-invasive device readiness inspection."""
    started_clock = perf_counter()
    result = {
        "check": "Device readiness",
        "status": "FAIL",
        "started_at": timestamp(),
        "completed_at": None,
        "duration_seconds": 0.0,
        "scanner": {},
        "printer": {},
        "cash_drawer": {},
        "second_monitor": {},
        "physical_verification_message": "",
        "issues": [],
    }
    try:
        result.update(analyze_device_readiness(host_window=host_window))
        result["status"] = "WARNING" if result["issues"] else "PASS"
    except Exception as exc:
        result["issues"].append(
            f"{type(exc).__name__}: "
            f"{str(exc) or 'Device readiness diagnostic failed'}"
        )
    finally:
        result["completed_at"] = timestamp()
        result["duration_seconds"] = round(perf_counter() - started_clock, 3)
    return result
