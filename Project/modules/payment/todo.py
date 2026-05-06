import os

from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import Qt

from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui,
    require_widgets,
    set_dialog_info,
    log_exception_traceback_and_postclose_statusBar,
)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))
UI_PATH = os.path.join(_PROJECT_DIR, 'ui', 'todo.ui')
QSS_PATH = os.path.join(_PROJECT_DIR, 'assets', 'dialog.qss')


def launch_todo_dialog(parent=None):
    """Build and return the TODO dialog.

    The dialog is created frameless so the UI's `customTitleBar` replaces
    the default window title bar. A barcode override is installed on the
    returned dialog so the wrapper can safely block scanner input while the
    modal is open.
    """
    dlg = build_dialog_from_ui(
        UI_PATH,
        host_window=parent,
        dialog_name='Todo',
        qss_path=QSS_PATH,
        frameless=True,
        application_modal=True,
    )

    if not dlg:
        from modules.ui_utils.dialog_utils import build_error_fallback_dialog

        return build_error_fallback_dialog(parent, 'Todo', QSS_PATH)

    try:
        widgets = require_widgets(dlg, {
            'close_btn': (QPushButton, 'customCloseBtn'),
        })
    except Exception:
        widgets = {}

    close_btn = widgets.get('close_btn') if widgets else None
    if close_btn is not None:
        try:
            close_btn.clicked.connect(dlg.reject)
        except Exception:
            pass

    def _barcode_override(barcode: str) -> bool:
        # Swallow scanner input while TODO dialog is active.
        return True

    try:
        dlg.barcode_override_handler = _barcode_override
    except Exception:
        pass

    try:
        # Optional: set focus to close button so Esc/X works predictably.
        if close_btn is not None:
            close_btn.setFocus()
    except Exception:
        pass

    return dlg
