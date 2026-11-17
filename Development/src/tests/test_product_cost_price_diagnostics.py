from modules.menu.diagnostics import (
    find_missing_product_cost_prices,
    format_diagnostic_report,
    run_product_cost_price_diagnostics,
)


def test_finds_only_missing_cost_prices():
    rows = [
        {"product_code": "A1", "cost_price": None},
        {"product_code": "B2", "cost_price": ""},
        {"product_code": "C3", "cost_price": "  "},
        {"product_code": "D4", "cost_price": 0},
        {"product_code": "E5", "cost_price": 1.25},
    ]

    result = find_missing_product_cost_prices(rows)

    assert result == {
        "database_total": 5,
        "missing_cost_price_total": 3,
        "missing_cost_price_codes": ["A1", "B2", "C3"],
    }


def test_run_and_report_cost_price_findings_in_columns():
    result = run_product_cost_price_diagnostics(
        database_rows=[
            {"product_code": code, "cost_price": None}
            for code in ("A1", "B2", "C3", "D4", "E5")
        ]
    )
    report = format_diagnostic_report({"product_cost_prices": result})

    assert result["status"] == "WARNING"
    assert "1. Products with missing cost price" in report
    assert "PRODUCTS WITH MISSING COST PRICE" in report
    assert "profit and margin calculations" in report
    assert "A1" in report and "B2" in report and "C3" in report and "D4" in report
    assert "- A1" not in report
