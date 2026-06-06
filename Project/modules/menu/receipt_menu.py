"""Receipt history dialog controller."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QDate, QObject, Qt, QEvent, QTimer
from PyQt5.QtGui import QFont, QTextOption
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
)

import modules.db_operation as dbop
from modules.devices.printer_and_drawer import print_receipt
from modules.payment.receipt_generator import generate_receipt_text
from modules.ui_utils import input_handler, ui_feedback
from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui,
    build_error_fallback_dialog,
    log_exception_traceback_and_postclose_statusBar,
    require_widgets,
    set_dialog_info,
    set_dialog_main_status_max,
)
from modules.ui_utils.error_logger import log_error_message
from modules.date_time import format_date, format_datetime, set_locked_property
from modules.table.table_widget_helpers import (
    apply_table_columns,
    configure_readonly_row_selection_table,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, "ui")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
QSS_PATH = os.path.join(ASSETS_DIR, "dialog.qss")
UI_PATH = os.path.join(UI_DIR, "receipt_menu.ui")


STATUS_CHOICES = ("All", "Paid", "Unpaid", "Cancelled")
DATE_TYPE_CHOICES = ("All", "Transaction date", "Payment date", "Cancellation date")
TABLE_COLUMNS = (
    "No.",
    "Receipt ↑↓",
    "Status ↑↓",
    "Transact ↑↓",
    "Paid ↑↓",
    "Cancelled ↑↓",
    "Amount ↑↓",
)
TABLE_HEADER_TOOLTIPS = (
    "Serial number",
    "Receipt number",
    "Receipt status",
    "Transaction date and time",
    "Payment date and time",
    "Cancellation date and time",
    "Receipt amount",
)


class ReceiptTableItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
            left = self.data(Qt.UserRole + 10)
            right = other.data(Qt.UserRole + 10)
            if left is not None and right is not None:
                return left < right
        except Exception:
            pass
        return super().__lt__(other)


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


def _format_amount(value: Any) -> str:
    try:
        return f"{float(value or 0.0):.2f}"
    except Exception:
        return "0.00"


def _sort_amount(value: Any) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _sort_text(value: Any) -> str:
    return str(value or "").strip().casefold()


def _sort_date(value: Any) -> str:
    return str(value or "").strip()


def _format_dt(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "—"
    try:
        return format_datetime(raw, fmt="%d/%m/%y %H:%M", lower_ampm=False)
    except Exception:
        try:
            return format_date(raw)
        except Exception:
            return raw


def _format_dt_full(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        return format_datetime(raw)
    except Exception:
        try:
            return format_date(raw)
        except Exception:
            return raw


def _configure_receipt_table(table: QTableWidget) -> None:
    """Configure the receipt history table.

    Shared helpers handle the common list-table column setup, header
    tooltips, and read-only row-selection behavior. Receipt History keeps
    row item creation, row tooltips, sort keys, and header-click sorting
    local because they depend on this dialog's receipt data shape.
    """
    apply_table_columns(table, [
        {
            "label": TABLE_COLUMNS[0],
            "mode": QHeaderView.Fixed,
            "width": 50,
            "align": Qt.AlignCenter,
            "tooltip": TABLE_HEADER_TOOLTIPS[0],
        },
        {
            "label": TABLE_COLUMNS[1],
            "mode": QHeaderView.Stretch,
            "align": Qt.AlignCenter,
            "tooltip": TABLE_HEADER_TOOLTIPS[1],
        },
        {
            "label": TABLE_COLUMNS[2],
            "mode": QHeaderView.Fixed,
            "width": 105,
            "align": Qt.AlignCenter,
            "tooltip": TABLE_HEADER_TOOLTIPS[2],
        },
        {
            "label": TABLE_COLUMNS[3],
            "mode": QHeaderView.Fixed,
            "width": 150,
            "align": Qt.AlignCenter,
            "tooltip": TABLE_HEADER_TOOLTIPS[3],
        },
        {
            "label": TABLE_COLUMNS[4],
            "mode": QHeaderView.Fixed,
            "width": 150,
            "align": Qt.AlignCenter,
            "tooltip": TABLE_HEADER_TOOLTIPS[4],
        },
        {
            "label": TABLE_COLUMNS[5],
            "mode": QHeaderView.Fixed,
            "width": 150,
            "align": Qt.AlignCenter,
            "tooltip": TABLE_HEADER_TOOLTIPS[5],
        },
        {
            "label": TABLE_COLUMNS[6],
            "mode": QHeaderView.Fixed,
            "width": 115,
            "align": Qt.AlignCenter,
            "tooltip": TABLE_HEADER_TOOLTIPS[6],
        },
    ])

    header = table.horizontalHeader()
    try:
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.setSortIndicator(1, Qt.AscendingOrder)
    except Exception:
        pass

    configure_readonly_row_selection_table(table, sorting_enabled=False)


def _selected_receipt(table: QTableWidget) -> Optional[Dict[str, Any]]:
    try:
        indexes = table.selectionModel().selectedRows()
    except Exception:
        indexes = []
    if not indexes:
        return None
    try:
        row = indexes[0].row()
        item = table.item(row, 0)
        data = item.data(Qt.UserRole) if item is not None else None
        return dict(data) if isinstance(data, dict) else None
    except Exception:
        return None


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
                "product_name": (QComboBox, "receiptProductNameComboBox"),
                "preview": (QPlainTextEdit, "receiptPreviewLabel"),
                "search_btn": (QPushButton, "searchReceiptBtn"),
                "reset_btn": (QPushButton, "resetReceiptBtn"),
                "print_radio": (QRadioButton, "receiptPrintRadioBtn"),
                "void_radio": (QRadioButton, "receiptVoidRadioBtn"),
                "note_lbl": (QLabel, "receiptNoteFieldLbl"),
                "note": (QLineEdit, "receiptNoteLineEdit"),
                "ok_btn": (QPushButton, "btnReceiptOk"),
                "cancel_btn": (QPushButton, "btnReceiptCancel"),
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
    product_name_combo: QComboBox = widgets["product_name"]
    preview: QPlainTextEdit = widgets["preview"]
    status_lbl: QLabel = widgets["status_lbl"]
    note_lbl: QLabel = widgets["note_lbl"]
    note: QLineEdit = widgets["note"]
    print_radio: QRadioButton = widgets["print_radio"]
    void_radio: QRadioButton = widgets["void_radio"]

    _configure_receipt_table(table)

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
            product_name_combo.blockSignals(True)
            product_name_combo.clear()
            product_name_combo.addItems(names)
            product_name_combo.setCurrentIndex(-1)
            product_name_combo.setEditText("")
        finally:
            try:
                product_name_combo.blockSignals(False)
            except Exception:
                pass
        try:
            line = product_name_combo.lineEdit()
            if line is not None:
                input_handler.setup_name_search_lineedit(
                    line,
                    names,
                    trigger_on_finish=False,
                )
        except Exception:
            pass

    def _set_product_name_text(name_text: str) -> None:
        try:
            product_name_combo.setEditText(str(name_text or "").strip())
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
            return None
        result = _lookup_product_by_code(code_text)
        if result:
            try:
                widgets["product_code"].setText(str(result.get("code") or code_text))
            except Exception:
                pass
            _set_product_name_text(str(result.get("name") or ""))
            return result
        _set_product_name_text("")
        if show_error:
            _set_status(status_lbl, "Product code not found.", ok=False)
        return None

    def _sync_product_from_name(*, show_error: bool = False) -> Optional[Dict[str, Any]]:
        name_text = _combo_text(product_name_combo)
        if not name_text:
            try:
                widgets["product_code"].clear()
            except Exception:
                pass
            return None
        result = _lookup_product_by_name(name_text)
        if result:
            try:
                widgets["product_code"].setText(str(result.get("code") or ""))
            except Exception:
                pass
            _set_product_name_text(str(result.get("name") or name_text))
            return result
        try:
            widgets["product_code"].clear()
        except Exception:
            pass
        if show_error:
            _set_status(status_lbl, "Product name not found.", ok=False)
        return None

    def _clear_product_name_when_code_edited(_text=None) -> None:
        try:
            _set_product_name_text("")
        except Exception:
            pass

    def _clear_product_code_when_name_edited(_text=None) -> None:
        try:
            widgets["product_code"].clear()
        except Exception:
            pass

    def _barcode_override(barcode: str) -> bool:
        code = str(barcode or "").strip()
        if not code:
            return True
        try:
            widgets["product_code"].setText(code)
        except Exception:
            pass
        _sync_product_from_code(show_error=True)
        try:
            widgets["search_btn"].setFocus(Qt.OtherFocusReason)
        except Exception:
            pass
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
        row = _selected_receipt(table)
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
            "product_name": _combo_text(product_name_combo),
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
            _render_preview(_selected_receipt(table))
        except Exception:
            _render_preview(None)

    def _renumber_rows() -> None:
        for row_idx in range(table.rowCount()):
            item = table.item(row_idx, 0)
            if item is None:
                continue
            serial = str(row_idx + 1)
            item.setText(serial)
            item.setToolTip(serial)
            item.setData(Qt.UserRole + 10, row_idx + 1)

    _sort_state = {"column": None, "order": Qt.AscendingOrder}

    def _sort_receipts_by_column(column: int) -> None:
        if column == 0:
            return
        try:
            selected = _selected_receipt(table)
            selected_no = str((selected or {}).get("receipt_no") or "")
        except Exception:
            selected_no = ""

        if _sort_state.get("column") == column:
            order = Qt.DescendingOrder if _sort_state.get("order") == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            order = Qt.AscendingOrder
        _sort_state["column"] = column
        _sort_state["order"] = order

        try:
            table.sortItems(column, order)
            table.horizontalHeader().setSortIndicator(column, order)
        except Exception:
            pass
        _renumber_rows()

        if selected_no:
            for row_idx in range(table.rowCount()):
                item = table.item(row_idx, 1)
                if item is not None and item.text() == selected_no:
                    table.selectRow(row_idx)
                    table.setCurrentItem(table.item(row_idx, 0) or item)
                    return
        _select_first_row()

    def _fill_table(rows: List[Dict[str, Any]]) -> None:
        try:
            table.setRowCount(0)
            for idx, row in enumerate(rows or [], start=1):
                visual_row = table.rowCount()
                table.insertRow(visual_row)
                values = (
                    str(idx),
                    str(row.get("receipt_no") or ""),
                    str(row.get("status") or ""),
                    _format_dt(row.get("created_at")),
                    _format_dt(row.get("paid_at")),
                    _format_dt(row.get("cancelled_at")),
                    _format_amount(row.get("amount")),
                )
                sort_keys = (
                    idx,
                    _sort_text(row.get("receipt_no")),
                    _sort_text(row.get("status")),
                    _sort_date(row.get("created_at")),
                    _sort_date(row.get("paid_at")),
                    _sort_date(row.get("cancelled_at")),
                    _sort_amount(row.get("amount")),
                )
                tooltips = (
                    str(idx),
                    str(row.get("receipt_no") or ""),
                    str(row.get("status") or ""),
                    _format_dt_full(row.get("created_at")),
                    _format_dt_full(row.get("paid_at")),
                    _format_dt_full(row.get("cancelled_at")),
                    _format_amount(row.get("amount")),
                )
                for col, text in enumerate(values):
                    item = ReceiptTableItem(text)
                    item.setData(Qt.UserRole, dict(row))
                    item.setData(Qt.UserRole + 10, sort_keys[col])
                    try:
                        item.setToolTip(tooltips[col])
                    except Exception:
                        pass
                    if col in (0, 2, 3, 4, 5, 6):
                        item.setTextAlignment(Qt.AlignCenter)
                    else:
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    table.setItem(visual_row, col, item)
        except Exception as exc:
            try:
                log_error_message(f"receipt_menu: fill table failed: {exc}")
            except Exception:
                pass
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
                _set_status(status_lbl, f"{len(rows)} receipt(s) found.", ok=True)
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

    def _reset_filters() -> None:
        today = QDate.currentDate()
        try:
            status_combo.setCurrentText("All")
            date_type_combo.setCurrentText("All")
            from_date.setDate(today)
            to_date.setDate(today)
            widgets["receipt_no"].clear()
            widgets["product_code"].clear()
            product_name_combo.setCurrentIndex(-1)
            product_name_combo.setEditText("")
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
        _render_preview(_selected_receipt(table))

    def _print_selected() -> None:
        row = _selected_receipt(table)
        if not row:
            _set_warning(status_lbl, "Select a receipt first.")
            return
        receipt_no = str(row.get("receipt_no") or "").strip()
        try:
            receipt_text = generate_receipt_text(receipt_no)
            if print_receipt(receipt_text):
                _set_status(status_lbl, f"Receipt {receipt_no} sent to printer.", ok=True)
                set_dialog_info(dlg, f"Receipt {receipt_no} printed.", duration=3500)
            else:
                _set_status(status_lbl, "Printer unavailable or receipt not sent.", ok=False)
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
        row = _selected_receipt(table)
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
        if void_radio.isChecked():
            _void_selected()
        else:
            _print_selected()

    def _cancel_close() -> None:
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
            if obj is table and event.type() == QEvent.KeyPress:
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    _render_preview(_selected_receipt(table))
                    return True
            if obj is note and event.type() == QEvent.KeyPress:
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    if void_radio.isChecked() and note.isEnabled():
                        _void_selected()
                        return True
            return False

    _event_filter = _ReceiptTableFilter(dlg)
    try:
        table.installEventFilter(_event_filter)
        note.installEventFilter(_event_filter)
        dlg._receipt_event_filter = _event_filter
    except Exception:
        pass

    _populate_combos()
    _populate_product_names()
    today = QDate.currentDate()
    try:
        from_date.setDate(today)
        to_date.setDate(today)
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
        widgets["search_btn"].clicked.connect(lambda: _refresh_receipts(show_count=True))
        widgets["reset_btn"].clicked.connect(_reset_filters)
        widgets["ok_btn"].clicked.connect(_on_ok)
        widgets["cancel_btn"].clicked.connect(_cancel_close)
        widgets["close_btn"].clicked.connect(_cancel_close)
        print_radio.toggled.connect(lambda _checked: _sync_action_state())
        void_radio.toggled.connect(lambda checked: (_sync_action_state(), checked and note.setFocus(Qt.OtherFocusReason)))
        widgets["receipt_no"].returnPressed.connect(lambda: _refresh_receipts(show_count=True))
        widgets["product_code"].textEdited.connect(_clear_product_name_when_code_edited)
        widgets["product_code"].editingFinished.connect(lambda: _sync_product_from_code(show_error=False))
        widgets["product_code"].returnPressed.connect(lambda: (_sync_product_from_code(show_error=True), _refresh_receipts(show_count=True)))
        product_name_combo.activated.connect(lambda _idx: _sync_product_from_name(show_error=False))
        if product_name_combo.lineEdit() is not None:
            product_name_combo.lineEdit().textEdited.connect(_clear_product_code_when_name_edited)
            product_name_combo.lineEdit().editingFinished.connect(lambda: _sync_product_from_name(show_error=False))
            product_name_combo.lineEdit().returnPressed.connect(lambda: (_sync_product_from_name(show_error=True), _refresh_receipts(show_count=True)))
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
