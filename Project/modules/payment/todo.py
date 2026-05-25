import os

from PyQt5.QtWidgets import QPushButton, QLineEdit, QLabel, QTableWidget, QHeaderView
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon

import config
from modules.ui_utils import input_handler, ui_feedback, todo_state
from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui,
    require_widgets,
    set_dialog_info,
)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))
UI_PATH = os.path.join(_PROJECT_DIR, 'ui', 'todo.ui')
QSS_PATH = os.path.join(_PROJECT_DIR, 'assets', 'dialog.qss')


def launch_todo_dialog(parent=None):
    """Build and return the TODO dialog.

    Uses the custom title bar and dialog.qss styling.
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
            'input': (QLineEdit, 'todoInputLineEdit'),
            'add_btn': (QPushButton, 'todoAddBtn'),
            'status': (QLabel, 'todoStatusLabel'),
            'table': (QTableWidget, 'todoTableWidget'),
        })
    except Exception:
        widgets = {}

    close_btn = widgets.get('close_btn') if widgets else None
    todo_input = widgets.get('input') if widgets else None
    add_btn = widgets.get('add_btn') if widgets else None
    status_lbl = widgets.get('status') if widgets else None
    table = widgets.get('table') if widgets else None
    if close_btn is not None:
        try:
            close_btn.clicked.connect(dlg.reject)
        except Exception:
            pass

    def _set_add_enabled(enabled: bool) -> None:
        if add_btn is None:
            return
        try:
            add_btn.setEnabled(bool(enabled))
        except Exception:
            pass
        try:
            add_btn.setFocusPolicy(Qt.StrongFocus if enabled else Qt.NoFocus)
        except Exception:
            pass

    def _update_add_state() -> None:
        text = (todo_input.text() or '').strip() if todo_input is not None else ''
        _set_add_enabled(bool(text))

    def _validate_todo_input() -> str:
        if todo_input is None:
            return ''
        return input_handler.handle_todo_input(todo_input)

    def _configure_table() -> None:
        if table is None:
            return
        try:
            table.setRowCount(int(config.TODO_ROWS))
        except Exception:
            pass
        try:
            table.setColumnCount(3)
        except Exception:
            pass
        try:
            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.Fixed)
            table.setColumnWidth(0, 60)
            table.setColumnWidth(2, 52)
        except Exception:
            pass
        try:
            table.verticalHeader().setVisible(False)
        except Exception:
            pass
        try:
            table.setShowGrid(False)
        except Exception:
            pass
        try:
            table.setSelectionMode(QTableWidget.NoSelection)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
        except Exception:
            pass

    def _clear_row(row: int) -> None:
        if table is None:
            return
        for col in range(3):
            try:
                table.setCellWidget(row, col, None)
            except Exception:
                pass

    def _refresh_table() -> None:
        if table is None:
            return
        for r in range(int(config.TODO_ROWS)):
            _clear_row(r)
        items = list(getattr(dlg, '_todo_items', []) or [])
        for r in range(int(config.TODO_ROWS)):
            if r >= len(items):
                try:
                    table.setRowHidden(r, True)
                except Exception:
                    pass
                continue
            try:
                table.setRowHidden(r, False)
            except Exception:
                pass
            try:
                table.setRowHeight(r, 44)
            except Exception:
                pass

            try:
                num_lbl = QLabel(str(r + 1))
                num_lbl.setAlignment(Qt.AlignCenter)
                num_lbl.setProperty('todoRowCell', 'number')
                table.setCellWidget(r, 0, num_lbl)
            except Exception:
                pass

            try:
                text_le = QLineEdit()
                text_le.setText(items[r])
                text_le.setReadOnly(True)
                text_le.setFocusPolicy(Qt.NoFocus)
                text_le.setProperty('todoRowCell', 'text')
                table.setCellWidget(r, 1, text_le)
            except Exception:
                pass

            try:
                del_btn = QPushButton()
                del_btn.setObjectName(f"todoDeleteBtn_{r + 1}")
                del_btn.setToolTip("Delete task")
                del_btn.setText("")
                icon_path = os.path.join(_PROJECT_DIR, 'assets', 'icons', 'delete_todo.svg')
                del_btn.setIcon(QIcon(icon_path))
                del_btn.setIconSize(QSize(36, 36))
                del_btn.setFlat(True)
                del_btn.setFocusPolicy(Qt.NoFocus)
                del_btn.setProperty('todoRowCell', 'delete')
                del_btn.clicked.connect(lambda _=None, idx=r: _delete_row(idx))
                table.setCellWidget(r, 2, del_btn)
            except Exception:
                pass

        try:
            if items:
                table.scrollToBottom()
        except Exception:
            pass

    def _save_items() -> None:
        try:
            todo_state.save_todos(getattr(dlg, '_todo_items', []) or [])
        except Exception as exc:
            ui_feedback.set_status_label(status_lbl, str(exc), ok=False, duration=4000)

    def _delete_row(index: int) -> None:
        items = list(getattr(dlg, '_todo_items', []) or [])
        if index < 0 or index >= len(items):
            return
        items.pop(index)
        dlg._todo_items = items
        _refresh_table()
        _save_items()

    def _handle_add() -> None:
        if todo_input is None:
            return
        try:
            text = _validate_todo_input()
            warning = todo_input.property('input_warning') or ''
        except Exception as exc:
            ui_feedback.set_status_label(status_lbl, str(exc), ok=False, duration=4000)
            return

        items = list(getattr(dlg, '_todo_items', []) or [])
        if len(items) >= int(config.TODO_ROWS):
            ui_feedback.set_status_label(
                status_lbl,
                "List is full. Delete items to free up rows",
                ok=False,
                duration=4000,
            )
            return

        items.append(text)
        dlg._todo_items = items
        dlg._todo_added = True
        _refresh_table()
        _save_items()

        try:
            todo_input.clear()
        except Exception:
            pass
        _update_add_state()
        if warning:
            ui_feedback.set_warning_status_label(status_lbl, warning, duration=4000)
        try:
            todo_input.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass

    def _validate_and_focus_add() -> None:
        if todo_input is None:
            return
        try:
            if not (todo_input.text() or '').strip():
                return
            _validate_todo_input()
        except Exception as exc:
            ui_feedback.set_status_label(status_lbl, str(exc), ok=False, duration=4000)
            try:
                todo_input.setFocus(Qt.OtherFocusReason)
                todo_input.selectAll()
            except Exception:
                pass
            return
        try:
            if add_btn is not None and add_btn.isEnabled():
                add_btn.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass

    if todo_input is not None:
        try:
            todo_input.returnPressed.connect(_validate_and_focus_add)
        except Exception:
            pass
        try:
            todo_input.textChanged.connect(lambda _=None: ui_feedback.clear_status_label(status_lbl))
        except Exception:
            pass
        try:
            todo_input.textChanged.connect(lambda _=None: _update_add_state())
        except Exception:
            pass

    if add_btn is not None:
        try:
            add_btn.clicked.connect(_handle_add)
        except Exception:
            pass

    try:
        orig_reject = getattr(dlg, 'reject', None)
    except Exception:
        orig_reject = None

    try:
        if callable(orig_reject):
            def _reject_with_default_msg():
                try:
                    if not getattr(dlg, 'main_status_msg', None):
                        msg = 'todo item added' if getattr(dlg, '_todo_added', False) else 'todo dialog closed'
                        set_dialog_info(dlg, msg, duration=3000)
                except Exception:
                    pass
                try:
                    orig_reject()
                except Exception:
                    pass
            dlg.reject = _reject_with_default_msg
    except Exception:
        pass

    dlg._todo_items = todo_state.load_todos()
    dlg._todo_added = False
    _configure_table()
    _refresh_table()
    _update_add_state()

    try:
        if todo_input is not None:
            todo_input.setFocus(Qt.OtherFocusReason)
    except Exception:
        pass

    return dlg
