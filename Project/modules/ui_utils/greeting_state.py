import json
from modules.wrappers.settings import appdata_path

_GREETING_NAME = 'greeting'


def load_greeting() -> str:
    path = appdata_path(_GREETING_NAME)
    if not path.exists():
        return ''
    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        value = str(data.get('selected') or '').strip()
        return value
    except Exception:
        return ''


def save_greeting(selected: str) -> None:
    value = str(selected or '').strip()
    path = appdata_path(_GREETING_NAME)
    tmp = path.with_suffix('.json.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump({'selected': value}, f, ensure_ascii=False, indent=2)
    tmp.replace(path)
