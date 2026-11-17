"""High-level barcode scanner routing and UI leak cleanup."""

import weakref

from PyQt5.QtCore import QObject, QTimer
from config import (
    BARCODE_SCANNER_HEALTH_INTERVAL_MS,
    BARCODE_SCANNER_SUMMARY_INTERVAL_MS,
    MAIN_STATUS_DURATION_MS,
    SCANNER_CANDIDATE_INACTIVITY_SECONDS,
    SCANNER_UI_SETTLE_MS,
    SCANNER_UI_SUPPRESS_SECONDS,
)
from modules.devices.scanner import BarcodeScanner
from modules.devices.scanner_trace_logger import trace_scanner_event
from modules.ui_utils import ui_feedback

PROTECTED_MANUAL_FIELD_NAMES = {
    'qtyInput',
    'tenderValLineEdit',
    'cashPayLineEdit',
    'netsPayLineEdit',
    'paynowPayLineEdit',
    'voucherPayLineEdit',
}


class BarcodeManager(QObject):
    """Manage scanner events, dialog overrides, modal blocking, and scan leaks."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scanner = BarcodeScanner()
        self._modalBlockScanner = False
        self._barcodeOverride = None
        self._scannerCandidateUntil = 0.0
        self._scannerBurstUntil = 0.0
        self._protectedManualText = weakref.WeakKeyDictionary()
        self._traceRouteCounts = {
            'barcodes_received': 0,
            'sales_added': 0,
            'sales_incremented': 0,
            'dialog_override_handled': 0,
            'routes_rejected_or_failed': 0,
        }
        self.scanner.barcode_scanned.connect(self.on_barcode_scanned)
        self.scanner.scanner_activity.connect(self._on_scanner_activity)
        self.scanner.candidate_completed.connect(self._on_scanner_candidate_completed)
        self.scanner.start()
        self._lastScannerHealth = None
        self._scannerHealthTimer = QTimer(self)
        self._scannerHealthTimer.setInterval(BARCODE_SCANNER_HEALTH_INTERVAL_MS)
        self._scannerHealthTimer.timeout.connect(self._trace_scanner_health)
        self._scannerHealthTimer.start()
        self._trace_scanner_health(force=True)
        self._scannerSummaryTimer = QTimer(self)
        self._scannerSummaryTimer.setInterval(BARCODE_SCANNER_SUMMARY_INTERVAL_MS)
        self._scannerSummaryTimer.timeout.connect(self._trace_scanner_summary)
        self._scannerSummaryTimer.start()


    def on_barcode_scanned(self, barcode: str):
        """Route a completed barcode scan to the active context."""
        parent = self.parent()
        barcode = (barcode or '').strip()
        self._trace_route('route_received', barcode=barcode)

        # Dialog overrides may accept scans that start in a product-code field.
        try:
            from PyQt5.QtWidgets import QApplication, QLabel
            override = getattr(self, '_barcodeOverride', None)
            fw = QApplication.instance().focusWidget() if QApplication.instance() else None
            obj_name = fw.objectName() if fw and hasattr(fw, 'objectName') else ''
            scan_start_name = getattr(self, '_scanStartObjName', '') or ''
            scan_started_in_code = self._is_barcode_allowed_name(scan_start_name)
            focus_in_code = self._is_barcode_allowed_name(obj_name)
            if callable(override):
                if focus_in_code or scan_started_in_code:
                    handled = False
                    try:
                        handled = override(barcode)
                    except Exception:
                        handled = False
                    if handled:
                        self._trace_route('route_finished', barcode=barcode, outcome='dialog-override-handled')
                        self._defer_barcode_field_value(fw, barcode)
                        return
                else:
                    self._restore_confirmed_scan_text(barcode)
                    dlg = QApplication.activeModalWidget() or QApplication.activeWindow()
                    try:
                        if dlg is not None and bool(dlg.property('suppressBarcodeWarning')):
                            self._trace_route('route_finished', barcode=barcode, outcome='dialog-warning-suppressed')
                            return
                    except Exception:
                        pass
                    if dlg is not None:
                        # Try to find a status label with a common naming pattern
                        status_lbl = None
                        for lbl_name in ['addStatusLabel', 'removeStatusLabel', 'updateStatusLabel', 'manualStatusLabel', 'refundStatusLabel', 'receiptStatusLabel']:
                            status_lbl = dlg.findChild(QLabel, lbl_name)
                            if status_lbl is not None:
                                break
                        if status_lbl is not None:
                            ui_feedback.set_warning_status_label(status_lbl, ui_feedback.BARCODE_WARNING_TEXT)
                    self._trace_route('route_finished', barcode=barcode, outcome='dialog-override-focus-rejected')
                    return
        except Exception as exc:
            self._trace_route('route_stage_exception', barcode=barcode, stage='override', exception=repr(exc))

        # Restore tentative input only after a scan is confirmed.
        self._restore_confirmed_scan_text(barcode)

        # If a held receipt is loaded into the cart, do not permit scanner-driven
        # routing into the main sales/payment flow. Keep dialog overrides working
        # (override logic above) so ProductCode dialogs can still accept scans.
        try:
            ctx = getattr(parent, 'receipt_context', {}) or {}
            if ctx.get('source') == 'HOLD_LOADED':
                self._trace_route('route_finished', barcode=barcode, outcome='hold-loaded')
                return
        except Exception:
            pass

        status_bar = getattr(parent, 'statusbar', None)

        # Generic scanner-blocked modals do not own scans.
        try:
            if getattr(self, '_modalBlockScanner', False):
                self._trace_route('route_finished', barcode=barcode, outcome='modal-block-open')
                return
        except Exception:
            pass

        # Manual-entry fields in the main window must not own or route scans.
        try:
            from PyQt5.QtWidgets import QApplication
            fw = QApplication.instance().focusWidget() if QApplication.instance() else None
            start_w = getattr(self, '_scanStartWidget', None)
            if self._is_protected_manual_field(fw) or self._is_protected_manual_field(start_w):
                self._trace_route('route_finished', barcode=barcode, outcome='protected-manual-field')
                return
        except Exception:
            pass

        readiness_gate = getattr(parent, '_require_sales_table_ready', None)
        if callable(readiness_gate) and not readiness_gate():
            self._trace_route('route_finished', barcode=barcode, outcome='sales-table-unavailable')
            return

        try:
            from modules.table_ui import handle_barcode_scanned
            try:
                from modules.table_ui.table_operations import get_product_info
                found, _, _, _ = get_product_info(barcode)
            except Exception:
                found = True
            if not found:
                self._trace_route('route_finished', barcode=barcode, outcome='product-not-found')
                if status_bar and hasattr(status_bar, 'showMessage'):
                    status_bar.showMessage(f"Product '{barcode}' not found - Opening Product Management (ADD)", MAIN_STATUS_DURATION_MS)
                if hasattr(parent, 'open_product_menu_dialog'):
                    parent.open_product_menu_dialog(
                        initial_mode='add',
                        initial_code=barcode,
                        opened_from_missing_scan=True,
                    )
                return
            if hasattr(parent, 'sales_table') and parent.sales_table is not None:
                try:
                    rows_before = self._sales_table_row_count()
                    outcome = handle_barcode_scanned(parent.sales_table, barcode, status_bar)
                    if outcome in {'added', 'incremented'}:
                        self._focus_sales_table()
                    self._trace_route(
                        'route_finished',
                        barcode=barcode,
                        outcome=outcome or 'no-outcome',
                        rows_before=rows_before,
                        rows_after=self._sales_table_row_count(),
                    )
                except Exception as exc:
                    self._trace_route('route_exception', barcode=barcode, exception=repr(exc))
                    marker = getattr(parent, '_mark_sales_table_unavailable', None)
                    if callable(marker):
                        marker(exc, where="Populate sales table from barcode scan")
                    return
            else:
                readiness_gate = getattr(parent, '_require_sales_table_ready', None)
                if callable(readiness_gate):
                    readiness_gate()
                elif status_bar and hasattr(status_bar, 'showMessage'):
                    status_bar.showMessage(f"Scanned: {barcode}", MAIN_STATUS_DURATION_MS)
        except Exception as exc:
            self._trace_route('route_exception', barcode=barcode, exception=repr(exc))

    def _on_scanner_activity(self, _when_ts: float, is_fast: bool = False):
        """Track burst timing and snapshot focused text before scanner characters land."""
        import time
        now = time.time()
        
        if now > getattr(self, '_scannerCandidateUntil', 0.0):
            try:
                from PyQt5.QtWidgets import QApplication
                app = QApplication.instance()
                fw = app.focusWidget() if app else None
                self._snapshot_scan_start(fw, now)
            except Exception:
                self._preScanText = None
        if is_fast:
            # Covers typical 12-14 digit scans plus Enter suffix.
            self._scannerCandidateUntil = max(
                getattr(self, '_scannerCandidateUntil', 0.0),
                now + SCANNER_UI_SUPPRESS_SECONDS,
            )
            self._scannerBurstUntil = max(
                getattr(self, '_scannerBurstUntil', 0.0),
                now + SCANNER_UI_SUPPRESS_SECONDS,
            )
            self._suppressEnterUntil = max(
                getattr(self, '_suppressEnterUntil', 0.0),
                now + SCANNER_UI_SUPPRESS_SECONDS,
            )
        else:
            # Keep one focus snapshot for the full candidate.
            self._scannerCandidateUntil = max(
                getattr(self, '_scannerCandidateUntil', 0.0),
                now + SCANNER_CANDIDATE_INACTIVITY_SECONDS,
            )

    def _snapshot_scan_start(self, widget, timestamp: float) -> None:
        """Capture editable text before the first candidate key lands."""
        from PyQt5.QtWidgets import QDateEdit, QLineEdit, QTextEdit, QPlainTextEdit
        self._scanStartWidget = widget
        self._scanStartObjName = self._object_name(widget)
        self._preScanText = None
        if isinstance(widget, QDateEdit):
            line = widget.lineEdit()
            self._preScanText = line.text() if line is not None else widget.text()
        elif isinstance(widget, QLineEdit):
            self._preScanText = widget.text()
        elif isinstance(widget, (QTextEdit, QPlainTextEdit)):
            self._preScanText = widget.toPlainText()

    def _on_scanner_candidate_completed(self, _accepted: bool) -> None:
        """Close the focus snapshot while leaving trailing-Enter protection active."""
        self._scannerCandidateUntil = 0.0
        self._scanStartWidget = None
        self._scanStartObjName = ''
        self._preScanText = None

    def _restore_pre_scan_text(self, fw):
        """Restore focused editable text captured at scan-burst start."""
        try:
            from PyQt5.QtWidgets import QDateEdit, QLineEdit, QTextEdit, QPlainTextEdit
            saved = getattr(self, '_preScanText', None)
            
            if fw is not None and saved is not None:
                if isinstance(fw, QDateEdit):
                    line = fw.lineEdit()
                    if line is not None:
                        line.setText(saved)
                    return True
                elif isinstance(fw, QLineEdit):
                    fw.setText(saved)
                    return True
                elif isinstance(fw, (QTextEdit, QPlainTextEdit)):
                    if isinstance(fw, QTextEdit):
                        fw.setHtml(saved) if '<' in saved else fw.setPlainText(saved)
                    else:
                        fw.setPlainText(saved)
                    return True
        except Exception:
            pass
        return False

    @staticmethod
    def _object_name(widget) -> str:
        try:
            if widget is None or not hasattr(widget, 'objectName'):
                return ''
            return str(widget.objectName() or '')
        except Exception:
            return ''

    @staticmethod
    def _is_barcode_allowed_name(name: str) -> bool:
        name = str(name or '')
        return name == 'productCodeLineEdit' or name.endswith('ProductCodeLineEdit')

    def _is_barcode_allowed_field(self, widget) -> bool:
        return self._is_barcode_allowed_name(self._object_name(widget))

    def _is_protected_manual_field(self, widget) -> bool:
        return self._object_name(widget) in PROTECTED_MANUAL_FIELD_NAMES

    def _remember_protected_manual_text(self, widget) -> None:
        if not self._is_protected_manual_field(widget):
            return
        try:
            from PyQt5.QtWidgets import QLineEdit
            if isinstance(widget, QLineEdit):
                self._protectedManualText[widget] = widget.text()
        except Exception:
            pass

    def _restore_confirmed_scan_text(self, barcode: str) -> None:
        """Restore editable text after pending scanner key events."""
        try:
            from PyQt5.QtCore import QTimer
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            fw = app.focusWidget() if app else None
            start_w = getattr(self, '_scanStartWidget', None)
            visited = set()
            for widget in (start_w, fw):
                if (
                    widget is None
                    or id(widget) in visited
                    or self._is_barcode_allowed_field(widget)
                ):
                    continue
                visited.add(id(widget))
                saved = self._saved_scan_text(widget, widget is start_w)
                if saved is not None:
                    QTimer.singleShot(
                        SCANNER_UI_SETTLE_MS,
                        lambda w=widget, value=saved: self._set_editable_text(w, value),
                    )
                else:
                    QTimer.singleShot(
                        SCANNER_UI_SETTLE_MS,
                        lambda w=widget: self._cleanup_scanner_leak(w, barcode),
                    )
        except Exception:
            pass

    def _defer_barcode_field_value(self, widget, barcode: str) -> None:
        """Keep a handled product-code field authoritative."""
        try:
            from PyQt5.QtCore import QTimer
            start_w = getattr(self, '_scanStartWidget', None)
            target = widget if self._is_barcode_allowed_field(widget) else start_w
            if self._is_barcode_allowed_field(target):
                QTimer.singleShot(
                    SCANNER_UI_SETTLE_MS,
                    lambda w=target, value=barcode: self._set_editable_text(w, value),
                )
        except Exception:
            pass

    def _saved_scan_text(self, widget, is_start_widget: bool):
        try:
            if self._is_protected_manual_field(widget):
                return self._protectedManualText.get(widget)
            if is_start_widget:
                return getattr(self, '_preScanText', None)
        except Exception:
            pass
        return None

    @staticmethod
    def _set_editable_text(widget, value) -> None:
        try:
            from PyQt5.QtWidgets import QDateEdit, QLineEdit, QTextEdit, QPlainTextEdit
            if isinstance(widget, QDateEdit):
                line = widget.lineEdit()
                if line is not None:
                    line.setText(value)
            elif isinstance(widget, QLineEdit):
                widget.setText(value)
            elif isinstance(widget, (QTextEdit, QPlainTextEdit)):
                widget.setPlainText(value)
        except (RuntimeError, TypeError):
            pass

    def eventFilter(self, obj, event):
        import time
        from PyQt5.QtCore import QEvent, Qt
        from PyQt5.QtWidgets import QApplication
        if event.type() == QEvent.FocusIn:
            self._remember_protected_manual_text(obj)
        elif event.type() == QEvent.KeyRelease:
            now = time.time()
            if (
                now > getattr(self, '_scannerCandidateUntil', 0.0)
                and now > getattr(self, '_scannerBurstUntil', 0.0)
            ):
                self._remember_protected_manual_text(obj)

        if event.type() == QEvent.KeyPress:
            k = event.key()
            now = time.time()
            text = event.text() or ''
            is_printable = len(text) == 1 and (31 < ord(text) < 127)
            if is_printable and now > getattr(self, '_scannerCandidateUntil', 0.0):
                try:
                    self._snapshot_scan_start(obj, now)
                    self._scannerCandidateUntil = now + SCANNER_CANDIDATE_INACTIVITY_SECONDS
                except Exception:
                    pass
            if is_printable and now > getattr(self, '_scannerBurstUntil', 0.0):
                self._remember_protected_manual_text(obj)

            try:
                if getattr(self, '_modalBlockScanner', False):
                    app = QApplication.instance()
                    fw = app.focusWidget() if app else None
                    modal = app.activeModalWidget() if app else None

                    try:
                        if modal is not None and fw is not None and fw.window() is modal:
                            pass
                        else:
                            if is_printable or k in (Qt.Key_Return, Qt.Key_Enter):
                                self._restore_pre_scan_text(fw)
                                return True
                    except Exception:
                        if is_printable or k in (Qt.Key_Return, Qt.Key_Enter):
                            self._restore_pre_scan_text(fw)
                            return True
            except Exception:
                pass

            if k in (Qt.Key_Return, Qt.Key_Enter) and now <= getattr(self, '_suppressEnterUntil', 0.0):
                return True

        return super().eventFilter(obj, event)
    
    def _cleanup_scanner_leak(self, fw, barcode):
        try:
            if fw is None or not barcode:
                return
            
            ch = barcode[0]
            
            from PyQt5.QtWidgets import QDateEdit, QLineEdit, QTextEdit, QPlainTextEdit

            if isinstance(fw, QDateEdit):
                line = fw.lineEdit()
                txt = line.text() if line is not None else ''
                if txt.endswith(ch) and line is not None:
                    line.setText(txt[:-1])
                    return

            if isinstance(fw, QLineEdit):
                txt = fw.text() or ''
                if txt.endswith(ch):
                    fw.setText(txt[:-1])
                    return

            elif isinstance(fw, (QTextEdit, QPlainTextEdit)):
                t = fw.toPlainText() or ''
                if t.endswith(ch):
                    if isinstance(fw, QTextEdit):
                        from PyQt5.QtGui import QTextCursor
                        cur = fw.textCursor()
                        cur.movePosition(QTextCursor.End)
                        cur.deletePreviousChar()
                        fw.setTextCursor(cur)
                    else:
                        fw.setPlainText(t[:-1])
                        fw.moveCursor(QTextCursor.End)
                    return
        except Exception:
            pass

    def _focus_sales_table(self) -> None:
        """Give successful main-window scans a deterministic safe focus target."""
        try:
            from PyQt5.QtCore import Qt
            parent = self.parent()
            table = getattr(parent, 'sales_table', None)
            if table is not None:
                table.setFocusPolicy(Qt.StrongFocus)
                table.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass

    def _sales_table_row_count(self):
        try:
            table = getattr(self.parent(), 'sales_table', None)
            return table.rowCount() if table is not None else None
        except Exception:
            return None

    def _trace_route(self, event: str, **fields) -> None:
        """Record scanner routing state without changing any routing decision."""
        try:
            outcome = fields.get('outcome')
            if event == 'route_received':
                self._traceRouteCounts['barcodes_received'] += 1
                return
            if event == 'route_finished' and outcome in {
                'added', 'incremented', 'dialog-override-handled'
            }:
                counter = {
                    'added': 'sales_added',
                    'incremented': 'sales_incremented',
                    'dialog-override-handled': 'dialog_override_handled',
                }[outcome]
                self._traceRouteCounts[counter] += 1
                rows_before = fields.get('rows_before')
                rows_after = fields.get('rows_after')
                expected_rows = (
                    rows_before + 1 if outcome == 'added' and isinstance(rows_before, int)
                    else rows_before if outcome == 'incremented' and isinstance(rows_before, int)
                    else None
                )
                if expected_rows is None or rows_after == expected_rows:
                    return
                event = 'suspicious_table_result'
            else:
                self._traceRouteCounts['routes_rejected_or_failed'] += 1

            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            focus = app.focusWidget() if app else None
            active = app.activeWindow() if app else None
            modal = app.activeModalWidget() if app else None
            parent = self.parent()
            context = getattr(parent, 'receipt_context', {}) or {}
            trace_scanner_event(
                event,
                focus_widget=self._object_name(focus),
                scan_start_widget=getattr(self, '_scanStartObjName', '') or '',
                active_window=self._object_name(active),
                active_modal=self._object_name(modal),
                modal_block=bool(getattr(self, '_modalBlockScanner', False)),
                override_installed=callable(getattr(self, '_barcodeOverride', None)),
                receipt_source=context.get('source'),
                sales_table_ready=getattr(parent, '_sales_table_ready', None),
                listener_alive=self.scanner.listener_is_alive(),
                scanner_enabled=getattr(self.scanner, '_enabled', None),
                **fields,
            )
        except Exception:
            pass

    def _trace_scanner_summary(self) -> None:
        """Write one compact five-minute summary instead of each normal scan."""
        try:
            input_counts = self.scanner.take_trace_summary()
            route_counts = dict(self._traceRouteCounts)
            if not any(input_counts.values()) and not any(route_counts.values()):
                return
            trace_scanner_event(
                'scanner_summary',
                listener_alive=self.scanner.listener_is_alive(),
                **input_counts,
                **route_counts,
            )
            for key in self._traceRouteCounts:
                self._traceRouteCounts[key] = 0
        except Exception:
            pass

    def _trace_scanner_health(self, force: bool = False) -> None:
        """Log listener health transitions; deliberately do not repair them."""
        try:
            listener = getattr(self.scanner, '_listener', None)
            state = (
                self.scanner.listener_is_alive(),
                bool(getattr(listener, 'running', False)) if listener is not None else False,
                bool(getattr(self.scanner, '_enabled', False)),
            )
            if force or state != self._lastScannerHealth:
                self._lastScannerHealth = state
                trace_scanner_event(
                    'listener_health',
                    listener_alive=state[0],
                    listener_running=state[1],
                    scanner_enabled=state[2],
                )
        except Exception:
            pass

    def install_event_filter(self, app_or_widget):
        """Install this manager as an event filter."""
        try:
            app_or_widget.installEventFilter(self)
        except Exception:
            pass

    def _start_scanner_modal_block(self):
        self._modalBlockScanner = True

    def _end_scanner_modal_block(self):
        self._modalBlockScanner = False

    def set_barcode_override(self, override_func):
        self._barcodeOverride = override_func

    def clear_barcode_override(self):
        self._barcodeOverride = None

    def stop(self):
        try:
            self._scannerHealthTimer.stop()
            self._scannerSummaryTimer.stop()
            self._trace_scanner_summary()
        except Exception:
            pass
        self.scanner.stop()
