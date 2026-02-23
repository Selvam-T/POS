import os
import datetime
from PyQt5.QtCore import Qt
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
    report_exception,
)
from modules.ui_utils import ui_feedback, input_handler
from modules.ui_utils.focus_utils import FieldCoordinator
from modules.ui_utils.error_logger import log_error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(BASE_DIR, 'ui')
VIEW_HOLD_UI = os.path.join(UI_DIR, 'view_hold.ui')

def launch_viewhold_dialog(parent=None):
    qss_path = os.path.join(BASE_DIR, 'assets', 'dialog.qss')
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

    widgets = require_widgets(dlg, {
        'search_in': (QLineEdit, 'viewHoldSearchLineEdit'),
        'table': (QTableWidget, 'receiptsTable'),
        'note_in': (QLineEdit, 'viewHoldNoteLineEdit'),
        'status_lbl': (QLabel, 'viewHoldStatusLabel'),
        'ok_btn': (QPushButton, 'btnViewHoldOk'),
        'cancel_btn': (QPushButton, 'btnViewHoldCancel'),
        'load_radio': (QRadioButton, 'viewHoldLoadRadioBtn'),
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
    load_radio = widgets['load_radio']
    print_radio = widgets['print_radio']
    void_radio = widgets['void_radio']

    _configure_receipts_table(table)
    try:
        table.setFocusPolicy(Qt.StrongFocus)
    except Exception:
        pass

    coord = FieldCoordinator(dlg)
    dlg._coord = coord  # prevent GC

    def _set_widgets_enabled(enabled: bool) -> None:
        search_in.setEnabled(enabled)
        table.setEnabled(enabled)
        load_radio.setEnabled(enabled)
        print_radio.setEnabled(enabled)
        void_radio.setEnabled(enabled)
        ok_btn.setEnabled(enabled)
        if not enabled:
            note_in.setEnabled(False)

    def _selected_row_note() -> str:
        try:
            r = table.currentRow()
        except Exception:
            r = -1
        if r < 0:
            return ""
        item = table.item(r, 4)
        try:
            return str(item.text() if item is not None else "")
        except Exception:
            return ""

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

    def _selected_receipt_total() -> float:
        try:
            r = table.currentRow()
        except Exception:
            return 0.0
        if r < 0:
            return 0.0
        item = table.item(r, 2)
        if item is None:
            return 0.0
        try:
            return float(str(item.text() or "0").replace(',', ''))
        except Exception:
            return 0.0

    _search_no_match = {'active': False}

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
            f"{customer_name} : {receipt_no} selected.",
            ok=True,
            duration=2000,
        )

    def _refresh_note_state(*_a) -> None:
        if not void_radio.isChecked():
            note_in.blockSignals(True)
            note_in.clear()
            note_in.blockSignals(False)
            note_in.setEnabled(False)
            return

        try:
            has_selection = table.currentRow() >= 0
        except Exception:
            has_selection = False
        if not has_selection:
            note_in.blockSignals(True)
            note_in.clear()
            note_in.blockSignals(False)
            note_in.setEnabled(False)
            return

        note_in.setEnabled(True)
        note_in.blockSignals(True)
        note_in.setText(_selected_row_note())
        note_in.blockSignals(False)

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

    def _focus_ok() -> None:
        try:
            ok_btn.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass

    def _focus_note_if_ready() -> None:
        try:
            if void_radio.isChecked() and note_in.isEnabled():
                note_in.setFocus(Qt.OtherFocusReason)
                note_in.selectAll()
        except Exception:
            pass

    def _on_action_changed(*_a) -> None:
        _refresh_note_state()
        if void_radio.isChecked():
            _focus_note_if_ready()
        else:
            _focus_ok()

    def _update_action_gate() -> None:
        try:
            has_selection = table.currentRow() >= 0
        except Exception:
            has_selection = False
        ok_btn.setEnabled(bool(has_selection))
        if not has_selection:
            note_in.setEnabled(False)

    def _apply_rows(rows: list[dict], *, empty_message: str = "") -> None:
        _fill_receipts_table(table, rows)
        if not rows:
            ui_feedback.set_status_label(status_lbl, empty_message or "No matching receipts.", ok=False)
            set_dialog_main_status_max(dlg, empty_message or "No matching receipts.", level='info', duration=2000)
            _update_action_gate()
            _refresh_note_state()
            return
        ui_feedback.clear_status_label(status_lbl)
        table.selectRow(0)
        _update_action_gate()
        _refresh_note_state()
        _show_selected_receipt_message()

    def _load_unpaid_receipts() -> None:
        try:
            rows = list_unpaid_receipts()
        except Exception:
            rows = []

        if not rows:
            _set_widgets_enabled(False)
            ui_feedback.set_status_label(status_lbl, "No UNPAID receipts found.", ok=False)
            set_dialog_main_status_max(dlg, "No UNPAID receipts found.", level='info', duration=2000)
            try:
                # When no receipts are available, ensure the Cancel button receives focus
                cancel_btn.setFocus(Qt.OtherFocusReason)
            except Exception:
                try:
                    cancel_btn.setFocus()
                except Exception:
                    pass
            return

        _set_widgets_enabled(True)
        if not load_radio.isChecked():
            load_radio.setChecked(True)
        _apply_rows(rows)

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

    def _on_search_sync(result: dict | None) -> None:
        if not isinstance(result, dict):
            _apply_rows([], empty_message="Search failed.")
            return
        rows = result.get('rows') or []
        q = str(result.get('query') or "").strip()
        msg = "No matching receipts." if q else "No UNPAID receipts found."
        _search_no_match['active'] = bool(q and not rows)
        _apply_rows(rows, empty_message=msg)
        if _search_no_match['active']:
            try:
                search_in.setFocus(Qt.OtherFocusReason)
                search_in.selectAll()
            except Exception:
                pass

    def _search_validate_on_enter() -> str:
        if _search_no_match.get('active'):
            _search_no_match['active'] = False
            try:
                search_in.clear()
            except Exception:
                pass
            ui_feedback.clear_status_label(status_lbl)
        return str(search_in.text() or "")

    def _next_from_search() -> None:
        try:
            txt = (search_in.text() or '').strip()
        except Exception:
            txt = ''
        if not txt:
            try:
                load_radio.setFocus(Qt.OtherFocusReason)
            except Exception:
                pass
            return
        _focus_table()

    coord.add_link(
        source=search_in,
        lookup_fn=_search_lookup,
        target_map={},
        on_sync=_on_search_sync,
        next_focus=_next_from_search,
        status_label=status_lbl,
        validate_fn=_search_validate_on_enter,
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

    def _handle_load() -> None:
        receipt_id, receipt_no = _selected_receipt_identifiers()
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
            report_exception(parent, "Load held receipt", exc, user_message="Error: Unable to load receipt", duration=6000)
            ui_feedback.set_status_label(status_lbl, "Unable to load receipt items.", ok=False)
            return

        if not items:
            ui_feedback.set_status_label(status_lbl, "No items found for this receipt.", ok=False)
            return

        try:
            from modules.table.table_operations import set_table_rows
            from modules.table.unit_helpers import canonicalize_unit

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

            set_table_rows(sales_table, rows, status_bar=getattr(parent, 'statusbar', None))

            panel = getattr(parent, 'payment_panel_controller', None) if parent is not None else None
            if panel is not None:
                try:
                    panel.set_payment_default(float(total))
                except Exception:
                    pass

            frame = getattr(parent, 'sales_frame_controller', None) if parent is not None else None
            if frame is not None and receipt_id is not None:
                try:
                    frame.notify_hold_loaded(int(receipt_id), float(total))
                except Exception:
                    pass

            set_dialog_main_status_max(dlg, f"Loaded receipt {receipt_no}.", level='info', duration=4000)
            dlg.accept()
        except Exception as exc:
            report_exception(parent, "Load held receipt", exc, user_message="Error: Unable to load receipt", duration=6000)
            ui_feedback.set_status_label(status_lbl, "Error loading receipt.", ok=False)

    def _handle_print() -> None:
        _rid, receipt_no = _selected_receipt_identifiers()
        if not receipt_no:
            ui_feedback.set_status_label(status_lbl, "Select a receipt.", ok=False)
            return

        try:
            from modules.payment import receipt_generator
            from modules.devices import printer as device_printer

            receipt_text = receipt_generator.generate_receipt_text(receipt_no)
            printed_ok = device_printer.print_receipt(receipt_text, blocking=True)
            if printed_ok:
                report_to_statusbar(parent, f"Printed receipt {receipt_no}", is_error=False, duration=4000)
                ui_feedback.set_status_label(status_lbl, "Printed.", ok=True, duration=2000)
            else:
                log_error(f"View Hold print failed: printer send failed for receipt_no={receipt_no}")
                report_to_statusbar(parent, f"Print failed for {receipt_no}", is_error=True, duration=6000)
                ui_feedback.set_status_label(status_lbl, "Print failed.", ok=False)
        except Exception as exc:
            report_exception(parent, "Print receipt", exc, user_message="Error: Unable to print receipt", duration=6000)
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
            report_exception(parent, "Void receipt", exc, user_message="Error: Unable to void receipt", duration=6000)
            ui_feedback.set_status_label(status_lbl, "Void failed.", ok=False)
            return

        if not ok:
            ui_feedback.set_status_label(status_lbl, "Void failed.", ok=False)
            report_to_statusbar(parent, "Void failed.", is_error=True, duration=6000)
            return

        report_to_statusbar(parent, f"Receipt {receipt_no or ''} voided.", is_error=False, duration=4000)
        ui_feedback.set_status_label(status_lbl, "Voided.", ok=True, duration=2000)
        note_in.clear()
        _reload_from_current_search()

    def _handle_ok() -> None:
        ui_feedback.clear_status_label(status_lbl)
        if load_radio.isChecked():
            _handle_load()
            return
        if print_radio.isChecked():
            _handle_print()
            return
        if void_radio.isChecked():
            _handle_void()
            return
        ui_feedback.set_status_label(status_lbl, "Select an action.", ok=False)

    def _handle_cancel() -> None:
        set_dialog_main_status_max(dlg, "View Hold cancelled.", level='info', duration=2500)
        dlg.reject()

    cancel_btn.clicked.connect(_handle_cancel)
    ok_btn.clicked.connect(_handle_ok)
    if close_btn is not None:
        close_btn.clicked.connect(_handle_cancel)

    def _clear_status_on_edit(*_a) -> None:
        ui_feedback.clear_status_label(status_lbl)

    search_in.textEdited.connect(_clear_status_on_edit)
    note_in.textEdited.connect(_clear_status_on_edit)

    def _on_selection_changed() -> None:
        _refresh_note_state()
        _update_action_gate()
        _show_selected_receipt_message()

    table.itemSelectionChanged.connect(_on_selection_changed)
    void_radio.toggled.connect(_on_action_changed)
    load_radio.toggled.connect(_on_action_changed)
    print_radio.toggled.connect(_on_action_changed)

    note_in.clear()
    note_in.setEnabled(False)

    _load_unpaid_receipts()

    search_in.setFocus(Qt.OtherFocusReason)
    search_in.selectAll()

    #set_dialog_main_status_max(dlg, "View Hold opened.", level='info', duration=2000)
    return dlg


def _configure_receipts_table(table: QTableWidget) -> None:
    table.setColumnCount(5)
    table.setHorizontalHeaderLabels([
        'Receipt No', 'Customer Name', 'Grand Total', 'Date', 'Note'
    ])
    header = table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.Fixed)
    header.setSectionResizeMode(1, QHeaderView.Fixed)
    header.setSectionResizeMode(2, QHeaderView.Fixed)
    header.setSectionResizeMode(3, QHeaderView.Stretch)
    header.setSectionResizeMode(4, QHeaderView.Stretch)
    header.resizeSection(0, 200)
    header.resizeSection(1, 200)
    header.resizeSection(2, 150)

    header_align = {
        0: Qt.AlignCenter,
        1: Qt.AlignLeft | Qt.AlignVCenter,
        2: Qt.AlignRight | Qt.AlignVCenter,
        3: Qt.AlignCenter,
        4: Qt.AlignLeft | Qt.AlignVCenter,
    }
    for col, align in header_align.items():
        try:
            item = table.horizontalHeaderItem(col)
            if item is not None:
                item.setTextAlignment(align)
        except Exception:
            pass
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setSelectionMode(QTableWidget.SingleSelection)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setSortingEnabled(True)
    table.setAlternatingRowColors(True)
    try:
        table.verticalHeader().setVisible(False)
    except Exception:
        pass


def _fill_receipts_table(table: QTableWidget, rows: list[dict]) -> None:
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
        2: Qt.AlignRight | Qt.AlignVCenter,
        3: Qt.AlignCenter,
        4: Qt.AlignLeft | Qt.AlignVCenter,
    }
    for r, row in enumerate(rows):
        table.insertRow(r)
        values = [
            str(row.get('receipt_no') or ''),
            str(row.get('customer_name') or ''),
            f"{float(row.get('grand_total') or 0.0):.2f}",
            _format_created_at(row.get('created_at')),
            str(row.get('note') or ''),
        ]
        for c, text in enumerate(values):
            item = QTableWidgetItem(text)
            if c == 0:
                try:
                    item.setData(Qt.UserRole, row.get('receipt_id') or row.get('id'))
                except Exception:
                    pass
            item.setTextAlignment(cell_align.get(c, Qt.AlignLeft | Qt.AlignVCenter))
            table.setItem(r, c, item)

    try:
        table.setSortingEnabled(bool(was_sorting))
    except Exception:
        pass


