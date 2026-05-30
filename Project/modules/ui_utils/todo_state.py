import json
import os
from pathlib import Path
from typing import List

from modules.ui_utils import input_validation
from modules.ui_utils.error_logger import log_error_message

try:
    from config import APPDATA_DIR
except Exception:
    APPDATA_DIR = None

try:
    from modules.wrappers.settings import appdata_path
except Exception:
    appdata_path = None

_TODO_NAME = 'todo'
_last_load_error = ''


def _todo_path() -> Path:
    if callable(appdata_path):
        try:
            return appdata_path(_TODO_NAME)
        except Exception:
            pass
    if APPDATA_DIR:
        path = Path(APPDATA_DIR) / f"{_TODO_NAME}.json"
    else:
        path = Path(__file__).resolve().parents[2] / 'AppData' / f"{_TODO_NAME}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _normalize_items(items: List[str]) -> List[str]:
    clean: List[str] = []
    for item in items or []:
        text = str(item or '').strip()
        if not text:
            continue
        clean.append(text)
    return clean


def load_todos() -> List[str]:
    global _last_load_error
    _last_load_error = ''
    path = _todo_path()
    if not path.exists():
        _last_load_error = f"Todo file missing: {path}"
        log_error_message(f"todo_state: {_last_load_error}")
        return []
    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        items = data.get('items', []) if isinstance(data, dict) else []
        items = _normalize_items(items)
        ok, msg = input_validation.validate_todo_items(items)
        if not ok:
            if len(items) > int(input_validation.TODO_ROWS):
                return items[:int(input_validation.TODO_ROWS)]
            _last_load_error = f"Invalid todo file: {msg}"
            log_error_message(f"todo_state: invalid items in {path}: {msg}")
            return []
        return items
    except Exception as exc:
        _last_load_error = f"Todo file could not be loaded: {exc}"
        log_error_message(f"todo_state: load failed: {exc}")
        return []


def get_last_load_error() -> str:
    return _last_load_error


def save_todos(items: List[str]) -> None:
    clean = _normalize_items(items)
    ok, msg = input_validation.validate_todo_items(clean)
    if not ok:
        raise ValueError(msg)

    path = _todo_path()
    tmp = path.with_suffix('.json.tmp')
    data = {'items': clean}
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(str(tmp), str(path))
