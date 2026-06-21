"""Shared runtime resource paths for source and PyInstaller execution."""

import re
from pathlib import Path

from config import ASSETS_DIR, QSS_DIR, UI_DIR


def ui_path(filename: str) -> str:
    return str(Path(UI_DIR) / filename)


def asset_path(*parts: str) -> str:
    return str(Path(ASSETS_DIR).joinpath(*parts))


def stylesheet_path(filename: str) -> str:
    return str(Path(QSS_DIR) / filename)


_ASSET_URL_RE = re.compile(
    r"url\(\s*(['\"]?)assets[\\/]([^)'\"]+)\1\s*\)",
    flags=re.IGNORECASE,
)


def resolve_stylesheet_urls(text: str, assets_dir=None) -> str:
    """Replace QSS ``url(assets/...)`` references with runtime absolute paths."""
    root = Path(assets_dir or ASSETS_DIR)

    def replace(match) -> str:
        target = root.joinpath(*re.split(r'[\\/]+', match.group(2)))
        return f'url("{target.as_posix()}")'

    return _ASSET_URL_RE.sub(replace, text)


def load_stylesheet(path) -> str:
    qss_path = Path(path)
    text = qss_path.read_text(encoding='utf-8')
    return resolve_stylesheet_urls(text)
