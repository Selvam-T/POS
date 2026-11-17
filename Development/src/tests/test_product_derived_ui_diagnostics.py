from modules.menu.diagnostics.product_derived_ui_check import (
    analyze_product_derived_ui,
    run_product_derived_ui_diagnostics,
)
from modules.menu.diagnostics.report_formatter import format_diagnostic_report
from modules.ui_utils.product_choices import build_product_name_choices


def _record(name, price=1.0, unit="Each", category="Other"):
    return (name, price, unit, category)


def _complete_cache():
    cache = {
        "1001": _record("Fresh  Milk"),
        "1002": _record("fresh milk"),
        "1003": _record("Apple-Juice"),
    }
    for index in range(1, 17):
        cache[f"VEG{index:02d}"] = _record(
            f"Vegetable {index}",
            category="Vegetable",
        )
    return cache


def test_shared_builder_returns_sorted_source_faithful_choices():
    choices = build_product_name_choices(
        {
            "1": _record("  Fresh   Milk "),
            "2": _record("Fresh   Milk"),
            "3": _record("Apple-Juice"),
            "4": _record(""),
        }
    )

    assert choices == ["Apple-Juice", "Fresh   Milk", "Fresh   Milk"]


def test_analysis_accepts_complete_slots_and_ignores_barcoded_vegetable():
    cache = _complete_cache()
    cache["9556000000001"] = _record(
        "Scanned Vegetable",
        category="Vegetable",
    )
    result = analyze_product_derived_ui(cache)

    assert result["missing_vegetable_codes"] == []
    assert result["unexpected_vegetable_codes"] == []
    assert result["invalid_vegetable_records"] == []
    assert result["available_vegetable_total"] == 16
    assert result["expected_choice_total"] == result["choice_total"]
    assert result["duplicate_source_name_total"] == 0


def test_analysis_reports_missing_unexpected_and_invalid_reserved_slots():
    cache = _complete_cache()
    del cache["VEG16"]
    cache["VEG17"] = _record("Unexpected", category="Vegetable")
    cache["VEG01"] = _record(
        "Vegetable 1",
        price=0,
        unit="",
        category="Other",
    )
    result = analyze_product_derived_ui(cache)

    assert result["missing_vegetable_codes"] == ["VEG16"]
    assert result["unexpected_vegetable_codes"] == ["VEG17"]
    assert result["invalid_vegetable_records"] == [
        {
            "product_code": "VEG01",
            "invalid_fields": ["selling price", "unit", "category"],
        }
    ]


def test_unpopulated_fixed_slots_are_informational_not_issues():
    cache = _complete_cache()
    del cache["VEG14"]
    del cache["VEG15"]
    del cache["VEG16"]
    result = run_product_derived_ui_diagnostics(cache)

    assert result["missing_vegetable_codes"] == [
        "VEG14",
        "VEG15",
        "VEG16",
    ]
    assert result["status"] == "PASS"
    assert result["issues"] == []


def test_malformed_cache_record_is_reported_without_crashing():
    cache = _complete_cache()
    cache["BROKEN"] = 42
    result = run_product_derived_ui_diagnostics(cache)

    assert result["status"] == "WARNING"
    assert result["malformed_cache_codes"] == ["BROKEN"]


def test_runner_and_report_state_widget_sync_limitation():
    result = run_product_derived_ui_diagnostics(_complete_cache())
    report = format_diagnostic_report({"product_derived_ui": result})

    assert result["status"] == "PASS"
    assert "PRODUCT SEARCH LISTS AND VEGETABLE SLOTS" in report
    assert "Manual entry, Refund, Receipt, Product menu" in report
    assert "Expected slots: 16" in report
    assert "Available slots: 16" in report
    assert "Unpopulated slot codes (informational): 0" in report
    assert "LIMITATIONS" in report
    assert "does not inspect unopened dialog widgets" in report
