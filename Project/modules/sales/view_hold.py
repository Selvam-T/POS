import os
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QLineEdit,
    QPushButton,
    QLabel,
    QTableWidget,
    QRadioButton,
    QTableWidgetItem,
    QHeaderView,
)

from modules.db_operation import (
    list_unpaid_receipts,
    search_unpaid_receipts_by_customer,
    void_receipt,
    receipt_repo,
)
from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui,
    require_widgets,
    set_dialog_main_status_max,
    report_to_statusbar,
    log_exception_traceback_and_postclose_statusBar,
    log_error_message_and_postclose_statusBar,
)
from modules.ui_utils import ui_feedback, input_handler
from modules.ui_utils.focus_utils import FieldCoordinator, FocusGate
from modules.ui_utils.error_logger import log_error_message
from modules.date_time import format_date, format_time
from config import (
    MAIN_STATUS_DURATION_MS,
    MAIN_STATUS_ERROR_DURATION_MS,
    MAIN_STATUS_LONG_DURATION_MS,
    MAIN_STATUS_SHORT_DURATION_MS,
    STATUS_LABEL_DURATION_MS,
)
from modules.table_ui.table_widget_helpers import (
    apply_table_columns,
    configure_readonly_row_selection_table,
)
from config import QSS_DIR, UI_DIR

VIEW_HOLD_UI = os.path.join(UI_DIR, 'view_hold.ui')


class ViewHoldTableItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
            left = self.data(Qt.UserRole + 10)
            right = other.data(Qt.UserRole + 10)
            if left is not None and right is not None:
                return left < right
        except Exception:
            pass
        return super().__lt__(other)


def _configure_receipts_table(table: QTableWidget) -> None:
    """Configure the receipts table for explicit header-click sorting.

    Shared helpers handle the common list-table column setup, header
    tooltips, and read-only row-selection behavior. View Hold keeps its
    sort keys and header-click sorting local because the row shape and
    selection workflow are dialog-specific.
    """
    apply_table_columns(table, [
        {
            'label': 'Receipt No ↑↓',
            'mode': QHeaderView.Fixed,
            'width': 200,
            'align': Qt.AlignCenter,
            'tooltip': 'Receipt number',
        },
        {
            'label': 'Customer Name ↑↓',
            'mode': QHeaderView.Stretch,
            'align': Qt.AlignLeft | Qt.AlignVCenter,
            'tooltip': 'Customer name',
        },
        {
            'label': 'Grand Total ↑↓',
            'mode': QHeaderView.Fixed,
            'width': 150,
            'align': Qt.AlignLeft | Qt.AlignVCenter,
            'tooltip': 'Grand total',
        },
        {
            'label': 'Date ↑↓',
            'mode': QHeaderView.Fixed,
            'width': 150,
            'align': Qt.AlignCenter,
            'tooltip': 'Transaction date',
        },
        {
            'label': 'Time ↑↓',
            'mode': QHeaderView.Fixed,
            'width': 150,
            'align': Qt.AlignCenter,
            'tooltip': 'Transaction time',
        },
    ])
    header = table.horizontalHeader()
    try:
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.setSortIndicator(0, Qt.AscendingOrder)
    except Exception:
        pass
    configure_readonly_row_selection_table(table, sorting_enabled=False)


