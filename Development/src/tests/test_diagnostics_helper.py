import sqlite3
from datetime import datetime, timezone

from modules.menu.diagnostics_helper import (
    CORE_TABLES,
    compare_product_cache,
    export_diagnostic_report,
    format_diagnostic_report,
    run_database_diagnostics,
    run_product_cache_diagnostics,
)


def _create_core_tables(path):
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(
            """
            CREATE TABLE Category (
                category_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE Product_list (
                product_code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                FOREIGN KEY(category_id) REFERENCES Category(category_id)
            );
            CREATE TABLE users (user_id INTEGER PRIMARY KEY);
            CREATE TABLE receipts (receipt_id INTEGER PRIMARY KEY);
            CREATE TABLE receipt_items (item_id INTEGER PRIMARY KEY);
            CREATE TABLE receipt_payments (payment_id INTEGER PRIMARY KEY);
            CREATE TABLE cash_outflows (outflows_id INTEGER PRIMARY KEY);
            """
        )
        conn.execute(
            "INSERT INTO Category(category_id, name) VALUES (1, 'Other')"
        )
        conn.execute(
            "INSERT INTO Product_list(product_code, name, category_id) "
            "VALUES ('1001', 'Test Product', 1)"
        )
        conn.commit()
    finally:
        conn.close()


def test_database_diagnostics_passes_and_counts_rows(tmp_path):
    db_path = tmp_path / "diagnostics.db"
    _create_core_tables(db_path)

    result = run_database_diagnostics(str(db_path))

    assert result["status"] == "PASS"
    assert result["read_only"] is True
    assert result["quick_check"] == ["ok"]
    assert result["foreign_key_violations"] == []
    assert result["missing_tables"] == []
    assert result["table_counts"]["Product_list"] == 1
    assert result["table_counts"]["Category"] == 1


def test_database_diagnostics_reports_missing_tables(tmp_path):
    db_path = tmp_path / "incomplete.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE Product_list (product_code TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

    result = run_database_diagnostics(str(db_path))

    assert result["status"] == "FAIL"
    assert set(result["missing_tables"]) == set(CORE_TABLES) - {"Product_list"}
    assert any("Missing required tables" in issue for issue in result["issues"])


def test_database_diagnostics_does_not_modify_database(tmp_path):
    db_path = tmp_path / "read_only.db"
    _create_core_tables(db_path)
    before = db_path.read_bytes()

    run_database_diagnostics(str(db_path))

    assert db_path.read_bytes() == before


def test_diagnostic_report_exports_utf8_text(tmp_path):
    db_path = tmp_path / "report.db"
    _create_core_tables(db_path)
    result = run_database_diagnostics(str(db_path))
    generated = datetime(2026, 7, 27, 18, 30, 45, tzinfo=timezone.utc)

    report_path = export_diagnostic_report(
        {"database": result},
        output_dir=tmp_path / "Diagnostic",
        generated_at=generated,
    )
    report = report_path.read_text(encoding="utf-8")

    assert report_path.name == "diagnostic_report_27jul2026_18-30-45.txt"
    assert "SELVAM POS DIAGNOSTIC REPORT" in report
    assert "Overall status: PASS" in report
    assert "Product_list: 1" in report
    assert "Category: 1" in report
    assert "SQLite quick_check:\n- ok" in report
    assert "Foreign-key violations:\n- None" in report
    assert "Issues:\n- None" in report


def test_diagnostic_report_uses_unique_filename(tmp_path):
    generated = datetime(2026, 7, 27, 18, 30, 45, tzinfo=timezone.utc)
    result = {"database": {"status": "FAIL", "issues": ["Test issue"]}}

    first = export_diagnostic_report(
        result,
        output_dir=tmp_path,
        generated_at=generated,
    )
    second = export_diagnostic_report(
        result,
        output_dir=tmp_path,
        generated_at=generated,
    )

    assert first.name == "diagnostic_report_27jul2026_18-30-45.txt"
    assert second.name == "diagnostic_report_27jul2026_18-30-45_2.txt"
    assert "Issues:\n- Test issue" in format_diagnostic_report(
        result,
        generated_at=generated,
    )


def test_diagnostic_report_surfaces_export_folder_failure(tmp_path):
    output_target = tmp_path / "not-a-folder"
    output_target.write_text("occupied", encoding="utf-8")

    try:
        export_diagnostic_report(
            {"database": {"status": "PASS"}},
            output_dir=output_target,
        )
    except OSError as exc:
        assert str(exc)
    else:
        raise AssertionError("Expected export_diagnostic_report to fail")


def _cache_rows():
    return [
        {
            "product_code": "1001",
            "name": "Test Product",
            "selling_price": 1.5,
            "unit": "Each",
            "category": "Other",
        },
        {
            "product_code": "1002",
            "name": "Second Product",
            "selling_price": 2.0,
            "unit": "Packet",
            "category": "Grocery",
        },
    ]


def test_product_cache_diagnostics_passes_for_matching_live_cache():
    cache = {
        "1001": ("Test Product", 1.5, "Each", "Other"),
        "1002": ("Second Product", 2.0, "Packet", "Grocery"),
    }

    result = run_product_cache_diagnostics(
        cache,
        database_rows=_cache_rows(),
    )

    assert result["status"] == "PASS"
    assert result["database_total"] == 2
    assert result["cache_total"] == 2
    assert result["consistent_total"] == 2
    assert result["inconsistent_total"] == 0
    assert result["issues"] == []


def test_product_cache_diagnostics_reports_all_inconsistency_types():
    cache = {
        "1001": ("Test Product", 9.5, "Each", "Other"),
        "9999": ("Extra Product", 3.0, "Each", "Other"),
        " lower ": ("Invalid Key Product", 1.0, "Each", "Other"),
    }

    result = run_product_cache_diagnostics(
        cache,
        database_rows=_cache_rows(),
    )

    assert result["status"] == "FAIL"
    assert result["missing_from_cache"] == ["1002"]
    assert set(result["extra_in_cache"]) == {"9999", "LOWER"}
    assert result["value_mismatches"] == ["1001"]
    assert result["mismatch_details"]["1001"]["fields"] == ["selling_price"]
    assert result["invalid_cache_keys"] == [" lower "]
    assert result["inconsistent_total"] == 5


def test_compare_product_cache_does_not_mutate_supplied_cache():
    cache = {"1001": ("Test Product", 1.5, "Each", "Other")}
    before = dict(cache)

    compare_product_cache(_cache_rows()[:1], cache)

    assert cache == before


def test_report_supports_cache_only_and_combined_failure():
    cache_result = run_product_cache_diagnostics(
        {"1001": ("Test Product", 1.5, "Each", "Other")},
        database_rows=_cache_rows()[:1],
    )
    cache_only = format_diagnostic_report({"product_cache": cache_result})

    assert "Overall status: PASS" in cache_only
    assert "1. Product cache consistency" in cache_only
    assert "PRODUCT CACHE CONSISTENCY" in cache_only
    assert "Live PRODUCT_CACHE total: 1" in cache_only

    failed_cache = dict(cache_result)
    failed_cache["status"] = "FAIL"
    failed_cache["issues"] = ["Cache value mismatches: 1"]
    combined = format_diagnostic_report(
        {
            "database": {"status": "PASS"},
            "product_cache": failed_cache,
        }
    )

    assert "Overall status: FAIL" in combined
    assert "1. Database counts and SQLite integrity" in combined
    assert "2. Product cache consistency" in combined
