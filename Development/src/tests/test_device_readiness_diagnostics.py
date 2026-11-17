from types import SimpleNamespace

from modules.menu.diagnostics import device_readiness_check
from modules.menu.diagnostics.report_formatter import format_diagnostic_report


def _all_modules_available(_name):
    return True


def test_disabled_hardware_and_test_mode_are_not_warnings(monkeypatch):
    monkeypatch.setattr(
        device_readiness_check,
        "_module_available",
        _all_modules_available,
    )
    monkeypatch.setattr(
        device_readiness_check.config,
        "ENABLE_PRINTER_PRINT",
        False,
    )
    monkeypatch.setattr(
        device_readiness_check.config,
        "ENABLE_CASH_DRAWER",
        False,
    )
    monkeypatch.setattr(
        device_readiness_check.config,
        "CUSTOMER_DISPLAY_ENABLED",
        True,
    )
    monkeypatch.setattr(
        device_readiness_check.config,
        "CUSTOMER_DISPLAY_TEST_MODE",
        True,
    )
    host = SimpleNamespace(
        barcode_manager=SimpleNamespace(scanner=object())
    )

    result = device_readiness_check.run_device_readiness_diagnostics(
        host_window=host
    )

    assert result["status"] == "PASS"
    assert result["printer"]["state"] == "DISABLED"
    assert result["cash_drawer"]["state"] == "DISABLED"
    assert result["second_monitor"]["state"] == "TEST MODE"
    assert result["issues"] == []


def test_invalid_enabled_printer_configuration_warns(monkeypatch):
    monkeypatch.setattr(
        device_readiness_check,
        "_module_available",
        _all_modules_available,
    )
    monkeypatch.setattr(
        device_readiness_check.config,
        "ENABLE_PRINTER_PRINT",
        True,
    )
    monkeypatch.setattr(device_readiness_check.config, "PRINTER_IP", "")
    monkeypatch.setattr(device_readiness_check.config, "PRINTER_PORT", 70000)

    result = device_readiness_check.run_device_readiness_diagnostics()

    assert result["status"] == "WARNING"
    assert result["printer"]["state"] == "CONFIGURATION WARNING"
    assert "Printer IP configuration is invalid" in result["issues"]
    assert "Printer port configuration is invalid" in result["issues"]


def test_absent_physical_second_monitor_is_not_a_warning(monkeypatch):
    monkeypatch.setattr(
        device_readiness_check,
        "_module_available",
        _all_modules_available,
    )
    monkeypatch.setattr(
        device_readiness_check.config,
        "CUSTOMER_DISPLAY_ENABLED",
        True,
    )
    monkeypatch.setattr(
        device_readiness_check.config,
        "CUSTOMER_DISPLAY_TEST_MODE",
        False,
    )

    result = device_readiness_check.analyze_device_readiness(screen_count=1)

    assert result["second_monitor"]["state"] == "NOT CONNECTED"
    assert result["issues"] == []


def test_report_states_physical_operations_are_not_tested(monkeypatch):
    monkeypatch.setattr(
        device_readiness_check,
        "_module_available",
        _all_modules_available,
    )
    result = device_readiness_check.run_device_readiness_diagnostics()
    report = format_diagnostic_report({"device_readiness": result})

    assert "DEVICE READINESS" in report
    assert "Print test: NOT TESTED" in report
    assert "Open test: NOT TESTED" in report
    assert "Physical input test: NOT TESTED" in report
    assert "Presentation test: NOT TESTED" in report
    assert (
        "Verify devices through normal application workflows."
        in report
    )