def _fill_receipts_table(table: QTableWidget, rows: list[dict]) -> None:
    """Populate `table` with `rows`.

    Sorting is temporarily disabled while rows are inserted to avoid
    re-ordering or visual jitter; user sorting preference is restored.
    Cell rendering stays local to this dialog; only header/selection setup
    is shared through `modules.table_ui.table_widget_helpers`.
    """
    was_sorting = False
    try:
        was_sorting = table.isSortingEnabled()
        table.setSortingEnabled(False)
    except Exception:
        was_sorting = False

    table.setRowCount(0)
    cell_align = {
        0: Qt.AlignCenter,
        1: Qt.AlignLeft | Qt.AlignVCenter,
        2: Qt.AlignLeft | Qt.AlignVCenter,
        3: Qt.AlignCenter,
        4: Qt.AlignCenter,
    }
    for r, row in enumerate(rows):
        table.insertRow(r)
        values = [
            str(row.get('receipt_no') or ''),
            str(row.get('customer_name') or ''),
            f"$ {float(row.get('grand_total') or 0.0):.2f}",
            format_date(row.get('created_at')),
            format_time(row.get('created_at')),
        ]
        sort_keys = [
            str(row.get('receipt_no') or '').strip().casefold(),
            str(row.get('customer_name') or '').strip().casefold(),
            float(row.get('grand_total') or 0.0),
            str(row.get('created_at') or '').strip(),
            str(row.get('created_at') or '').strip(),
        ]
        for c, text in enumerate(values):
            item = ViewHoldTableItem(text)
            item.setData(Qt.UserRole + 10, sort_keys[c])
            if c == 0:
                try:
                    item.setData(Qt.UserRole, row.get('receipt_id') or row.get('id'))
                    try:
                        item.setData(Qt.UserRole + 1, row.get('note') or '')
                    except Exception:
                        pass
                except Exception:
                    pass
            item.setTextAlignment(cell_align.get(c, Qt.AlignLeft | Qt.AlignVCenter))
            table.setItem(r, c, item)

    try:
        table.setSortingEnabled(bool(was_sorting))
    except Exception:
        pass


