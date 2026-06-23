import config
from modules.ui_utils import greeting_state


def test_current_greeting_uses_saved_value_first(monkeypatch):
    monkeypatch.setattr(greeting_state, 'load_greeting', lambda: 'Saved greeting')
    monkeypatch.setattr(config, 'GREETING_SELECTED', 'Config greeting')

    assert greeting_state.current_greeting() == 'Saved greeting'


def test_current_greeting_uses_config_fallback(monkeypatch):
    monkeypatch.setattr(greeting_state, 'load_greeting', lambda: '')
    monkeypatch.setattr(config, 'GREETING_SELECTED', 'Config greeting')

    assert greeting_state.current_greeting() == 'Config greeting'


def test_current_greeting_uses_default_fallback(monkeypatch):
    monkeypatch.setattr(greeting_state, 'load_greeting', lambda: '')
    monkeypatch.setattr(config, 'GREETING_SELECTED', '')

    assert greeting_state.current_greeting() == greeting_state.DEFAULT_GREETING
