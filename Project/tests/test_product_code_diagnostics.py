from modules.menu.diagnostics.product_code_check import (
    find_suspicious_product_codes,
    run_product_code_diagnostics,
)
from modules.menu.diagnostics.report_formatter import format_diagnostic_report


def _row(code, name=None):
    return {"product_code": code, "name": name or f"Product {code}"}


def test_finds_one_to_three_missing_tail_characters():
    result = find_suspicious_product_codes(
        [
            _row("9556123456"),
            _row("95561234567"),
            _row("955612345678"),
            _row("9556123456789"),
        ]
    )

    pairs = {
        (item["shorter_code"], item["longer_code"]): item
        for item in result["candidates"]
    }
    assert pairs[("955612345678", "9556123456789")]["confidence"] == "HIGH"
    assert pairs[("95561234567", "9556123456789")][
        "missing_tail_characters"
    ] == 2
    assert pairs[("9556123456", "9556123456789")][
        "missing_tail_characters"
    ] == 3


def test_does_not_flag_middle_deletion_substitution_or_transposition():
    result = find_suspicious_product_codes(
        [
            _row("12345678"),
            _row("12340678"),
            _row("12345679"),
            _row("12345768"),
        ]
    )

    assert result["candidate_total"] == 0


def test_ignores_short_vegetable_and_other_internal_codes():
    result = find_suspicious_product_codes(
        [
            _row("1234"),
            _row("12345"),
            _row("VEG01"),
            _row("VEG-02"),
            _row("ABC123"),
        ]
    )

    assert result["eligible_numeric_total"] == 1
    assert result["ignored_short_code_total"] == 1
    assert result["ignored_vegetable_code_total"] == 2
    assert result["ignored_other_code_total"] == 1
    assert result["candidate_total"] == 0


def test_runner_returns_warning_for_tail_candidate_and_pass_otherwise():
    warning = run_product_code_diagnostics(
        database_rows=[_row("955612345678"), _row("9556123456789")]
    )
    passed = run_product_code_diagnostics(
        database_rows=[_row("9556123456789"), _row("8888888888888")]
    )

    assert warning["status"] == "WARNING"
    assert warning["candidate_total"] == 1
    assert passed["status"] == "PASS"
    assert passed["candidate_total"] == 0


def test_report_explains_tail_candidate():
    result = run_product_code_diagnostics(
        database_rows=[
            _row("955612345678", "Possible incomplete"),
            _row("9556123456789", "Full barcode"),
        ]
    )
    report = format_diagnostic_report({"product_codes": result})

    assert "Overall status: WARNING" in report
    assert "CHECK SETTINGS" in report
    assert "Tail truncation range checked: 1 to 3 missing characters" in report
    assert "SCAN SUMMARY" in report
    assert "FINDINGS" in report
    assert "Suspicious product codes: 2" in report
    assert "Suspicious tail-truncation pairs found: 1" in report
    assert "High-confidence pairs: 1" in report
    assert "REVIEW CANDIDATES" in report
    assert "Missing tail characters: 1" in report
    assert "Confidence: HIGH" in report
    assert "a) 955612345678 - Possible incomplete" in report
    assert "b) 9556123456789 - Full barcode" in report


def test_report_clearly_separates_zero_findings_from_settings():
    result = run_product_code_diagnostics(
        database_rows=[_row("1234"), _row("VEG01"), _row("9556123456789")]
    )
    report = format_diagnostic_report({"product_codes": result})

    assert "Minimum barcode length checked: 5 characters" in report
    assert "Product codes read from database: 3" in report
    assert "Codes excluded from comparison: 2" in report
    assert "Suspicious product codes: 0" in report
    assert "Suspicious tail-truncation pairs found: 0" in report
    assert "REVIEW CANDIDATES\n- None" in report


def test_report_counts_unique_suspicious_codes_separately_from_pairs():
    result = run_product_code_diagnostics(
        database_rows=[
            _row("1234567890"),
            _row("12345678901"),
            _row("123456789012"),
        ]
    )
    report = format_diagnostic_report({"product_codes": result})

    assert "Suspicious product codes: 3" in report
    assert "Suspicious tail-truncation pairs found: 3" in report
