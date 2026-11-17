from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTabWidget,
)

from modules.menu import admin_menu

_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication([])
    return _APP


def _dialog():
    _app()
    host = QMainWindow()
    dialog = admin_menu.launch_admin_dialog(host, user_id=1, is_admin=True)
    dialog._test_host = host
    dialog.show()
    _app().processEvents()
    return dialog


def test_identity_placeholders_are_gray_style_hooks_read_only_and_no_focus():
    dialog = _dialog()
    for prefix in ('admin', 'staff'):
        for field in ('Name', 'Email'):
            label = dialog.findChild(QLabel, f'{prefix}{field}FieldLbl')
            line_edit = dialog.findChild(QLineEdit, f'{prefix}{field}LineEdit')
            assert label.property('futurePlaceholder') is True
            assert line_edit.property('futurePlaceholder') is True
            assert line_edit.isReadOnly() is True
            assert line_edit.focusPolicy() == Qt.NoFocus
    dialog.close()


def test_screen2_and_export_close_buttons_close_the_dialog():
    for name in ('btnScreen2Cancel', 'btnExportCancel'):
        dialog = _dialog()
        button = dialog.findChild(QPushButton, name)
        assert button.text() == 'CLOSE'
        button.click()
        _app().processEvents()
        assert dialog.isVisible() is False


def test_export_success_focuses_export_close(monkeypatch, tmp_path):
    monkeypatch.setattr(admin_menu.Path, 'home', classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(
        admin_menu,
        'get_product_list_readable_rows',
        lambda: (['product_code'], [('1001',)]),
    )
    dialog = _dialog()
    tabs = dialog.findChild(QTabWidget, 'tabWidget')
    tabs.setCurrentWidget(dialog.findChild(type(tabs.widget(0)), 'tabExport'))
    dialog.findChild(QPushButton, 'csvExportBtn').click()
    _app().processEvents()

    assert dialog.findChild(QPushButton, 'btnExportCancel').hasFocus()
    assert list((tmp_path / 'POS_Exports' / 'Inventory').glob('*.csv'))
    dialog.close()


def test_export_failure_focuses_export_close(monkeypatch, tmp_path):
    logged_errors = []
    monkeypatch.setattr(admin_menu, 'log_error_message', logged_errors.append)
    blocked_home = tmp_path / 'not_a_directory'
    blocked_home.write_text('blocked', encoding='utf-8')
    monkeypatch.setattr(
        admin_menu.Path,
        'home',
        classmethod(lambda cls: blocked_home),
    )
    dialog = _dialog()
    tabs = dialog.findChild(QTabWidget, 'tabWidget')
    tabs.setCurrentWidget(dialog.findChild(type(tabs.widget(0)), 'tabExport'))
    dialog.findChild(QPushButton, 'csvExportBtn').click()
    _app().processEvents()

    assert 'failed' in dialog.findChild(QLabel, 'exportStatusLabel').text().lower()
    assert dialog.findChild(QPushButton, 'btnExportCancel').hasFocus()
    assert logged_errors
    assert 'Product List CSV failed' in logged_errors[0]
    dialog.close()
