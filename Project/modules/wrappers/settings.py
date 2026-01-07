import json
import os
from pathlib import Path
from typing import Dict, Any, Tuple

# External config with app constants
try:
    from config import APPDATA_DIR, VEG_SLOTS
except Exception:
    # Fallbacks if config is not yet updated; keep things working during dev
    BASE_DIR = Path(__file__).resolve().parents[2]  # .../POS/Project
    APPDATA_DIR = str(BASE_DIR / 'AppData')
    VEG_SLOTS = 14


def _ensure_appdata_dir() -> Path:
    p = Path(APPDATA_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def appdata_path(name: str) -> Path:
    """Return the full path to <APPDATA_DIR>/<name>.json and ensure parent exists."""
    return _ensure_appdata_dir() / f"{name}.json"


def veg_slots() -> int:
    return int(VEG_SLOTS)


def _default_mapping(n: int) -> Dict[str, Dict[str, str]]:
    # veg1..vegN initialized to empty
    return {f"veg{i}": {"state": "empty", "label": "empty"} for i in range(1, n + 1)}


def _validate_mapping(mapping: Dict[str, Any], n: int) -> Tuple[bool, str]:
    try:
        keys = [f"veg{i}" for i in range(1, n + 1)]
        for k in keys:
            if k not in mapping:
                return False, f"Missing key: {k}"
            entry = mapping[k]
            if not isinstance(entry, dict):
                return False, f"Invalid entry for {k}"
            state = entry.get("state")
            label = entry.get("label")
            if state not in ("custom", "empty"):
                return False, f"Invalid state for {k}: {state}"
            if not isinstance(label, str):
                return False, f"Invalid label for {k}"
        return True, ""
    except Exception as e:
        return False, str(e)


def load_mapping(name: str) -> Dict[str, Dict[str, str]]:
    """Load mapping JSON; return defaults if file missing or invalid."""
    n = veg_slots()
    path = appdata_path(name)
    if not path.exists():
        return _default_mapping(n)
    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        ok, msg = _validate_mapping(data, n)
        if not ok:
            # fall back gracefully
            return _default_mapping(n)
        return data
    except Exception:
        return _default_mapping(n)


def save_mapping(name: str, mapping: Dict[str, Dict[str, str]]) -> None:
    """Atomically save mapping to JSON (<name>.json)."""
    n = veg_slots()
    ok, msg = _validate_mapping(mapping, n)
    if not ok:
        raise ValueError(f"Invalid mapping: {msg}")

    path = appdata_path(name)
    tmp = path.with_suffix('.json.tmp')
    # write pretty but compact
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    os.replace(str(tmp), str(path))


def exists(name: str) -> bool:
    return appdata_path(name).exists()


# Convenience aliases for vegetables feature
VEG_NAME = 'vegetables'


def load_vegetables() -> Dict[str, Dict[str, str]]:
    return load_mapping(VEG_NAME)


def save_vegetables(mapping: Dict[str, Dict[str, str]]) -> None:
    save_mapping(VEG_NAME, mapping)
