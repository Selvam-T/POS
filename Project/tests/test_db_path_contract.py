from pathlib import Path

import pytest

import config
from modules.db_operation.sqlite_runtime import get_conn, get_db_path


def test_default_database_path_comes_from_config(tmp_path, monkeypatch):
    configured = tmp_path / 'configured.db'
    configured.touch()
    monkeypatch.delenv('POS_DB_PATH', raising=False)
    monkeypatch.setenv('DB_PATH', str(tmp_path / 'ignored.db'))
    monkeypatch.setattr(config, 'DB_PATH', str(configured))

    assert get_db_path() == str(configured.resolve())


def test_pos_db_path_overrides_config(tmp_path, monkeypatch):
    override = tmp_path / 'support.db'
    override.touch()
    monkeypatch.setenv('POS_DB_PATH', str(override))

    assert get_db_path() == str(override.resolve())


def test_missing_database_fails_without_creating_file(tmp_path, monkeypatch):
    missing = tmp_path / 'missing.db'
    monkeypatch.setenv('POS_DB_PATH', str(missing))

    with pytest.raises(FileNotFoundError, match='Database file not found'):
        get_db_path()

    assert not missing.exists()


def test_explicit_missing_connection_path_is_not_created(tmp_path):
    missing = tmp_path / 'explicit-missing.db'

    with pytest.raises(FileNotFoundError, match='Database file not found'):
        get_conn(str(missing))

    assert not missing.exists()


def test_connection_opens_existing_database(tmp_path):
    db_path = tmp_path / 'existing.db'
    db_path.touch()

    conn = get_conn(str(db_path))
    try:
        assert conn.execute('PRAGMA foreign_keys').fetchone()[0] == 1
    finally:
        conn.close()


def test_missing_database_stops_application_startup(monkeypatch):
    import main
    from modules.db_operation import sqlite_runtime
    from modules.ui_utils import error_logger

    messages = []

    def raise_missing_database():
        raise FileNotFoundError('Database file not found: test-missing.db')

    monkeypatch.setattr(main, 'QApplication', lambda _argv: object())
    monkeypatch.setattr(main, 'load_qss', lambda _app: None)
    monkeypatch.setattr(main, 'qInstallMessageHandler', lambda _handler: None)
    monkeypatch.setattr(sqlite_runtime, 'get_db_path', raise_missing_database)
    monkeypatch.setattr(error_logger, 'log_error_message', lambda _message: None)
    monkeypatch.setattr(
        main.QMessageBox,
        'critical',
        lambda _parent, title, message: messages.append((title, message)),
    )

    assert main.main() == 1
    assert messages == [
        (
            'Database Not Found',
            'Database file not found: test-missing.db\n\nThe application will close.',
        )
    ]
