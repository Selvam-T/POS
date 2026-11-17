from main import MainLoader


class _Table:
    def __init__(self, *, fail=False):
        self.fail = fail

    def rowCount(self):
        if self.fail:
            raise RuntimeError("table unavailable")
        return 0


class _Host:
    _show_sales_table_unavailable = MainLoader._show_sales_table_unavailable
    _mark_sales_table_unavailable = MainLoader._mark_sales_table_unavailable
    _require_sales_table_ready = MainLoader._require_sales_table_ready

    def __init__(self, table=None, *, ready=False):
        self.sales_table = table
        self._sales_table_ready = ready
        self._sales_table_failure_logged = False
        self._sales_table_error = ""
        self._sales_table_unavailable_message = "Sales table unavailable."


def test_ready_sales_table_allows_transaction_actions(monkeypatch):
    statuses = []
    monkeypatch.setattr(
        "main.report_to_statusbar",
        lambda *args, **kwargs: statuses.append((args, kwargs)),
    )
    host = _Host(_Table(), ready=True)

    assert host._require_sales_table_ready() is True
    assert statuses == []


def test_unavailable_sales_table_logs_once_but_reports_each_attempt(monkeypatch):
    logs = []
    statuses = []
    monkeypatch.setattr(
        "modules.ui_utils.error_logger.log_error_message",
        logs.append,
    )
    monkeypatch.setattr(
        "main.report_to_statusbar",
        lambda *args, **kwargs: statuses.append((args, kwargs)),
    )
    host = _Host(None, ready=False)

    assert host._require_sales_table_ready() is False
    assert host._require_sales_table_ready() is False

    assert len(logs) == 1
    assert "Sales table is not initialized" in logs[0]
    assert len(statuses) == 2
    assert all(call[1]["is_error"] is True for call in statuses)


def test_runtime_table_failure_marks_sales_table_unavailable(monkeypatch):
    logs = []
    statuses = []
    monkeypatch.setattr(
        "modules.ui_utils.error_logger.log_error_message",
        logs.append,
    )
    monkeypatch.setattr(
        "main.report_to_statusbar",
        lambda *args, **kwargs: statuses.append((args, kwargs)),
    )
    host = _Host(_Table(fail=True), ready=True)

    assert host._require_sales_table_ready() is False
    assert host._sales_table_ready is False
    assert "table unavailable" in host._sales_table_error
    assert len(logs) == 1
    assert len(statuses) == 1
