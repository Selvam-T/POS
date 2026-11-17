"""Directory helpers for writable runtime data."""

from pathlib import Path

from config import ADS_DIR, APPDATA_DIR


def ensure_appdata_dir(path=None) -> Path:
    destination = Path(path or APPDATA_DIR)
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def ensure_ads_dir(path=None) -> Path:
    destination = Path(path or ADS_DIR)
    destination.mkdir(parents=True, exist_ok=True)
    return destination
