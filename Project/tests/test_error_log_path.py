from pathlib import Path

import config
from modules.status_footer import status_footer
from modules.ui_utils import error_logger


def test_log_path_is_external_and_shared():
    expected = str(Path(config.LOGS_DIR) / config.ERROR_LOG_FILENAME)

    assert config.LOG_PATH == expected
    assert error_logger.LOG_PATH == expected
    assert status_footer.LOG_PATH == expected


def test_barcode_routing_log_path_is_external_and_separate():
    expected = str(Path(config.LOGS_DIR) / config.BARCODE_ROUTING_LOG_FILENAME)

    assert config.BARCODE_ROUTING_LOG_PATH == expected
    assert config.BARCODE_ROUTING_LOG_PATH != config.LOG_PATH


def test_ensure_error_log_creates_directory_and_file(tmp_path):
    log_path = tmp_path / 'logs' / 'error.log'

    returned = error_logger.ensure_error_log_file(log_path)

    assert returned == str(log_path)
    assert log_path.is_file()
    assert log_path.read_text(encoding='utf-8') == ''


def test_log_error_message_appends_to_selected_file(tmp_path):
    log_path = tmp_path / 'logs' / 'error.log'

    error_logger.log_error_message('phase 3 test', log_path=log_path)

    text = log_path.read_text(encoding='utf-8')
    assert text.endswith(' - phase 3 test\n')


def test_truncate_error_log_keeps_file(tmp_path):
    log_path = tmp_path / 'logs' / 'error.log'
    log_path.parent.mkdir()
    log_path.write_text('existing error\n', encoding='utf-8')

    returned = error_logger.truncate_error_log(log_path)

    assert returned == str(log_path)
    assert log_path.is_file()
    assert log_path.stat().st_size == 0
