"""Small QTableWidget helpers shared by list-style tables."""

from typing import Any, Mapping, Sequence

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAbstractItemView, QTableWidget


def apply_table_columns(table: QTableWidget, columns: Sequence[Mapping[str, Any]]) -> None:
    """Apply labels, header sizing, alignment, and tooltips from column specs."""
    if table is None:
        return

    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels([str(col.get("label", "")) for col in columns])

    header = table.horizontalHeader()
    for index, column in enumerate(columns):
        mode = column.get("mode")
        if mode is not None:
            header.setSectionResizeMode(index, mode)

        width = column.get("width")
        if width is not None:
            header.resizeSection(index, int(width))

        item = table.horizontalHeaderItem(index)
        if item is None:
            continue

        item.setTextAlignment(column.get("align", Qt.AlignCenter))
        tooltip = column.get("tooltip")
        if tooltip:
            item.setToolTip(str(tooltip))


def configure_readonly_row_selection_table(table: QTableWidget, *, sorting_enabled: bool = False) -> None:
    """Apply common read-only, row-selecting behavior for list tables."""
    if table is None:
        return

    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSortingEnabled(bool(sorting_enabled))
    table.setAlternatingRowColors(True)
    try:
        table.verticalHeader().setVisible(False)
    except Exception:
        pass
