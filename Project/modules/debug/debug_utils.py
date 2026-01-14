"""debug_utils.py - legacy debug helpers (console output removed)."""

from PyQt5.QtWidgets import QWidget

def describe_widget(w: QWidget) -> str:
    try:
        if w is None:
            return 'None'
        name = w.objectName() or ''
        cls = w.metaObject().className() if hasattr(w, 'metaObject') else w.__class__.__name__
        if name:
            return f"{cls}(objectName='{name}')"
        return cls
    except Exception:
        return '<unknown>'

def debug_print_focus(context: str, barcode: str = '', main_window=None):
    """No-op: console debug output removed."""
    return
