"""High-level barcode scanner routing and UI leak cleanup."""

from PyQt5.QtCore import QObject
from config import SCANNER_KEY_INTERVAL_SECONDS, SCANNER_UI_SUPPRESS_SECONDS
from modules.devices.scanner import BarcodeScanner

class BarcodeManager(QObject):
    """Manage scanner events, dialog overrides, modal blocking, and scan leaks."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scanner = BarcodeScanner()
        self._modalBlockScanner = False
        self._barcodeOverride = None
        self._scannerCandidateUntil = 0.0
        self.scanner.barcode_scanned.connect(self.on_barcode_scanned)
        self.scanner.scanner_activity.connect(self._on_scanner_activity)
        self.scanner.start()


    def on_barcode_scanned(self, barcode: str):
        """Route a completed barcode scan to the active context."""
        parent = self.parent()
        barcode = (barcode or '').strip()

        # Dialog overrides may accept scans that start in a product-code field.
        try:
            from PyQt5.QtWidgets import QApplication, QLabel
            override = getattr(self, '_barcodeOverride', None)
            fw = QApplication.instance().focusWidget() if QApplication.instance() else None
            obj_name = fw.objectName() if fw and hasattr(fw, 'objectName') else ''
            scan_start_name = getattr(self, '_scanStartObjName', '') or ''
            scan_started_in_code = bool(scan_start_name.endswith('ProductCodeLineEdit'))
            focus_in_code = bool(obj_name.endswith('ProductCodeLineEdit'))
            if callable(override):
                if focus_in_code or scan_started_in_code:
                    handled = False
                    try:
                        handled = override(barcode)
                    except Exception:
                        handled = False
                    if handled:
                        self._cleanup_scanner_leak(fw, barcode)
                        try:
                            start_w = getattr(self, '_scanStartWidget', None)
                            if start_w is not None and start_w is not fw:
                                self._cleanup_scanner_leak(start_w, barcode)
                        except Exception:
                            pass
                        return
                else:
                    if not self._restore_pre_scan_text(fw):
                        self._cleanup_scanner_leak(fw, barcode)
                    dlg = QApplication.activeModalWidget() or QApplication.activeWindow()
                    try:
                        if dlg is not None and bool(dlg.property('suppressBarcodeWarning')):
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
                            status_lbl.setText('Scan only in Product Code field')
                    return
        except Exception:
            pass

        # If a held receipt is loaded into the cart, do not permit scanner-driven
        # routing into the main sales/payment flow. Keep dialog overrides working
        # (override logic above) so ProductCode dialogs can still accept scans.
        try:
            ctx = getattr(parent, 'receipt_context', {}) or {}
            if ctx.get('source') == 'HOLD_LOADED':
                self._ignore_scan(barcode, reason='hold-loaded')
                return
        except Exception:
            pass

        status_bar = getattr(parent, 'statusbar', None)

        # Generic scanner-blocked modals do not own scans.
        try:
            if getattr(self, '_modalBlockScanner', False):
                self._ignore_scan(barcode, reason='modal-block-open')
                return
        except Exception:
            pass

        # Quantity editor input must stay manual.
        try:
            from PyQt5.QtWidgets import QApplication
            fw = QApplication.instance().focusWidget() if QApplication.instance() else None
            if fw is not None and getattr(fw, 'objectName', lambda: '')() == 'qtyInput':
                self._ignore_scan(barcode, reason='qtyInput-focused')
                return
        except Exception:
            pass

        readiness_gate = getattr(parent, '_require_sales_table_ready', None)
        if callable(readiness_gate) and not readiness_gate():
            self._ignore_scan(barcode, reason='sales-table-unavailable')
            return

        try:
            from modules.table_ui import handle_barcode_scanned
            try:
                from modules.table_ui.table_operations import get_product_info
                found, _, _, _ = get_product_info(barcode)
            except Exception:
                found = True
            if not found:
                if status_bar and hasattr(status_bar, 'showMessage'):
                    status_bar.showMessage(f"Product '{barcode}' not found - Opening Product Management (ADD)", 3000)
                if hasattr(parent, 'open_product_menu_dialog'):
                    parent.open_product_menu_dialog(initial_mode='add', initial_code=barcode)
                return
            if hasattr(parent, 'sales_table') and parent.sales_table is not None:
                try:
                    handle_barcode_scanned(parent.sales_table, barcode, status_bar)
                except Exception as exc:
                    marker = getattr(parent, '_mark_sales_table_unavailable', None)
                    if callable(marker):
                        marker(exc, where="Populate sales table from barcode scan")
                    return
            elif status_bar and hasattr(status_bar, 'showMessage'):
                readiness_gate = getattr(parent, '_require_sales_table_ready', None)
                if callable(readiness_gate):
                    readiness_gate()
                else:
                    status_bar.showMessage(f"Scanned: {barcode}", 3000)
        except Exception:
            pass

    def _on_scanner_activity(self, _when_ts: float, is_fast: bool = False):
        """Track burst timing and snapshot focused text before scanner characters land."""
        import time
        now = time.time()
        
        if now > getattr(self, '_scannerCandidateUntil', 0.0):
            try:
                from PyQt5.QtWidgets import QApplication, QLineEdit, QTextEdit, QPlainTextEdit
                app = QApplication.instance()
                fw = app.focusWidget() if app else None
                
                self._scanStartWidget = fw
                self._scanStartObjName = fw.objectName() if fw and hasattr(fw, 'objectName') else ''
                self._scanStartTs = now
                
                self._preScanText = None
                if fw:
                    if isinstance(fw, QLineEdit):
                        self._preScanText = fw.text()
                    elif isinstance(fw, (QTextEdit, QPlainTextEdit)):
                        self._preScanText = fw.toPlainText()
            except Exception:
                self._preScanText = None
        if is_fast:
            # Covers typical 12-14 digit scans plus Enter suffix.
            self._scannerCandidateUntil = max(
                getattr(self, '_scannerCandidateUntil', 0.0),
                now + SCANNER_UI_SUPPRESS_SECONDS,
            )
            self._suppressEnterUntil = max(
                getattr(self, '_suppressEnterUntil', 0.0),
                now + SCANNER_UI_SUPPRESS_SECONDS,
            )
        else:
            self._scannerCandidateUntil = now + SCANNER_KEY_INTERVAL_SECONDS

    def _restore_pre_scan_text(self, fw):
        """Restore focused editable text captured at scan-burst start."""
        try:
            from PyQt5.QtWidgets import QLineEdit, QTextEdit, QPlainTextEdit
            saved = getattr(self, '_preScanText', None)
            
            if fw is not None and saved is not None:
                if isinstance(fw, QLineEdit):
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

    def eventFilter(self, obj, event):
        import time
        from PyQt5.QtCore import QEvent, Qt
        from PyQt5.QtWidgets import QApplication
        if event.type() == QEvent.KeyPress:
            k = event.key()
            now = time.time()
            try:
                if getattr(self, '_modalBlockScanner', False):
                    app = QApplication.instance()
                    fw = app.focusWidget() if app else None
                    modal = app.activeModalWidget() if app else None

                    try:
                        if modal is not None and fw is not None and fw.window() is modal:
                            pass
                        else:
                            text = event.text() or ''
                            is_printable = len(text) == 1 and (31 < ord(text) < 127)
                            if is_printable or k in (Qt.Key_Return, Qt.Key_Enter):
                                self._restore_pre_scan_text(fw)
                                return True
                    except Exception:
                        text = event.text() or ''
                        is_printable = len(text) == 1 and (31 < ord(text) < 127)
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
            
            from PyQt5.QtWidgets import QLineEdit, QTextEdit, QPlainTextEdit

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

    def _ignore_scan(self, barcode: str, reason: str = ''):
        try:
            from PyQt5.QtWidgets import QApplication
            fw = QApplication.instance().focusWidget() if QApplication.instance() else None
            if not self._restore_pre_scan_text(fw):
                self._cleanup_scanner_leak(fw, barcode)
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
        self.scanner.stop()