def launch_viewhold_dialog(parent=None):
    """Open the View Hold dialog and wire its behavior.

    The dialog lists UNPAID receipts and allows Load, Print or Void actions.
    """
    qss_path = os.path.join(QSS_DIR, 'dialog.qss')
    dlg = build_dialog_from_ui(
        VIEW_HOLD_UI,
        host_window=parent,
        dialog_name='View Hold',
        qss_path=qss_path,
        frameless=True,
        application_modal=True,
    )

    if not dlg:
        from modules.ui_utils.dialog_utils import build_error_fallback_dialog
        return build_error_fallback_dialog(parent, "View Hold", qss_path)

    # Resolve required widgets from the loaded UI
    widgets = require_widgets(dlg, {
        'search_in': (QLineEdit, 'viewHoldSearchLineEdit'),
        'table': (QTableWidget, 'viewHoldTable'),
        'note_in': (QLineEdit, 'viewHoldNoteLineEdit'),
        'status_lbl': (QLabel, 'viewHoldStatusLabel'),
        'ok_btn': (QPushButton, 'btnViewHoldOk'),
        'cancel_btn': (QPushButton, 'btnViewHoldCancel'),
        'load1_radio': (QRadioButton, 'viewHoldLoad1RadioBtn'),
        'load2_radio': (QRadioButton, 'viewHoldLoad2RadioBtn'),
        'print_radio': (QRadioButton, 'viewHoldPrintRadioBtn'),
        'void_radio': (QRadioButton, 'viewHoldVoidRadioBtn'),
    })
    close_btn = dlg.findChild(QPushButton, 'customCloseBtn')

    search_in = widgets['search_in']
    table = widgets['table']
    note_in = widgets['note_in']
    status_lbl = widgets['status_lbl']
    ok_btn = widgets['ok_btn']
    cancel_btn = widgets['cancel_btn']
    load1_radio = widgets['load1_radio']
    load2_radio = widgets['load2_radio']
    print_radio = widgets['print_radio']
    void_radio = widgets['void_radio']

    _configure_receipts_table(table)
    try:
        table.setFocusPolicy(Qt.StrongFocus)
    except Exception:
        pass

    # Keyboard/focus coordinator for live search and note input
    coord = FieldCoordinator(dlg)
    dlg._coord = coord  # prevent GC

    # Gate note input for VOID-only editing; placeholder shown only when unlocked
    # Ensure note is editable so unlock restores a white background via QSS
    try:
        note_in.setReadOnly(False)
    except Exception:
        pass
    note_gate = FocusGate([note_in], lock_enabled=True)
    try:
        note_gate.remember_placeholders([note_in])
        note_gate.hide_placeholders([note_in])
    except Exception:
        pass
    # Label that corresponds to the note input (for greying when gated)
    note_lbl = dlg.findChild(QLabel, 'viewHoldNoteFieldLbl')

    def _set_field_locked(lbl: QLabel, locked: bool) -> None:
        if lbl is None:
            return
        try:
            lbl.setProperty('locked', bool(locked))
            try:
                lbl.style().unpolish(lbl)
                lbl.style().polish(lbl)
            except Exception:
                pass
            try:
                lbl.update()
            except Exception:
                pass
        except Exception:
            pass

    note_gate.set_locked(True)
    _set_field_locked(note_lbl, True)

    # Enable or disable main input widgets when no receipts are available
    def _set_widgets_enabled(enabled: bool) -> None:
        search_in.setEnabled(enabled)
        table.setEnabled(enabled)
        load1_radio.setEnabled(enabled)
        load2_radio.setEnabled(enabled)
        print_radio.setEnabled(enabled)
        void_radio.setEnabled(enabled)
        ok_btn.setEnabled(enabled)
        if not enabled:
            note_in.setEnabled(False)

    # Return the stored note (UserRole+1) for the currently selected row
    def _selected_note_text() -> str:
        try:
            r = table.currentRow()
        except Exception:
            r = -1
        if r < 0:
            return ""
        # Prefer the stored note in UserRole+1 on the receipt_no cell (col 0).
        try:
            item0 = table.item(r, 0)
            if item0 is not None:
                note_data = item0.data(Qt.UserRole + 1)
                if note_data is not None:
                    return str(note_data or '')
        except Exception:
            pass
        # No visible note column any more; if not found return empty.
        return ""

    # Return (receipt_id, receipt_no) for the current selection
    def _selected_receipt_identifiers() -> tuple[int | None, str]:
        try:
            r = table.currentRow()
        except Exception:
            r = -1
        if r < 0:
            return None, ""

        receipt_no = ""
        receipt_id = None

        item0 = table.item(r, 0)
        if item0 is not None:
            try:
                receipt_no = str(item0.text() or "")
            except Exception:
                receipt_no = ""
            try:
                rid = item0.data(Qt.UserRole)
                receipt_id = int(rid) if rid is not None else None
            except Exception:
                receipt_id = None

        return receipt_id, receipt_no

    def _selected_customer_name() -> str:
        try:
            row = table.currentRow()
            item = table.item(row, 1) if row >= 0 else None
            return str(item.text() or "").strip() if item is not None else ""
        except Exception:
            return ""

    _search_skip_sync = {'active': False}

    # Clear search text without triggering a live-sync refresh
    def _clear_search_text() -> None:
        _search_skip_sync['active'] = True
        try:
            search_in.blockSignals(True)
        except Exception:
            pass
        try:
            search_in.clear()
        except Exception:
            pass
        try:
            search_in.blockSignals(False)
        except Exception:
            pass
        QTimer.singleShot(0, lambda: _search_skip_sync.__setitem__('active', False))

    # Update status label with a short message for the selected receipt
    def _show_selected_receipt_message() -> None:
        try:
            if table.currentRow() < 0:
                return
        except Exception:
            return

        _rid, receipt_no = _selected_receipt_identifiers()
        if not receipt_no:
            return

        customer_name = ""
        try:
            item = table.item(table.currentRow(), 1)
            customer_name = str(item.text() if item is not None else "").strip()
        except Exception:
            customer_name = ""

        if not customer_name:
            customer_name = "Unknown Customer"

        ui_feedback.set_status_label(
            status_lbl,
            f"{customer_name} receipt is selected.",
            ok=True,
            duration=STATUS_LABEL_DURATION_MS,
        )

    # Update status label to reflect the currently selected action
    def _show_selected_action_message() -> None:
        if load1_radio.isChecked():
            msg = "Load to continue selected."
        elif load2_radio.isChecked():
            msg = "Load to pay selected."
        elif print_radio.isChecked():
            msg = "Print selected."
        elif void_radio.isChecked():
            msg = "Void selected."
        else:
            return
        ui_feedback.set_status_label(status_lbl, msg, ok=True, duration=STATUS_LABEL_DURATION_MS)

    # Enable/disable and populate the note input depending on VOID mode
    def _refresh_note_state(*_a) -> None:
        if not void_radio.isChecked():
            note_in.blockSignals(True)
            note_in.clear()
            note_in.blockSignals(False)
            try:
                note_gate.hide_placeholders([note_in])
            except Exception:
                pass
            note_gate.set_locked(True)
            try:
                _set_field_locked(note_lbl, True)
            except Exception:
                pass
            return

        try:
            has_selection = table.currentRow() >= 0
        except Exception:
            has_selection = False
        if not has_selection:
            note_in.blockSignals(True)
            note_in.clear()
            note_in.blockSignals(False)
            try:
                note_gate.hide_placeholders([note_in])
            except Exception:
                pass
            note_gate.set_locked(True)
            try:
                _set_field_locked(note_lbl, True)
            except Exception:
                pass
            return

        note_gate.set_locked(False)
        try:
            _set_field_locked(note_lbl, False)
        except Exception:
            pass
        try:
            note_gate.restore_placeholders([note_in])
        except Exception:
            pass
        note_in.blockSignals(True)
        note_in.setText(_selected_note_text())
        note_in.blockSignals(False)

    # Ensure the receipts table has keyboard focus and a selected row
    def _focus_table() -> None:
        try:
            table.setFocus(Qt.OtherFocusReason)
        except Exception:
            return
        try:
            if table.rowCount() > 0 and table.currentRow() < 0:
                table.selectRow(0)
        except Exception:
            pass

    # Move keyboard focus to the OK button
    def _focus_ok() -> None:
        try:
            ok_btn.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass

    # Move keyboard focus to the Cancel button
    def _focus_cancel() -> None:
        try:
            cancel_btn.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass

    # Focus note input and select text if VOID mode is active
    def _focus_note_if_ready() -> None:
        try:
            if void_radio.isChecked() and note_in.isEnabled():
                note_in.setFocus(Qt.OtherFocusReason)
                note_in.selectAll()
        except Exception:
            pass

    # Handle toggling between Load / Print / Void actions
    def _on_action_changed(*_a) -> None:
        _refresh_note_state()
        _show_selected_action_message()
        if void_radio.isChecked():
            _focus_cancel()
        else:
            _focus_ok()

    # Enable or disable OK based on whether a row is selected
    def _update_action_gate() -> None:
        try:
            has_selection = table.currentRow() >= 0
        except Exception:
            has_selection = False
        ok_btn.setEnabled(bool(has_selection))
        if not has_selection:
            note_in.setEnabled(False)

    # Fill the table with rows and manage empty-state UI feedback
    def _apply_rows(
        rows: list[dict],
        *,
        empty_message: str | None = "",
        select_first: bool = True,
        show_selected_message: bool = True,
        clear_status_on_rows: bool = True,
    ) -> None:
        _fill_receipts_table(table, rows)
        if not rows:
            if empty_message is not None:
                msg = empty_message or "No matching receipts."
                ui_feedback.set_status_label(status_lbl, msg, ok=False)
                set_dialog_main_status_max(dlg, msg, level='info', duration=MAIN_STATUS_SHORT_DURATION_MS)
            _update_action_gate()
            _refresh_note_state()
            return
        if clear_status_on_rows:
            ui_feedback.clear_status_label(status_lbl)
        if select_first:
            table.selectRow(0)
        _update_action_gate()
        _refresh_note_state()
        if select_first and show_selected_message:
            _show_selected_receipt_message()

    _sort_state = {'column': None, 'order': Qt.AscendingOrder}

    def _sort_receipts_by_column(column: int) -> None:
        try:
            selected_id, selected_no = _selected_receipt_identifiers()
        except Exception:
            selected_id, selected_no = None, ""

        if _sort_state.get('column') == column:
            order = Qt.DescendingOrder if _sort_state.get('order') == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            order = Qt.AscendingOrder
        _sort_state['column'] = column
        _sort_state['order'] = order

        try:
            table.sortItems(column, order)
            table.horizontalHeader().setSortIndicator(column, order)
        except Exception:
            pass

        for row_idx in range(table.rowCount()):
            item = table.item(row_idx, 0)
            if item is None:
                continue
            try:
                receipt_id = item.data(Qt.UserRole)
            except Exception:
                receipt_id = None
            receipt_no = str(item.text() or "")
            if (selected_id is not None and receipt_id == selected_id) or (
                selected_id is None and selected_no and receipt_no == selected_no
            ):
                table.selectRow(row_idx)
                table.setCurrentItem(item)
                return

        if table.rowCount() > 0:
            table.selectRow(0)

    # Load UNPAID receipts from the DB and apply them to the table
    def _load_unpaid_receipts() -> None:
        try:
            rows = list_unpaid_receipts()
        except Exception:
            rows = []

        if not rows:
            _set_widgets_enabled(False)
            ui_feedback.set_status_label(status_lbl, "No UNPAID receipts found.", ok=False)
            set_dialog_main_status_max(dlg, "No UNPAID receipts found.", level='info', duration=MAIN_STATUS_SHORT_DURATION_MS)
            try:
                # When no receipts are available, ensure the Cancel button receives focus
                _focus_cancel()
            except Exception:
                pass
            return

        _set_widgets_enabled(True)
        if not load1_radio.isChecked():
            load1_radio.setChecked(True)
        _apply_rows(rows)

    # Reload table using the current search text (preserve user context)
    def _reload_from_current_search() -> None:
        try:
            q = (search_in.text() or "").strip()
        except Exception:
            q = ""
        try:
            rows = list_unpaid_receipts() if not q else search_unpaid_receipts_by_customer(q)
        except Exception:
            rows = []
        msg = "No matching receipts." if q else "No UNPAID receipts found."
        _apply_rows(rows, empty_message=msg)

    # Lookup function used by FieldCoordinator for live search
    def _search_lookup(val: str) -> dict:
        q = (val or "").strip()
        try:
            if not q:
                rows = list_unpaid_receipts()
            else:
                rows = search_unpaid_receipts_by_customer(q)
        except Exception:
            rows = []
        return {'rows': rows, 'query': q}

    # Callback invoked when a live search returns results
    def _on_search_sync(result: dict | None) -> None:
        if _search_skip_sync.get('active'):
            _search_skip_sync['active'] = False
            return
        if result is None:
            try:
                rows = list_unpaid_receipts()
            except Exception:
                rows = []
            _apply_rows(
                rows,
                empty_message=None,
                select_first=True,
                show_selected_message=False,
                clear_status_on_rows=True,
            )
            return
        if not isinstance(result, dict):
            _apply_rows([], empty_message="Search failed.")
            return
        rows = result.get('rows') or []
        q = str(result.get('query') or "").strip()
        _apply_rows(
            rows,
            empty_message=None,
            select_first=True,
            show_selected_message=False,
            clear_status_on_rows=True,
        )

    # Validate Enter key behavior on the search field
    def _search_validate_on_enter() -> str:
        link = coord.links.get(search_in)
        if link is not None:
            link['lookup'] = None
            QTimer.singleShot(0, lambda: link.__setitem__('lookup', _search_lookup))
        try:
            row_count = table.rowCount()
        except Exception:
            row_count = 0

        if row_count <= 0:
            _clear_search_text()
            ui_feedback.set_status_label(status_lbl, "No match was found", ok=False)
            try:
                rows = list_unpaid_receipts()
            except Exception:
                rows = []
            _apply_rows(
                rows,
                empty_message=None,
                select_first=False,
                show_selected_message=False,
                clear_status_on_rows=False,
            )
            try:
                _focus_cancel()
            except Exception:
                pass
            return ""

        try:
            table.selectRow(0)
        except Exception:
            pass
        _update_action_gate()
        _refresh_note_state()
        _show_selected_receipt_message()
        _clear_search_text()
        _focus_ok()
        return str(search_in.text() or "")

    # Decide where focus should go after a search (table or action radio)
    def _next_from_search() -> None:
        return

    coord.add_link(
        source=search_in,
        lookup_fn=_search_lookup,
        target_map={},
        on_sync=_on_search_sync,
        next_focus=_next_from_search,
        status_label=None,
        validate_fn=_search_validate_on_enter,
        swallow_empty=False,
        live_lookup=True,
        live_min_chars=0,
        live_debounce_ms=180,
    )

    coord.add_link(
        source=note_in,
        next_focus=_focus_ok,
        status_label=status_lbl,
        validate_fn=lambda: note_in.setText(input_handler.handle_note_input(note_in)) or note_in.text(),
        swallow_empty=False,
    )

    # --- Action handlers: LOAD / PRINT / VOID / OK / CANCEL ---
    def _handle_load(*, load_as_active_sale: bool) -> None:
        receipt_id, receipt_no = _selected_receipt_identifiers()
        customer_name = _selected_customer_name()
        if not receipt_no:
            ui_feedback.set_status_label(status_lbl, "Select a receipt.", ok=False)
            return

        if receipt_id is None:
            try:
                header = receipt_repo.get_receipt_header_by_no(receipt_no)
                if header and header.get('receipt_id') is not None:
                    receipt_id = int(header.get('receipt_id'))
            except Exception:
                receipt_id = None

        if receipt_id is None:
            ui_feedback.set_status_label(status_lbl, "Unable to resolve receipt id.", ok=False)
            return

        try:
            items = receipt_repo.list_receipt_items_by_no(receipt_no, receipt_id=receipt_id)
        except Exception as exc:
            log_exception_traceback_and_postclose_statusBar(
                dlg,
                "View Hold load receipt items",
                exc,
                user_message="Error: Unable to load receipt",
                level="error",
                duration=MAIN_STATUS_ERROR_DURATION_MS,
            )
            ui_feedback.set_status_label(status_lbl, "Unable to load receipt items.", ok=False)
            return

        if not items:
            ui_feedback.set_status_label(status_lbl, "No items found for this receipt.", ok=False)
            return

        try:
            from modules.table_ui.table_operations import get_total, set_table_rows
            from modules.domain.unit_helpers import canonicalize_unit

            rows = []
            total = 0.0
            for it in items:
                qty = float(it.get('qty') or 0.0)
                name = str(it.get('product_name') or '')
                unit = canonicalize_unit(it.get('unit') or '')
                unit_price = it.get('unit_price')
                if unit_price is None:
                    unit_price = 0.0
                try:
                    unit_price = float(unit_price or 0.0)
                except Exception:
                    unit_price = 0.0

                if unit_price <= 0.0:
                    try:
                        lt = float(it.get('line_total') or 0.0)
                        unit_price = (lt / qty) if qty else 0.0
                    except Exception:
                        unit_price = 0.0

                line_total = qty * unit_price
                total += line_total

                rows.append({
                    'product_name': name,
                    'quantity': qty,
                    'unit_price': unit_price,
                    'unit': unit,
                    'editable': unit != 'Kg',
                })

            sales_table = getattr(parent, 'sales_table', None) if parent is not None else None
            if sales_table is None:
                ui_feedback.set_status_label(status_lbl, "Sales table not available.", ok=False)
                return

            try:
                set_table_rows(sales_table, rows, status_bar=getattr(parent, 'statusbar', None))
            except Exception as exc:
                marker = getattr(parent, '_mark_sales_table_unavailable', None)
                if callable(marker):
                    marker(exc, where="Populate sales table from View Hold")
                set_dialog_main_status_max(
                    dlg,
                    "Error: Sales table unavailable. Transaction was not loaded.",
                    level="error",
                    duration=MAIN_STATUS_LONG_DURATION_MS,
                )
                ui_feedback.set_status_label(
                    status_lbl,
                    "Sales table unavailable. Transaction was not loaded.",
                    ok=False,
                )
                return

            payable_total = get_total(sales_table)

            panel = getattr(parent, 'payment_panel_controller', None) if parent is not None else None
            if panel is not None:
                try:
                    panel.set_payment_default(float(payable_total))
                except Exception:
                    pass

            frame = getattr(parent, 'sales_frame_controller', None) if parent is not None else None
            if load_as_active_sale:
                ctx = getattr(parent, 'receipt_context', None) if parent is not None else None
                if isinstance(ctx, dict):
                    ctx['active_receipt_id'] = None
                    ctx['source'] = 'ACTIVE_SALE'
                    ctx['status'] = 'NONE'
                try:
                    parent._refresh_sales_label_from_context()
                except Exception:
                    pass
            else:
                if frame is not None and receipt_id is not None:
                    try:
                        frame.notify_hold_loaded(int(receipt_id), float(payable_total))
                    except Exception:
                        pass

            if load_as_active_sale:
                log_context = (
                    f"receipt_id={receipt_id}, receipt_no={receipt_no!r}, "
                    f"customer_name={customer_name!r}"
                )
                try:
                    ok = void_receipt(
                        receipt_id=receipt_id,
                        receipt_no=receipt_no or None,
                        note="System cancelled - ongoing shopping",
                    )
                except Exception as exc:
                    log_exception_traceback_and_postclose_statusBar(
                        dlg,
                        f"View Hold cancel held receipt ({log_context})",
                        exc,
                        user_message=(
                            f"Error: Receipt {receipt_no} could not be cancelled; "
                            "transaction continued."
                        ),
                        level="error",
                        duration=MAIN_STATUS_ERROR_DURATION_MS,
                    )
                    ui_feedback.set_status_label(
                        status_lbl,
                        "Unable to cancel held receipt; continuing transaction.",
                        ok=False,
                    )
                else:
                    if not ok:
                        log_error_message_and_postclose_statusBar(
                            dlg,
                            f"View Hold cancel held receipt ({log_context})",
                            "void_receipt returned False; transaction loading continued",
                            user_message=(
                                f"Error: Receipt {receipt_no} could not be cancelled; "
                                "transaction continued."
                            ),
                            level="error",
                            duration=MAIN_STATUS_ERROR_DURATION_MS,
                        )
                        ui_feedback.set_status_label(
                            status_lbl,
                            "Could not cancel held receipt; continuing transaction.",
                            ok=False,
                        )

                set_dialog_main_status_max(dlg, f"On Hold transaction loaded to continue shopping.", level='info', duration=MAIN_STATUS_DURATION_MS)
            else:
                set_dialog_main_status_max(dlg, f"Loaded receipt {receipt_no} to make Payment.", level='info', duration=MAIN_STATUS_DURATION_MS)
            dlg.accept()
        except Exception as exc:
            log_exception_traceback_and_postclose_statusBar(
                dlg,
                "View Hold apply loaded receipt",
                exc,
                user_message="Error: Unable to load receipt",
                level="error",
                duration=MAIN_STATUS_ERROR_DURATION_MS,
            )
            ui_feedback.set_status_label(status_lbl, "Error loading receipt.", ok=False)

    def _handle_print() -> None:
        _rid, receipt_no = _selected_receipt_identifiers()
        if not receipt_no:
            ui_feedback.set_status_label(status_lbl, "Select a receipt.", ok=False)
            return

        try:
            from modules.payment import receipt_generator
            from modules.devices import print_helper

            receipt_text = receipt_generator.generate_receipt_text(receipt_no)
            print_result = print_helper.print_receipt_with_fallback(
                receipt_text,
                blocking=True,
                context="View Hold",
            )
            
            if print_result.get("ok"):
                report_to_statusbar(parent, f"Printed receipt {receipt_no}", is_error=False, duration=MAIN_STATUS_DURATION_MS)
                try:
                    dlg.accept()
                except Exception:
                    pass
            else:
                log_error_message_and_postclose_statusBar(
                    dlg,
                    "View Hold print failed",
                    f"Printer send failed for receipt {receipt_no}: "
                    f"{print_result.get('error') or 'unknown'}",
                    user_message=f"Print failed for {receipt_no}",
                    level="error",
                    duration=MAIN_STATUS_ERROR_DURATION_MS,
                )
                ui_feedback.set_status_label(status_lbl, f"Print failed for {receipt_no}", ok=False)
        except Exception as exc:
            log_exception_traceback_and_postclose_statusBar(
                dlg,
                "View Hold print receipt",
                exc,
                user_message="Error: Unable to print receipt",
                level="error",
                duration=MAIN_STATUS_ERROR_DURATION_MS,
            )
            ui_feedback.set_status_label(status_lbl, "Print error.", ok=False)

    def _handle_void() -> None:
        receipt_id, receipt_no = _selected_receipt_identifiers()
        if not receipt_no and receipt_id is None:
            ui_feedback.set_status_label(status_lbl, "Select a receipt.", ok=False)
            return

        if receipt_id is None and receipt_no:
            try:
                header = receipt_repo.get_receipt_header_by_no(receipt_no)
                if header and header.get('receipt_id') is not None:
                    receipt_id = int(header.get('receipt_id'))
            except Exception:
                receipt_id = None

        note_text = ""
        try:
            note_text = input_handler.handle_note_input(note_in)
        except Exception:
            try:
                note_text = str(note_in.text() or "").strip()
            except Exception:
                note_text = ""
        note_arg = note_text if (note_text or '').strip() else None

        try:
            ok = void_receipt(receipt_id=receipt_id, receipt_no=receipt_no or None, note=note_arg)
        except Exception as exc:
            log_exception_traceback_and_postclose_statusBar(
                dlg,
                "View Hold void receipt",
                exc,
                user_message="Error: Unable to void receipt",
                level="error",
                duration=MAIN_STATUS_ERROR_DURATION_MS,
            )
            ui_feedback.set_status_label(status_lbl, "Void failed.", ok=False)
            return

        if not ok:
            ui_feedback.set_status_label(status_lbl, "Void failed.", ok=False)
            report_to_statusbar(parent, "Void failed.", is_error=True, duration=MAIN_STATUS_ERROR_DURATION_MS)
            return

        note_in.clear()
        _reload_from_current_search()
        gated_applied = False
        try:
            # If there are no receipts left after void, apply gating so only
            # the Cancel/Close buttons remain active and show a clear hint.
            if table.rowCount() == 0:
                _set_widgets_enabled(False)
                gated_applied = True
        except Exception:
            gated_applied = False

        if gated_applied:
            ui_feedback.set_status_label(
                status_lbl,
                f"Receipt {receipt_no} voided. No receipts remaining; cancel to close.",
                ok=True,
                duration=STATUS_LABEL_DURATION_MS,
            )
        else:
            ui_feedback.set_status_label(status_lbl, f"Receipt {receipt_no} voided.", ok=True, duration=STATUS_LABEL_DURATION_MS)

    def _handle_ok() -> None:
        ui_feedback.clear_status_label(status_lbl)
        if load1_radio.isChecked():
            _handle_load(load_as_active_sale=True)
            return
        if load2_radio.isChecked():
            _handle_load(load_as_active_sale=False)
            return
        if print_radio.isChecked():
            _handle_print()
            return
        if void_radio.isChecked():
            _handle_void()
            return
        # Defensive logging: record unexpected state and show a user-facing hint
        log_error_message("ViewHold: OK pressed but no action selected")
        ui_feedback.set_status_label(status_lbl, "Select an action.", ok=False)

    def _handle_cancel() -> None:
        set_dialog_main_status_max(dlg, "View Hold cancelled.", level='info', duration=MAIN_STATUS_DURATION_MS)
        dlg.reject()

    cancel_btn.clicked.connect(_handle_cancel)
    ok_btn.clicked.connect(_handle_ok)
    if close_btn is not None:
        close_btn.clicked.connect(_handle_cancel)

    # Clear dialog-local status when user edits search or note
    def _clear_status_on_edit(*_a) -> None:
        ui_feedback.clear_status_label(status_lbl)

    search_in.textEdited.connect(_clear_status_on_edit)
    note_in.textEdited.connect(_clear_status_on_edit)

    # Update UI when table selection changes
    def _on_selection_changed() -> None:
        _refresh_note_state()
        _update_action_gate()
        _show_selected_receipt_message()
        # Only move focus when the user explicitly interacts with the table
        # (mouse click gives the table focus; programmatic selections do not).
        try:
            if table.hasFocus() or table.viewport().hasFocus():
                _clear_search_text()
                _focus_ok()
        except Exception:
            pass

    table.itemSelectionChanged.connect(_on_selection_changed)
    table.horizontalHeader().sectionClicked.connect(_sort_receipts_by_column)
    void_radio.toggled.connect(_on_action_changed)
    load1_radio.toggled.connect(_on_action_changed)
    load2_radio.toggled.connect(_on_action_changed)
    print_radio.toggled.connect(_on_action_changed)

    note_in.clear()
    note_in.setEnabled(False)

    _load_unpaid_receipts()

    try:
        _focus_ok()
    except Exception:
        pass

    #set_dialog_main_status_max(dlg, "View Hold opened.", level='info', duration=MAIN_STATUS_SHORT_DURATION_MS)
    return dlg
