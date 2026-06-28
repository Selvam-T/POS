"""Receipt history dialog controller."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from PyQt5.QtCore import QDate, QObject, Qt, QEvent, QTimer
from PyQt5.QtGui import QFont, QTextOption
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QTableWidget,
)

import modules.db_operation as dbop
from modules.devices import print_helper
from modules.payment.receipt_generator import generate_receipt_text
from modules.ui_utils import input_handler, ui_feedback
from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui,
    build_error_fallback_dialog,
    log_exception_traceback_and_postclose_statusBar,
    log_error_message_and_postclose_statusBar,
    require_widgets,
    set_dialog_info,
    set_dialog_main_status_max,
)
from modules.ui_utils.error_logger import log_error_message
from modules.date_time import (
    clamp_date_range_bounds,
    init_date_range_bounds,
    set_locked_property,
)
from modules.table_ui.receipt_table_helpers import (
    configure_receipt_table,
    fill_receipt_table,
    selected_receipt,
    sort_receipts_by_column,
)
from config import QSS_DIR, UI_DIR

QSS_PATH = os.path.join(QSS_DIR, "dialog.qss")
UI_PATH = os.path.join(UI_DIR, "receipt_menu.ui")


STATUS_CHOICES = ("All", "Paid", "Unpaid", "Cancelled")
DATE_TYPE_CHOICES = ("All", "Transaction date", "Payment date", "Cancellation date")

def _status_value(text: str) -> str:
    value = str(text or "All").strip().upper()
    if value in ("PAID", "UNPAID", "CANCELLED"):
        return value
    return "ALL"


def _date_type_value(text: str) -> str:
    value = str(text or "All").strip().lower()
    if value.startswith("transaction"):
        return "TRANSACTION DATE"
    if value.startswith("payment"):
        return "PAYMENT DATE"
    if value.startswith("cancellation"):
        return "CANCELLATION DATE"
    return "ALL"


def _combo_text(combo: QComboBox) -> str:
    try:
        return str(combo.currentText() or "").strip()
    except Exception:
        return ""


def _line_text(widget) -> str:
    try:
        return str(widget.text() or "").strip()
    except Exception:
        return ""


def _date_text(widget: QDateEdit) -> str:
    try:
        return widget.date().toString("yyyy-MM-dd")
    except Exception:
        return QDate.currentDate().toString("yyyy-MM-dd")

def _set_status(label: QLabel, message: str, *, ok: bool = True, duration: int = 3500) -> None:
    try:
        ui_feedback.set_status_label(label, message, ok=ok, duration=duration)
    except Exception:
        try:
            label.setText(message)
        except Exception:
            pass


def _set_warning(label: QLabel, message: str, *, duration: int = 3500) -> None:
    try:
        ui_feedback.set_warning_status_label(label, message, duration=duration)
    except Exception:
        _set_status(label, message, ok=False, duration=duration)


def launch_receipt_dialog(host_window, *args, **kwargs):
    """Open Receipt History dialog as a modal frameless panel."""
    dlg = build_dialog_from_ui(
        UI_PATH,
        host_window=host_window,
        dialog_name="receipt_menu",
        qss_path=QSS_PATH,
    )
    if dlg is None:
        return build_error_fallback_dialog(host_window, "Receipt History", QSS_PATH)

    try:
        widgets = require_widgets(
            dlg,
            {
                "close_btn": (QPushButton, "customCloseBtn"),
                "table": (QTableWidget, "receiptTable"),
                "status_combo": (QComboBox, "receiptStatusComboBox"),
                "date_type_combo": (QComboBox, "receiptDateTypeComboBox"),
                "from_date": (QDateEdit, "receiptFromDateEdit"),
                "to_date": (QDateEdit, "receiptToDateEdit"),
                "receipt_no": (QLineEdit, "receiptNumberLineEdit"),
                "product_code": (QLineEdit, "receiptProductCodeLineEdit"),
                "product_name": (QLineEdit, "receiptProductNameLineEdit"),
                "preview": (QPlainTextEdit, "receiptPreviewLabel"),
                "search_btn": (QPushButton, "searchReceiptBtn"),
                "reset_btn": (QPushButton, "resetReceiptBtn"),
                "print_radio": (QRadioButton, "receiptPrintRadioBtn"),
                "void_radio": (QRadioButton, "receiptVoidRadioBtn"),
                "note_lbl": (QLabel, "receiptNoteFieldLbl"),
                "note": (QLineEdit, "receiptNoteLineEdit"),
                "ok_btn": (QPushButton, "btnReceiptOk"),
                "close_action_btn": (QPushButton, "btnReceiptClose"),
                "status_lbl": (QLabel, "receiptStatusLabel"),
            },
            hard_fail=True,
        )
    except Exception as exc:
        try:
            log_error_message(f"receipt_menu: require_widgets failed: {exc}")
        except Exception:
            pass
        return build_error_fallback_dialog(host_window, "Receipt History", QSS_PATH)

    table: QTableWidget = widgets["table"]
    status_combo: QComboBox = widgets["status_combo"]
    date_type_combo: QComboBox = widgets["date_type_combo"]
    from_date: QDateEdit = widgets["from_date"]
    to_date: QDateEdit = widgets["to_date"]
    product_name_line: QLineEdit = widgets["product_name"]
    preview: QPlainTextEdit = widgets["preview"]
    status_lbl: QLabel = widgets["status_lbl"]
    product_code_line: QLineEdit = widgets["product_code"]
    note_lbl: QLabel = widgets["note_lbl"]
    note: QLineEdit = widgets["note"]
    print_radio: QRadioButton = widgets["print_radio"]
    void_radio: QRadioButton = widgets["void_radio"]

    def _current_table_status() -> str:
        return _status_value(_combo_text(status_combo))

    configure_receipt_table(table, status=_current_table_status())

    try:
        preview.setReadOnly(True)
        preview.setFont(QFont("Consolas", 10))
        option = preview.document().defaultTextOption()
        option.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        option.setWrapMode(QTextOption.NoWrap)
        preview.document().setDefaultTextOption(option)
    except Exception:
        pass

    def _populate_combos() -> None:
        try:
            status_combo.blockSignals(True)
            status_combo.clear()
            status_combo.addItems(list(STATUS_CHOICES))
            status_combo.setCurrentText("All")
        finally:
            try:
                status_combo.blockSignals(False)
            except Exception:
                pass
        try:
            date_type_combo.blockSignals(True)
            date_type_combo.clear()
            date_type_combo.addItems(list(DATE_TYPE_CHOICES))
            date_type_combo.setCurrentText("All")
        finally:
            try:
                date_type_combo.blockSignals(False)
            except Exception:
                pass

    def _populate_product_names() -> None:
        try:
            if not dbop.PRODUCT_CACHE:
                dbop.load_product_cache()
        except Exception as exc:
            try:
                log_error_message(f"receipt_menu: product cache load failed: {exc}")
            except Exception:
                pass
        names = []
        seen = set()
        for rec in (dbop.PRODUCT_CACHE or {}).values():
            name_text = str(rec[0] or "").strip() if rec else ""
            key = name_text.casefold()
            if name_text and key not in seen:
                names.append(name_text)
                seen.add(key)
        names.sort(key=str.casefold)

        try:
            product_name_line.clear()
            input_handler.setup_name_search_lineedit(
                product_name_line,
                names,
                trigger_on_finish=False,
            )
        except Exception:
            pass

    def _set_product_name_text(name_text: str) -> None:
        product_name_line.setText(str(name_text or "").strip())

    def _set_input_error(widget, has_error: bool) -> None:
        try:
            widget.setProperty("input_error", bool(has_error))
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()
        except Exception:
            pass

    def _focus_search_btn() -> None:
        QTimer.singleShot(0, lambda: widgets["search_btn"].setFocus(Qt.OtherFocusReason))

    barcode_warning = ui_feedback.create_auto_clearing_warning_label(
        status_lbl,
        ui_feedback.BARCODE_WARNING_TEXT,
        duration=4500,
    )

    def _mark_product_error(widget, message: str) -> None:
        _set_input_error(widget, True)
        _set_status(status_lbl, message, ok=False)
        try:
            widget.setFocus(Qt.OtherFocusReason)
            widget.selectAll()
        except Exception:
            pass

    def _lookup_product_by_code(code_text: str) -> Optional[Dict[str, Any]]:
        try:
            return input_handler.get_coordinator_lookup(code_text, "code")
        except Exception:
            return None

    def _lookup_product_by_name(name_text: str) -> Optional[Dict[str, Any]]:
        try:
            return input_handler.get_coordinator_lookup(name_text, "name")
        except Exception:
            return None

    def _sync_product_from_code(*, show_error: bool = False) -> Optional[Dict[str, Any]]:
        code_text = _line_text(widgets["product_code"])
        if not code_text:
            _set_product_name_text("")
            _set_input_error(widgets["product_code"], False)
            return None
        result = _lookup_product_by_code(code_text)
        if result:
            widgets["product_code"].setText(str(result.get("code") or code_text))
            _set_product_name_text(str(result.get("name") or ""))
            _set_input_error(widgets["product_code"], False)
            _set_input_error(product_name_line, False)
            return result
        _set_product_name_text("")
        if show_error:
            _mark_product_error(widgets["product_code"], "Product code not found.")
        return None

    def _sync_product_from_name(*, show_error: bool = False) -> Optional[Dict[str, Any]]:
        name_text = _line_text(product_name_line)
        if not name_text:
            widgets["product_code"].clear()
            _set_input_error(product_name_line, False)
            return None
        result = _lookup_product_by_name(name_text)
        if result:
            widgets["product_code"].setText(str(result.get("code") or ""))
            _set_product_name_text(str(result.get("name") or name_text))
            _set_input_error(product_name_line, False)
            _set_input_error(widgets["product_code"], False)
            return result
        widgets["product_code"].clear()
        if show_error:
            _mark_product_error(product_name_line, "Product name not found.")
        return None

    def _clear_product_name_when_code_edited(_text=None) -> None:
        _set_input_error(widgets["product_code"], False)
        _set_product_name_text("")

    def _clear_barcode_warning_when_code_cleared(_text=None) -> None:
        try:
            if _line_text(product_code_line):
                return
        except Exception:
            return
        barcode_warning.clear()

    def _clear_product_code_when_name_edited(_text=None) -> None:
        _set_input_error(product_name_line, False)
        widgets["product_code"].clear()

    def _commit_product_code() -> None:
        if not _line_text(widgets["product_code"]):
            _set_input_error(widgets["product_code"], False)
            _focus_search_btn()
            return
        if _sync_product_from_code(show_error=True):
            _focus_search_btn()

    def _commit_product_name() -> None:
        if not _line_text(product_name_line):
            _set_input_error(product_name_line, False)
            _focus_search_btn()
            return
        if _sync_product_from_name(show_error=True):
            _focus_search_btn()

    def _barcode_override(barcode: str) -> bool:
        code = str(barcode or "").strip()
        if not code:
            return True
        widgets["product_code"].setText(code)
        _sync_product_from_code(show_error=True)
        if not bool(widgets["product_code"].property("input_error")):
            _focus_search_btn()
        return True

    def _set_note_locked(locked: bool) -> None:
        locked = bool(locked)
        try:
            note.setEnabled(not locked)
            note.setReadOnly(locked)
            note.setFocusPolicy(Qt.NoFocus if locked else Qt.StrongFocus)
            set_locked_property(note, locked)
            set_locked_property(note_lbl, locked)
        except Exception:
            pass
        try:
            if locked:
                note.clear()
        except Exception:
            pass

    def _sync_action_state() -> None:
        row = selected_receipt(table)
        status = str((row or {}).get("status") or "").strip().upper()
        can_void = status == "UNPAID"
        try:
            void_radio.setEnabled(can_void)
            void_radio.setFocusPolicy(Qt.StrongFocus if can_void else Qt.NoFocus)
            set_locked_property(void_radio, not can_void)
        except Exception:
            pass
        if not can_void and void_radio.isChecked():
            try:
                print_radio.setChecked(True)
            except Exception:
                pass
        _set_note_locked(not (can_void and void_radio.isChecked()))

    def _build_search_params() -> Dict[str, Any]:
        return {
            "status": _status_value(_combo_text(status_combo)),
            "date_type": _date_type_value(_combo_text(date_type_combo)),
            "from_date": _date_text(from_date),
            "to_date": _date_text(to_date),
            "receipt_no": _line_text(widgets["receipt_no"]),
            "product_code": _line_text(widgets["product_code"]),
        }

    def _render_preview(row: Optional[Dict[str, Any]]) -> None:
        if not row:
            preview.setPlainText("Selected receipt preview appears here")
            _sync_action_state()
            return
        receipt_no = str(row.get("receipt_no") or "").strip()
        if not receipt_no:
            preview.setPlainText("Selected receipt preview appears here")
            _sync_action_state()
            return
        try:
            receipt_text = generate_receipt_text(receipt_no)
            preview.setPlainText(receipt_text)
        except Exception as exc:
            preview.setPlainText("Receipt preview unavailable.")
            _set_status(status_lbl, f"Receipt preview failed: {exc}", ok=False)
            try:
                log_error_message(f"receipt_menu: preview failed for {receipt_no}: {exc}")
            except Exception:
                pass
        finally:
            _sync_action_state()

    def _select_first_row() -> None:
        try:
            if table.rowCount() <= 0:
                _render_preview(None)
                return
            table.selectRow(0)
            item = table.item(0, 0)
            if item is not None:
                table.setCurrentItem(item)
            _render_preview(selected_receipt(table))
        except Exception:
            _render_preview(None)

    _sort_state = {"column": None, "order": Qt.AscendingOrder}
    _active_table_layout = {"status": _current_table_status()}

    def _sort_receipts_by_column(column: int) -> None:
        sort_receipts_by_column(
            table,
            column,
            _sort_state,
            select_first_row=_select_first_row,
            status=_current_table_status(),
        )

    def _fill_table(rows) -> None:
        table_status = _current_table_status()
        if _active_table_layout.get("status") != table_status:
            configure_receipt_table(table, status=table_status)
            _sort_state["column"] = None
            _sort_state["order"] = Qt.AscendingOrder
            _active_table_layout["status"] = table_status
        fill_receipt_table(table, rows, status=table_status)
        _select_first_row()

    def _refresh_receipts(*, show_count: bool = False) -> None:
        try:
            try:
                if from_date.date() > to_date.date():
                    _set_warning(status_lbl, "From date cannot be after To date.")
                    return
            except Exception:
                pass
            params = _build_search_params()
            rows = dbop.search_receipts(**params)
            _fill_table(rows)
            if show_count:
                if rows:
                    _set_status(status_lbl, f"{len(rows)} receipt(s) found.", ok=True)
                else:
                    _set_status(status_lbl, "No receipts found.", ok=False)
        except Exception as exc:
            _fill_table([])
            _set_status(status_lbl, f"Receipt search failed: {exc}", ok=False)
            log_exception_traceback_and_postclose_statusBar(
                dlg,
                "Receipt search failed",
                exc,
                user_message=f"Error: Receipt search failed: {exc}",
                level="error",
                duration=5000,
            )

    def _run_search() -> None:
        _refresh_receipts(show_count=True)
        try:
            widgets["reset_btn"].setFocus(Qt.OtherFocusReason)
        except Exception:
            pass

    def _reset_filters() -> None:
        today = QDate.currentDate()
        try:
            status_combo.setCurrentText("All")
            date_type_combo.setCurrentText("All")
            init_date_range_bounds(from_date, to_date, today=today)
            widgets["receipt_no"].clear()
            widgets["product_code"].clear()
            product_name_line.clear()
            _set_input_error(widgets["product_code"], False)
            _set_input_error(product_name_line, False)
            print_radio.setChecked(True)
            note.clear()
        except Exception:
            pass
        _refresh_receipts(show_count=True)
        try:
            status_combo.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass

    def _on_selection_changed() -> None:
        _render_preview(selected_receipt(table))

    def _print_selected() -> None:
        row = selected_receipt(table)
        if not row:
            _set_warning(status_lbl, "Select a receipt first.")
            return
        receipt_no = str(row.get("receipt_no") or "").strip()
        try:
            receipt_text = generate_receipt_text(receipt_no)
            print_result = print_helper.print_receipt_with_fallback(
                receipt_text,
                blocking=True,
                context="Receipt History",
            )
            if print_result.get("ok"):
                mode = str(print_result.get("mode") or "printer")
                target = "console" if mode == "console" else "printer"
                _set_status(status_lbl, f"Receipt {receipt_no} sent to {target}.", ok=True)
                set_dialog_info(dlg, f"Receipt {receipt_no} printed.", duration=3500)
            else:
                _set_status(status_lbl, "Printer unavailable or receipt not sent.", ok=False)
                log_error_message_and_postclose_statusBar(
                    dlg,
                    "Receipt print failed",
                    f"Printer send failed for receipt {receipt_no}: {print_result.get('error') or 'unknown'}",
                    user_message=f"Error: Receipt print failed for {receipt_no}",
                    level="error",
                    duration=5000,
                )
        except Exception as exc:
            _set_status(status_lbl, f"Print failed: {exc}", ok=False)
            log_exception_traceback_and_postclose_statusBar(
                dlg,
                "Receipt print failed",
                exc,
                user_message=f"Error: Receipt print failed: {exc}",
                level="error",
                duration=5000,
            )

    def _void_selected() -> None:
        row = selected_receipt(table)
        if not row:
            _set_warning(status_lbl, "Select an unpaid receipt first.")
            return
        receipt_no = str(row.get("receipt_no") or "").strip()
        status = str(row.get("status") or "").strip().upper()
        if status != "UNPAID":
            _set_warning(status_lbl, "Only UNPAID receipts can be voided.")
            _sync_action_state()
            return
        try:
            ok = dbop.void_unpaid_receipt(
                receipt_id=row.get("receipt_id"),
                receipt_no=receipt_no,
                note=_line_text(note),
            )
            if not ok:
                _set_status(status_lbl, "Receipt was not voided. It may already be paid or cancelled.", ok=False)
                log_error_message_and_postclose_statusBar(
                    dlg,
                    "Receipt void failed",
                    f"void_unpaid_receipt returned false for receipt {receipt_no}",
                    user_message=f"Error: Receipt {receipt_no} was not voided.",
                    level="error",
                    duration=5000,
                )
                return
            _set_status(status_lbl, f"Receipt {receipt_no} voided.", ok=True)
            set_dialog_main_status_max(
                dlg,
                f"Receipt {receipt_no} voided.",
                level="info",
                duration=3500,
            )
            print_radio.setChecked(True)
            note.clear()
            _refresh_receipts(show_count=False)
        except Exception as exc:
            _set_status(status_lbl, f"Void failed: {exc}", ok=False)
            log_exception_traceback_and_postclose_statusBar(
                dlg,
                "Receipt void failed",
                exc,
                user_message=f"Error: Receipt void failed: {exc}",
                level="error",
                duration=5000,
            )

    def _on_ok() -> None:
        try:
            if void_radio.isChecked():
                _void_selected()
            else:
                _print_selected()
        finally:
            QTimer.singleShot(0, lambda: widgets["close_action_btn"].setFocus(Qt.OtherFocusReason))

    def _close_dialog() -> None:
        try:
            if not getattr(dlg, "main_status_msg", None):
                set_dialog_info(dlg, "Receipt dialog closed.", duration=3000)
        except Exception:
            pass
        try:
            dlg.reject()
        except Exception:
            pass

    class _ReceiptTableFilter(QObject):
        def eventFilter(self, obj, event):
            if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if obj is widgets["product_code"]:
                    _commit_product_code()
                    return True
                if obj is product_name_line:
                    _commit_product_name()
                    return True
                if obj in (status_combo, date_type_combo, widgets["receipt_no"]):
                    try:
                        widgets["search_btn"].setFocus(Qt.OtherFocusReason)
                    except Exception:
                        pass
                    return True
                if obj is from_date or obj is getattr(from_date, "lineEdit", lambda: None)():
                    try:
                        to_date.setFocus(Qt.OtherFocusReason)
                    except Exception:
                        pass
                    return True
                if obj is to_date or obj is getattr(to_date, "lineEdit", lambda: None)():
                    try:
                        widgets["search_btn"].setFocus(Qt.OtherFocusReason)
                    except Exception:
                        pass
                    return True
            if obj is table and event.type() == QEvent.KeyPress:
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    _render_preview(selected_receipt(table))
                    return True
            if obj is note and event.type() == QEvent.KeyPress:
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    if void_radio.isChecked() and note.isEnabled():
                        widgets["ok_btn"].setFocus(Qt.OtherFocusReason)
                        return True
            return False

    _event_filter = _ReceiptTableFilter(dlg)
    try:
        table.installEventFilter(_event_filter)
        note.installEventFilter(_event_filter)
        status_combo.installEventFilter(_event_filter)
        date_type_combo.installEventFilter(_event_filter)
        from_date.installEventFilter(_event_filter)
        to_date.installEventFilter(_event_filter)
        if from_date.lineEdit() is not None:
            from_date.lineEdit().installEventFilter(_event_filter)
        if to_date.lineEdit() is not None:
            to_date.lineEdit().installEventFilter(_event_filter)
        widgets["receipt_no"].installEventFilter(_event_filter)
        widgets["product_code"].installEventFilter(_event_filter)
        product_name_line.installEventFilter(_event_filter)
        dlg._receipt_event_filter = _event_filter
    except Exception:
        pass

    _populate_combos()
    _populate_product_names()
    today = QDate.currentDate()
    try:
        init_date_range_bounds(from_date, to_date, today=today)
        from_date.setCalendarPopup(True)
        to_date.setCalendarPopup(True)
    except Exception:
        pass
    try:
        print_radio.setChecked(True)
        widgets["ok_btn"].setDefault(True)
        widgets["ok_btn"].setAutoDefault(True)
    except Exception:
        pass
    _set_note_locked(True)

    try:
        table.itemSelectionChanged.connect(_on_selection_changed)
        table.horizontalHeader().sectionClicked.connect(_sort_receipts_by_column)
        from_date.dateChanged.connect(lambda _date: clamp_date_range_bounds(from_date, to_date))
        to_date.dateChanged.connect(lambda _date: clamp_date_range_bounds(from_date, to_date))
        widgets["search_btn"].clicked.connect(_run_search)
        widgets["reset_btn"].clicked.connect(_reset_filters)
        widgets["ok_btn"].clicked.connect(_on_ok)
        widgets["close_action_btn"].clicked.connect(_close_dialog)
        widgets["close_btn"].clicked.connect(_close_dialog)
        print_radio.toggled.connect(lambda _checked: _sync_action_state())
        void_radio.toggled.connect(lambda checked: (_sync_action_state(), checked and note.setFocus(Qt.OtherFocusReason)))
        widgets["product_code"].textEdited.connect(_clear_product_name_when_code_edited)
        widgets["product_code"].textEdited.connect(_clear_barcode_warning_when_code_cleared)
        product_name_line.textEdited.connect(_clear_product_code_when_name_edited)
    except Exception as exc:
        try:
            log_error_message(f"receipt_menu: signal wiring failed: {exc}")
        except Exception:
            pass

    try:
        dlg.barcode_override_handler = _barcode_override
    except Exception:
        pass

    _refresh_receipts(show_count=False)
    QTimer.singleShot(0, lambda: status_combo.setFocus(Qt.OtherFocusReason))

    return dlg
