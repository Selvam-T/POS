from pathlib import Path

import config
from modules.runtime.data import ensure_ads_dir, ensure_appdata_dir
from modules.runtime.paths import (
    asset_path,
    resolve_stylesheet_urls,
    stylesheet_path,
    ui_path,
)


def test_runtime_resource_helpers_use_shared_roots():
    assert ui_path('main_window.ui') == str(Path(config.UI_DIR) / 'main_window.ui')
    assert asset_path('icons', 'admin.svg') == str(
        Path(config.ASSETS_DIR) / 'icons' / 'admin.svg'
    )
    assert config.ICON_ADMIN == asset_path('icons', 'admin.svg')
    assert stylesheet_path('main.qss') == str(
        Path(config.ASSETS_DIR) / 'qss' / 'main.qss'
    )


def test_qss_asset_url_is_rewritten_to_runtime_assets(tmp_path):
    assets_dir = tmp_path / 'app' / '_internal' / 'assets'
    source = 'QComboBox { image: url(assets/icons/down_arrow.svg); }'

    resolved = resolve_stylesheet_urls(source, assets_dir=assets_dir)

    expected = (assets_dir / 'icons' / 'down_arrow.svg').as_posix()
    assert f'url("{expected}")' in resolved
    assert 'url(assets/' not in resolved


def test_writable_paths_are_external_to_runtime_resources():
    assert Path(config.APPDATA_DIR) == Path(config.DATA_DIR) / 'json'
    assert Path(config.ADS_DIR) == Path(config.DATA_DIR) / 'ads'
    assert Path(config.APPDATA_DIR) != Path(config.RUNTIME_DIR) / 'AppData'
    assert Path(config.ADS_DIR) != Path(config.ASSETS_DIR) / 'ads'


def test_writable_data_directories_are_created(tmp_path):
    json_dir = tmp_path / 'data' / 'json'
    ads_dir = tmp_path / 'data' / 'ads'

    assert ensure_appdata_dir(json_dir) == json_dir
    assert ensure_ads_dir(ads_dir) == ads_dir
    assert json_dir.is_dir()
    assert ads_dir.is_dir()