def _format_created_at(val) -> str:
    """Format a created_at value into 'dd-MMM-YYYY HH:MM'.

    Accepts datetime objects, numeric timestamps, or common string formats.
    Falls back to the original string representation on parse failure.
    """
    if val is None or (isinstance(val, str) and not val.strip()):
        return ''

    dt = None
    try:
        if isinstance(val, datetime.datetime):
            dt = val
        elif isinstance(val, (int, float)):
            # assume POSIX timestamp
            try:
                dt = datetime.datetime.fromtimestamp(float(val))
            except Exception:
                dt = None
        elif isinstance(val, str):
            s = val.strip()
            # try ISO first
            try:
                dt = datetime.datetime.fromisoformat(s)
            except Exception:
                dt = None
            if dt is None:
                # try several common formats
                fmts = (
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d %H:%M",
                    "%d-%m-%Y %H:%M:%S",
                    "%d/%m/%Y %H:%M:%S",
                    "%d-%m-%Y %H:%M",
                    "%d/%m/%Y %H:%M",
                    "%Y-%m-%d",
                )
                for fmt in fmts:
                    try:
                        dt = datetime.datetime.strptime(s, fmt)
                        break
                    except Exception:
                        dt = None
            # as a last resort, if string contains a space-separated ISO-like prefix
        else:
            # unknown type — fallback to str()
            return str(val)
    except Exception:
        try:
            return str(val)
        except Exception:
            return ''

    if dt is None:
        try:
            return str(val)
        except Exception:
            return ''

    try:
        return dt.strftime("%d-%b-%Y %I:%M %p").replace("AM", "am").replace("PM", "pm")
    except Exception:
        try:
            return str(val)
        except Exception:
            return ''