import os
from typing import Optional

from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtWidgets import QLineEdit, QPushButton, QLabel

from modules.db_operation.held_sale_committer import HeldSaleCommitter
from modules.ui_utils import input_handler, input_validation, ui_feedback
from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui,
    require_widgets,
    set_dialog_main_status_max,
    report_exception_post_close,
)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')
HOLD_SALES_UI = os.path.join(UI_DIR, 'hold_sales.ui')


class _ReactivePlaceholderFilter(QObject):
    def __init__(self, templates: dict[QLineEdit, str], parent=None):
        super().__init__(parent)
        self._templates = templates or {}

    def eventFilter(self, obj, event):
        template = self._templates.get(obj)
        if template is None:
            return super().eventFilter(obj, event)

        try:
            if event.type() == QEvent.FocusIn:
                obj.setPlaceholderText("")
            elif event.type() == QEvent.FocusOut:
                if not (obj.text() or "").strip():
                    obj.setPlaceholderText(template)
        except Exception:
            pass
        return super().eventFilter(obj, event)


def _show_validation_error(status_label: QLabel, widget: QLineEdit, message: str) -> None:
    ui_feedback.set_status_label(status_label, message, ok=False)
    widget.setFocus(Qt.OtherFocusReason)
    widget.selectAll()


def _build_sales_snapshot(parent) -> list[dict]:
    if parent is None:
        return []
    try:
        if hasattr(parent, "_build_sale_items_snapshot"):
            return list(parent._build_sale_items_snapshot() or [])
    except Exception:
        pass
    return []


def launch_hold_sales_dialog(parent=None):
    qss_path = os.path.join(BASE_DIR, 'assets', 'dialog.qss')
    dlg = build_dialog_from_ui(
        HOLD_SALES_UI,
        host_window=parent,
        dialog_name='Hold Sales',
        qss_path=qss_path,
        frameless=True,
        application_modal=True,
    )
    if dlg is None:
        return None

    widgets = require_widgets(dlg, {
        'name_in': (QLineEdit, 'holdSalesCustomerLineEdit'),
        'note_in': (QLineEdit, 'holdSalesNoteLineEdit'),
        'status_lbl': (QLabel, 'holdSalesStatusLabel'),
        'ok_btn': (QPushButton, 'btnHoldSalesOk'),
        'cancel_btn': (QPushButton, 'btnHoldSalesCancel'),
    })
    close_btn = dlg.findChild(QPushButton, 'customCloseBtn')

    name_in = widgets['name_in']
    note_in = widgets['note_in']
    status_lbl = widgets['status_lbl']
    ok_btn = widgets['ok_btn']
    cancel_btn = widgets['cancel_btn']

    name_in.setReadOnly(False)
    note_in.setReadOnly(False)
    name_in.setFocusPolicy(Qt.StrongFocus)
    note_in.setFocusPolicy(Qt.StrongFocus)

    placeholders = {}
    for le in (name_in, note_in):
        ui_default = (le.placeholderText() or "").strip()
        if not ui_default:
            ui_default = (le.text() or "").strip()
        placeholders[le] = ui_default
        le.clear()
        le.setPlaceholderText(ui_default)

    placeholder_filter = _ReactivePlaceholderFilter(placeholders, dlg)
    dlg._hold_sales_placeholder_filter = placeholder_filter
    name_in.installEventFilter(placeholder_filter)
    note_in.installEventFilter(placeholder_filter)

    def _refresh_ok_enabled() -> None:
        customer = input_handler.canonicalize_title_text(name_in.text())
        ok_customer, _ = input_validation.validate_customer(customer)
        note_val = input_handler.canonicalize_title_text(note_in.text())
        ok_note, _ = input_validation.validate_note(note_val)
        ok_btn.setEnabled(bool(ok_customer and ok_note))

    ok_btn.setEnabled(False)

    def _clear_inline_status(*_args):
        ui_feedback.clear_status_label(status_lbl)
        _refresh_ok_enabled()

    name_in.textEdited.connect(_clear_inline_status)
    note_in.textEdited.connect(_clear_inline_status)

    def _on_name_enter() -> None:
        try:
            customer_name = input_handler.handle_customer_input(name_in)
            name_in.setText(customer_name)
            note_in.setFocus(Qt.OtherFocusReason)
            note_in.selectAll()
        except ValueError as exc:
            _show_validation_error(status_lbl, name_in, str(exc))

    def _on_note_enter() -> None:
        try:
            note_text = input_handler.handle_note_input(note_in)
            note_in.setText(note_text)
            ok_btn.setFocus(Qt.OtherFocusReason)
        except ValueError as exc:
            _show_validation_error(status_lbl, note_in, str(exc))

    name_in.returnPressed.connect(_on_name_enter)
    note_in.returnPressed.connect(_on_note_enter)

    hold_committer = HeldSaleCommitter()

    def _handle_ok() -> None:
        try:
            customer_name = input_handler.handle_customer_input(name_in)
            name_in.setText(customer_name)
        except ValueError as exc:
            _show_validation_error(status_lbl, name_in, str(exc))
            return

        try:
            note_text = input_handler.handle_note_input(note_in)
            note_in.setText(note_text)
        except ValueError as exc:
            _show_validation_error(status_lbl, note_in, str(exc))
            return

        sales_items = _build_sales_snapshot(parent)
        if not sales_items:
            _show_validation_error(status_lbl, name_in, "No active sale to hold")
            return

        try:
            receipt_no = hold_committer.commit_hold_sale(
                customer_name=customer_name,
                note=note_text,
                sales_items=sales_items,
            )
            dlg.held_receipt_no = receipt_no

            if parent is not None and hasattr(parent, "_clear_sales_table_core"):
                parent._clear_sales_table_core()
            panel = getattr(parent, 'payment_panel_controller', None) if parent is not None else None
            if panel is not None:
                panel.clear_payment_frame()

            set_dialog_main_status_max(dlg, "Sale held successfully.", level='info', duration=4000)
            dlg.accept()
        except Exception as exc:
            report_exception_post_close(
                dlg,
                "Hold sale",
                exc,
                user_message="Error: Unable to hold sale (see error.log)",
                level='error',
                duration=6000,
            )
            ui_feedback.set_status_label(status_lbl, "Unable to hold sale.", ok=False)

    ok_btn.clicked.connect(_handle_ok)
    cancel_btn.clicked.connect(dlg.reject)
    if close_btn is not None:
        close_btn.clicked.connect(dlg.reject)

    name_in.setFocus(Qt.OtherFocusReason)
    name_in.selectAll()
    _refresh_ok_enabled()

    return dlg
