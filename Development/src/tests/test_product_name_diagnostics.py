from modules.menu.diagnostics.product_name_check import (
    find_duplicate_product_names,
    normalize_product_name_for_duplicate_check,
    run_product_name_diagnostics,
)
from modules.menu.diagnostics.report_formatter import format_diagnostic_report


def _row(code, name):
    return {"product_code": code, "name": name}


def test_normalization_collapses_repeated_whitespace_and_case():
    assert (
        normalize_product_name_for_duplicate_check("  Fresh   MILK\t1L ")
        == "fresh milk 1l"
    )


def test_repeated_space_variants_are_duplicate_names():
    result = find_duplicate_product_names(
        [
            _row("1001", "Fresh  Milk"),
            _row("1002", " fresh milk "),
            _row("1003", "Other Product"),
        ]
    )

    assert result["duplicate_group_total"] == 1
    assert result["duplicate_product_total"] == 2
    group = result["duplicate_groups"][0]
    assert group["normalized_name"] == "fresh milk"
    assert {item["product_code"] for item in group["products"]} == {
        "1001",
        "1002",
    }


def test_punctuation_difference_and_near_duplicate_are_not_grouped():
    result = find_duplicate_product_names(
        [
            _row("1001", "Fresh-Milk"),
            _row("1002", "Fresh Milk"),
            _row("1003", "Fresh Mil"),
        ]
    )

    assert result["duplicate_group_total"] == 0


def test_runner_warns_for_duplicates_and_passes_without_them():
    warning = run_product_name_diagnostics(
        database_rows=[
            _row("1001", "Test Product"),
            _row("1002", "test   product"),
        ]
    )
    passed = run_product_name_diagnostics(
        database_rows=[
            _row("1001", "Test Product"),
            _row("1002", "Other Product"),
        ]
    )

    assert warning["status"] == "WARNING"
    assert warning["duplicate_group_total"] == 1
    assert passed["status"] == "PASS"


def test_report_lists_duplicate_group_product_details():
    result = run_product_name_diagnostics(
        database_rows=[
            _row("1001", "Fresh  Milk"),
            _row("1002", "fresh milk"),
        ]
    )
    report = format_diagnostic_report({"product_names": result})

    assert "Overall status: WARNING" in report
    assert "DUPLICATE PRODUCT NAMES" in report
    assert "Duplicate name groups found: 1" in report
    assert "Products in duplicate groups: 2" in report
    assert "Normalized name: fresh milk (2 products)" in report
    assert "1001 - Fresh  Milk" in report
    assert "1002 - fresh milk" in report
