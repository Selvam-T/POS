"""Receipt History table helpers.

Column definitions are declarative so header setup, row display, tooltips, and
sort keys stay in sync across the status-specific receipt table layouts.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from modules.date_time import format_date, format_datetime
from modules.table_ui.table_widget_helpers import (
    apply_table_columns,
    configure_readonly_row_selection_table,
)
from modules.ui_utils.error_logger import log_error_message


SORT_ROLE = Qt.UserRole + 10
ARROWS = " ↑↓"
EMPTY_DATE = "—"


class ReceiptTableItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
            left = self.data(SORT_ROLE)
            right = other.data(SORT_ROLE)
            if left is not None and right is not None:
                return left < right
        except Exception:
            pass
        return super().__lt__(other)


def _format_amount(value: Any) -> str:
    try:
        return f"$ {float(value or 0.0):.2f}"
    except Exception:
        return "$0.00"


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
        return EMPTY_DATE
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


def _note_text(row: Dict[str, Any]) -> str:
    return str(row.get("note") or "").strip()


def _column(
    key: str,
    label: str,
    *,
    mode: QHeaderView.ResizeMode,
    width: Optional[int] = None,
    header_align=Qt.AlignCenter,
    cell_align=Qt.AlignLeft | Qt.AlignVCenter,
    tooltip: str = "",
    value: Callable[[Dict[str, Any], int], Any],
    sort: Callable[[Dict[str, Any], int], Any],
    cell_tooltip: Callable[[Dict[str, Any], int], Any],
) -> Dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "mode": mode,
        "width": width,
        "header_align": header_align,
        "cell_align": cell_align,
        "tooltip": tooltip,
        "value": value,
        "sort": sort,
        "cell_tooltip": cell_tooltip,
    }


COLUMN_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "serial": _column(
        "serial",
        "No.",
        mode=QHeaderView.Fixed,
        width=50,
        cell_align=Qt.AlignCenter,
        tooltip="Serial number",
        value=lambda row, idx: str(idx),
        sort=lambda row, idx: idx,
        cell_tooltip=lambda row, idx: str(idx),
    ),
    "receipt_no": _column(
        "receipt_no",
        "Receipt" + ARROWS,
        mode=QHeaderView.Stretch,
        tooltip="Receipt number",
        value=lambda row, idx: str(row.get("receipt_no") or ""),
        sort=lambda row, idx: _sort_text(row.get("receipt_no")),
        cell_tooltip=lambda row, idx: str(row.get("receipt_no") or ""),
    ),
    "status": _column(
        "status",
        "Status" + ARROWS,
        mode=QHeaderView.Fixed,
        width=105,
        cell_align=Qt.AlignCenter,
        tooltip="Receipt status",
        value=lambda row, idx: str(row.get("status") or ""),
        sort=lambda row, idx: _sort_text(row.get("status")),
        cell_tooltip=lambda row, idx: str(row.get("status") or ""),
    ),
    "created_at": _column(
        "created_at",
        "Transact" + ARROWS,
        mode=QHeaderView.Fixed,
        width=150,
        cell_align=Qt.AlignCenter,
        tooltip="Transaction date and time",
        value=lambda row, idx: _format_dt(row.get("created_at")),
        sort=lambda row, idx: _sort_date(row.get("created_at")),
        cell_tooltip=lambda row, idx: _format_dt_full(row.get("created_at")),
    ),
    "paid_at": _column(
        "paid_at",
        "Paid" + ARROWS,
        mode=QHeaderView.Fixed,
        width=150,
        cell_align=Qt.AlignCenter,
        tooltip="Payment date and time",
        value=lambda row, idx: _format_dt(row.get("paid_at")),
        sort=lambda row, idx: _sort_date(row.get("paid_at")),
        cell_tooltip=lambda row, idx: _format_dt_full(row.get("paid_at")),
    ),
    "cancelled_at": _column(
        "cancelled_at",
        "Cancelled" + ARROWS,
        mode=QHeaderView.Fixed,
        width=150,
        cell_align=Qt.AlignCenter,
        tooltip="Cancellation date and time",
        value=lambda row, idx: _format_dt(row.get("cancelled_at")),
        sort=lambda row, idx: _sort_date(row.get("cancelled_at")),
        cell_tooltip=lambda row, idx: _format_dt_full(row.get("cancelled_at")),
    ),
    "amount": _column(
        "amount",
        "Amount" + ARROWS,
        mode=QHeaderView.Fixed,
        width=115,
        tooltip="Receipt amount",
        value=lambda row, idx: _format_amount(row.get("amount")),
        sort=lambda row, idx: _sort_amount(row.get("amount")),
        cell_tooltip=lambda row, idx: _format_amount(row.get("amount")),
    ),
    "note": _column(
        "note",
        "Note" + ARROWS,
        mode=QHeaderView.Stretch,
        width=300,
        tooltip="Receipt note",
        value=lambda row, idx: _note_text(row),
        sort=lambda row, idx: _sort_text(row.get("note")),
        cell_tooltip=lambda row, idx: _note_text(row),
    ),
}


STATUS_LAYOUTS: Dict[str, Sequence[Dict[str, Any]]] = {
    "ALL": (
        {},
        {},
        {},
        {},
        {},
        {},
        {},
    ),
    "PAID": (
        {},
        {},
        {"key": "status", "width": 150},
        {"key": "created_at", "width": 190},
        {"key": "paid_at", "width": 190},
        {"key": "amount", "width": 135},
    ),
    "UNPAID": (
        {},
        {},
        {"key": "status", "width": 190},
        {"key": "created_at", "width": 190},
        {"key": "amount", "width": 135},
    ),
    "CANCELLED": (
        {},
        {"key": "receipt_no", "mode": QHeaderView.Fixed, "width": 150},
        {},
        {"key": "created_at", "width": 145},
        {"key": "cancelled_at", "width": 145},
        {"key": "amount", "width": 115},
        {"key": "note"},
    ),
}


DEFAULT_LAYOUT_KEYS = (
    "serial",
    "receipt_no",
    "status",
    "created_at",
    "paid_at",
    "cancelled_at",
    "amount",
)


def _layout_status(status: str) -> str:
    normalized = str(status or "ALL").strip().upper()
    return normalized if normalized in STATUS_LAYOUTS else "ALL"


def _resolve_layout(status: str) -> List[Dict[str, Any]]:
    layout_status = _layout_status(status)
    if layout_status == "ALL":
        return [dict(COLUMN_DEFINITIONS[key]) for key in DEFAULT_LAYOUT_KEYS]

    resolved = []
    for idx, override in enumerate(STATUS_LAYOUTS[layout_status]):
        key = override.get("key") or DEFAULT_LAYOUT_KEYS[idx]
        col = dict(COLUMN_DEFINITIONS[key])
        col.update(override)
        resolved.append(col)
    return resolved


def _header_specs(status: str) -> List[Dict[str, Any]]:
    return [
        {
            "label": col["label"],
            "mode": col["mode"],
            "width": col.get("width"),
            "align": col.get("header_align", Qt.AlignCenter),
            "tooltip": col.get("tooltip"),
        }
        for col in _resolve_layout(status)
    ]


def configure_receipt_table(table: QTableWidget, *, status: str = "ALL") -> None:
    apply_table_columns(table, _header_specs(status))

    header = table.horizontalHeader()
    try:
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.setSortIndicator(1, Qt.AscendingOrder)
    except Exception:
        pass

    configure_readonly_row_selection_table(table, sorting_enabled=False)


def selected_receipt(table: QTableWidget) -> Optional[Dict[str, Any]]:
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


def renumber_rows(table: QTableWidget) -> None:
    for row_idx in range(table.rowCount()):
        item = table.item(row_idx, 0)
        if item is None:
            continue
        serial = str(row_idx + 1)
        item.setText(serial)
        item.setToolTip(serial)
        item.setData(SORT_ROLE, row_idx + 1)


def sort_receipts_by_column(
    table: QTableWidget,
    column: int,
    sort_state: Dict[str, Any],
    *,
    select_first_row: Callable[[], None],
    status: str = "ALL",
) -> None:
    if column == 0:
        return
    if column >= len(_resolve_layout(status)):
        return
    try:
        selected = selected_receipt(table)
        selected_no = str((selected or {}).get("receipt_no") or "")
    except Exception:
        selected_no = ""

    if sort_state.get("column") == column:
        order = Qt.DescendingOrder if sort_state.get("order") == Qt.AscendingOrder else Qt.AscendingOrder
    else:
        order = Qt.AscendingOrder
    sort_state["column"] = column
    sort_state["order"] = order

    try:
        table.sortItems(column, order)
        table.horizontalHeader().setSortIndicator(column, order)
    except Exception:
        pass
    renumber_rows(table)

    if selected_no:
        for row_idx in range(table.rowCount()):
            item = table.item(row_idx, 1)
            if item is not None and item.text() == selected_no:
                table.selectRow(row_idx)
                table.setCurrentItem(table.item(row_idx, 0) or item)
                return
    select_first_row()


def fill_receipt_table(table: QTableWidget, rows: List[Dict[str, Any]], *, status: str = "ALL") -> None:
    try:
        columns = _resolve_layout(status)
        table.setRowCount(0)
        for idx, row in enumerate(rows or [], start=1):
            visual_row = table.rowCount()
            table.insertRow(visual_row)
            for col_idx, col in enumerate(columns):
                text = str(col["value"](row, idx))
                item = ReceiptTableItem(text)
                item.setData(Qt.UserRole, dict(row))
                item.setData(SORT_ROLE, col["sort"](row, idx))
                try:
                    item.setToolTip(str(col["cell_tooltip"](row, idx)))
                except Exception:
                    pass
                item.setTextAlignment(col.get("cell_align", Qt.AlignLeft | Qt.AlignVCenter))
                table.setItem(visual_row, col_idx, item)
    except Exception as exc:
        try:
            log_error_message(f"receipt_menu: fill table failed: {exc}")
        except Exception:
            pass
