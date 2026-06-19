import os

import config


def test_development_path_layout(tmp_path):
    project_dir = tmp_path / 'Project'
    layout = config._resolve_path_layout(
        module_file=str(project_dir / 'config.py'),
        executable=str(tmp_path / 'Python' / 'python.exe'),
        frozen=False,
    )

    assert layout['is_packaged'] is False
    assert layout['runtime_dir'] == os.path.abspath(str(project_dir))
    assert layout['app_dir'] == os.path.abspath(str(project_dir))
    assert layout['client_root'] == os.path.abspath(str(tmp_path))
    assert layout['db_dir'] == os.path.abspath(str(tmp_path / 'db'))
    assert layout['assets_dir'] == os.path.abspath(str(project_dir / 'assets'))


def test_packaged_path_layout(tmp_path):
    app_dir = tmp_path / 'app'
    internal_dir = app_dir / '_internal'
    layout = config._resolve_path_layout(
        module_file=str(internal_dir / 'config.py'),
        executable=str(app_dir / 'SelvamPOS.exe'),
        frozen=True,
    )

    assert layout['is_packaged'] is True
    assert layout['runtime_dir'] == os.path.abspath(str(internal_dir))
    assert layout['app_dir'] == os.path.abspath(str(app_dir))
    assert layout['client_root'] == os.path.abspath(str(tmp_path))
    assert layout['db_dir'] == os.path.abspath(str(tmp_path / 'db'))
    assert layout['logs_dir'] == os.path.abspath(str(tmp_path / 'logs'))
    assert layout['backups_dir'] == os.path.abspath(str(tmp_path / 'backups'))
    assert layout['data_dir'] == os.path.abspath(str(tmp_path / 'data'))
    assert layout['assets_dir'] == os.path.abspath(str(internal_dir / 'assets'))
    assert layout['ui_dir'] == os.path.abspath(str(internal_dir / 'ui'))
