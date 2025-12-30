"""
debug_utils.py - Utility functions for focus/widget debugging in the POS system.
"""
from PyQt5.QtWidgets import QWidget, QApplication

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
    """
    Print detailed focus/widget chain for debugging scanner and focus issues.
    """
    try:
        app = QApplication.instance()
        aw = app.activeWindow() if app else None
        fw = app.focusWidget() if app else None
        # Build parent chain from focus widget up to window
        chain = []
        cur = fw
        seen = 0
        while cur is not None and seen < 10:  # limit to avoid accidental loops
            chain.append(describe_widget(cur))
            cur = cur.parent()
            seen += 1
        chain_str = ' -> '.join(reversed(chain)) if chain else 'None'
        win_title = ''
        try:
            if aw and hasattr(aw, 'windowTitle'):
                win_title = aw.windowTitle()
        except Exception:
            pass
        print('[Scanner][Focus]',
              f"context={context}",
              f"barcode='{barcode}'",
              f"activeWindow={describe_widget(aw)}",
              f"windowTitle='{win_title}'",
              f"focusPath={chain_str}")
    except Exception as _e:
        print('[Scanner][Focus] debug failed:', _e)
