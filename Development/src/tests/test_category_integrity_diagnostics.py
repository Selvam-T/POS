from modules.menu.diagnostics.category_integrity_check import (
    analyze_category_integrity,
    run_category_integrity_diagnostics,
)
from modules.menu.diagnostics.report_formatter import format_diagnostic_report


def _category(category_id, name, protected=False):
    return {
        "category_id": category_id,
        "name": name,
        "is_protected": protected,
    }


def _product(code, name, category_id):
    return {
        "product_code": code,
        "name": name,
        "category_id": category_id,
    }


def _valid_categories():
    return [
        _category(1, "Other", True),
        _category(2, "Vegetable", True),
        _category(3, "Drinks"),
    ]


def test_category_name_duplicates_normalize_spaces_and_case_only():
    result = analyze_category_integrity(
        _valid_categories()
        + [
            _category(4, "Soft  Drinks"),
            _category(5, "soft drinks"),
            _category(6, "Soft-Drinks"),
        ],
        [],
    )

    assert result["duplicate_name_group_total"] == 1
    assert result["duplicate_name_groups"][0]["normalized_name"] == (
        "soft drinks"
    )
    assert result["duplicate_name_groups"][0]["category_count"] == 2


def test_reports_no_category_id_and_nonexistent_category_id_separately():
    result = analyze_category_integrity(
        _valid_categories(),
        [
            _product("1001", "No category", None),
            _product("1002", "Broken category", 99),
            _product("1003", "Valid", 3),
        ],
    )

    assert result["products_without_category_id_total"] == 1
    assert result["products_without_category_id"][0]["product_code"] == "1001"
    assert result["products_with_missing_category_id_total"] == 1
    assert result["products_with_missing_category_id"][0][
        "category_id"
    ] == 99


def test_reports_missing_required_and_wrong_fixed_vegetable_category():
    result = analyze_category_integrity(
        [_category(1, "Other", True), _category(3, "Drinks")],
        [_product("VEG01", "Spinach", 3)],
    )

    assert result["missing_required_categories"] == ["Vegetable"]
    assert result["fixed_vegetables_wrong_category_total"] == 1
    assert result["fixed_vegetables_wrong_category"][0][
        "category_name"
    ] == "Drinks"


def test_unpopulated_vegetable_slots_are_not_category_issues():
    result = run_category_integrity_diagnostics(
        category_rows=_valid_categories(),
        product_rows=[_product("1001", "Normal Product", 3)],
    )

    assert result["status"] == "PASS"
    assert result["issues"] == []


def test_report_uses_explicit_relationship_labels():
    result = run_category_integrity_diagnostics(
        category_rows=_valid_categories(),
        product_rows=[
            _product("1001", "No category", None),
            _product("1002", "Broken category", 99),
        ],
    )
    report = format_diagnostic_report({"category_integrity": result})

    assert "Overall status: WARNING" in report
    assert "CATEGORY INTEGRITY" in report
    assert "Products with no category_id: 1" in report
    assert (
        "Products referencing an ID that does not exist in the "
        "Category table: 1"
    ) in report
    assert "1002 - Broken category; category_id=99" in report
    assert "CATEGORY USAGE" not in report
    assert "CATEGORY CHOICES" not in report
