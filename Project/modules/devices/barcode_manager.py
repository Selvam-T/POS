"""
Barcode Manager Module
Handles high-level barcode scanner logic, routing, and application state management.
Imports and uses BarcodeScanner from scanner.py.
"""

from PyQt5.QtCore import QObject
from modules.devices.scanner import BarcodeScanner

class BarcodeManager(QObject):
    """
    Manages barcode scanner events, routing, and modal blocking for the application.
    
    Barcode scan leak prevention strategy:
    - At the start of a scanner burst, _on_scanner_activity() snapshots the current text of the focused widget.
    - If a scan is routed to a forbidden widget, eventFilter() restores the widget's text to the snapshot, wiping any leaked characters.
    - Only allowed widgets (e.g., product code fields) accept the scan; all others are protected from unwanted input.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scanner = BarcodeScanner()
        self._modalBlockScanner = False
        self._barcodeOverride = None
        self.scanner.barcode_scanned.connect(self.on_barcode_scanned)
        self.scanner.scanner_activity.connect(self._on_scanner_activity)
        self.scanner.start()


    def on_barcode_scanned(self, barcode: str):
        """
        Handle barcode scanned event. Routes barcode to appropriate handler based on current context.
        """
        parent = self.parent()
        barcode = (barcode or '').strip()

        # Generalized barcode override logic for all dialogs with *ProductCodeLineEdit
        try:
            from PyQt5.QtWidgets import QApplication, QLabel
            override = getattr(self, '_barcodeOverride', None)
            fw = QApplication.instance().focusWidget() if QApplication.instance() else None
            obj_name = fw.objectName() if fw and hasattr(fw, 'objectName') else ''
            # During fast scans, focus may change before the Enter suffix arrives (e.g., auto-lookup
            # logic moves focus to an OK button). Track the scan-start focus to keep overrides usable.
            scan_start_name = getattr(self, '_scanStartObjName', '') or ''
            scan_started_in_code = bool(scan_start_name.endswith('ProductCodeLineEdit'))
            focus_in_code = bool(obj_name.endswith('ProductCodeLineEdit'))
            # Allow scan only if focus is in a product code field (endswith convention)
            if callable(override):
                if focus_in_code or scan_started_in_code:
                    handled = False
                    try:
                        handled = override(barcode)
                    except Exception:
                        handled = False
                    if handled:
                        # Best-effort cleanup on both current focus and scan-start widget.
                        self._cleanup_scanner_leak(fw, barcode)
                        try:
                            start_w = getattr(self, '_scanStartWidget', None)
                            if start_w is not None and start_w is not fw:
                                self._cleanup_scanner_leak(start_w, barcode)
                        except Exception:
                            pass
                        return  # accepted by dialog
                else:
                    # Clean up the leaked char, keep focus, show error
                    self._cleanup_scanner_leak(fw, barcode)
                    # Show error in a status label if present (try to find any QLabel ending with StatusLabel)
                    dlg = QApplication.activeModalWidget() or QApplication.activeWindow()
                    if dlg is not None:
                        # Try to find a status label with a common naming pattern
                        status_lbl = None
                        for lbl_name in ['addStatusLabel', 'removeStatusLabel', 'updateStatusLabel', 'refundStatusLabel', 'historyStatusLabel']:
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

        # Get status bar reference
        status_bar = getattr(parent, 'statusbar', None)

        # If a generic modal (e.g., manual entry) is open, ignore scan and cleanup any leaked char
        try:
            if getattr(self, '_modalBlockScanner', False):
                self._ignore_scan(barcode, reason='modal-block-open')
                return
        except Exception:
            pass

        # If focus is in salesTable quantity editor, ignore scan
        try:
            from PyQt5.QtWidgets import QApplication
            fw = QApplication.instance().focusWidget() if QApplication.instance() else None
            if fw is not None and getattr(fw, 'objectName', lambda: '')() == 'qtyInput':
                self._ignore_scan(barcode, reason='qtyInput-focused')
                return
        except Exception:
            pass

        # If focus is in payment refund input, route code there
        try:
            if fw is not None and getattr(fw, 'objectName', lambda: '')() == 'refundInput':
                try:
                    fw.setText(barcode)
                except Exception:
                    pass
                return
        except Exception:
            pass

        try:
            from modules.table import handle_barcode_scanned
            try:
                from modules.table.table_operations import get_product_info
                found, _, _, _ = get_product_info(barcode)
            except Exception:
                found = True
            if not found:
                # Product not found - open Product Management in ADD mode with code prefilled
                if status_bar and hasattr(status_bar, 'showMessage'):
                    status_bar.showMessage(f"Product '{barcode}' not found - Opening Product Management (ADD)", 3000)
                if hasattr(parent, 'open_product_menu_dialog'):
                    parent.open_product_menu_dialog(initial_mode='add', initial_code=barcode)
                return
            # Product found - add to sales table
            if hasattr(parent, 'sales_table') and parent.sales_table is not None:
                handle_barcode_scanned(parent.sales_table, barcode, status_bar)
            elif status_bar and hasattr(status_bar, 'showMessage'):
                status_bar.showMessage(f"Scanned: {barcode}", 3000)
        except Exception:
            pass

    def _on_scanner_activity(self, when_ts: float):
        """
        Swallow Enter/Return keys briefly during scanner activity to avoid triggering default buttons.
        
        Also takes a snapshot of the focused widget's text at the very start of a scanner burst.
        This snapshot is used to restore the widget if a scan is later rejected (forbidden field).
        """
        import time
        now = time.time()
        
        # This block triggers at the very START of a new barcode burst
        if now > getattr(self, '_scannerActiveUntil', 0.0):
            try:
                from PyQt5.QtWidgets import QApplication, QLineEdit, QTextEdit, QPlainTextEdit
                app = QApplication.instance()
                fw = app.focusWidget() if app else None
                
                self._scanStartWidget = fw
                self._scanStartObjName = fw.objectName() if fw and hasattr(fw, 'objectName') else ''
                self._scanStartTs = now
                
                # We save the text BEFORE the scanner types into it
                self._preScanText = None
                if fw:
                    if isinstance(fw, QLineEdit):
                        self._preScanText = fw.text()
                    elif isinstance(fw, (QTextEdit, QPlainTextEdit)):
                        self._preScanText = fw.toPlainText()
            except Exception:
                self._preScanText = None
        # timing logic to detect fast scanner input
        prev = getattr(self, '_scannerPrevTs', 0.0) or 0.0
        dt = when_ts - prev if prev > 0 else None
        if dt is not None and dt <= 0.08:
            # Extend windows long enough for typical 12–14 digit scans + Enter suffix.
            self._scannerActiveUntil = max(getattr(self, '_scannerActiveUntil', 0.0), now + 0.90)
            self._suppressEnterUntil = max(getattr(self, '_suppressEnterUntil', 0.0), now + 0.90)
        self._scannerPrevTs = when_ts

    def _restore_pre_scan_text(self, fw):
        """
        Rolls back a widget to its state before the current scan burst started.
        Used to wipe any leaked scanner characters from forbidden widgets.
        """
        try:
            from PyQt5.QtWidgets import QLineEdit, QTextEdit, QPlainTextEdit
            # Get the saved text from the snapshot taken in _on_scanner_activity
            saved = getattr(self, '_preScanText', None)
            
            if fw is not None and saved is not None:
                if isinstance(fw, QLineEdit):
                    fw.setText(saved)
                elif isinstance(fw, (QTextEdit, QPlainTextEdit)):
                    if isinstance(fw, QTextEdit):
                        fw.setHtml(saved) if '<' in saved else fw.setPlainText(saved)
                    else:
                        fw.setPlainText(saved)
        except Exception:
            pass

    def eventFilter(self, obj, event):
        import time
        from PyQt5.QtCore import QEvent, Qt
        from PyQt5.QtWidgets import QApplication
        if event.type() == QEvent.KeyPress:
            # Barcode scan leak prevention:
            # If a forbidden widget receives scanner input during a scan burst, restore its text to the pre-scan snapshot.
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
                                # --- RESTORATION POINT 1: Modal Blocking ---
                                # If a scan leaks while a modal is open, wipe it.
                                self._restore_pre_scan_text(fw)
                                return True
                    except Exception:
                        text = event.text() or ''
                        is_printable = len(text) == 1 and (31 < ord(text) < 127)
                        if is_printable or k in (Qt.Key_Return, Qt.Key_Enter):
                            self._restore_pre_scan_text(fw) # Wipes leak
                            return True
            except Exception:
                pass

            if k in (Qt.Key_Return, Qt.Key_Enter) and now <= getattr(self, '_suppressEnterUntil', 0.0):
                return True

            if now <= getattr(self, '_scannerActiveUntil', 0.0):
                app = QApplication.instance()
                fw = app.focusWidget() if app else None
                
                # Get the object name safely
                obj_name = fw.objectName() if fw and hasattr(fw, 'objectName') else ''

                # Only these fields are permitted to receive scanner input.
                is_allowed = (
                    obj_name in ('productCodeLineEdit', 'refundInput')
                    or obj_name.endswith('ProductCodeLineEdit')
                )
                
                text = event.text() or ''
                is_printable = len(text) == 1 and (31 < ord(text) < 127)
                
                # If it's a scanner-typed character and NOT an allowed field, wipe and block.
                if is_printable and not is_allowed:
                    self._restore_pre_scan_text(fw) # Roll back to original text
                    return True

        return super().eventFilter(obj, event)
    
    def _cleanup_scanner_leak(self, fw, barcode):
        try:
            if fw is None or not barcode:
                return
            
            ch = barcode[0] # The first digit of the scan
            
            from PyQt5.QtWidgets import QLineEdit, QTextEdit, QPlainTextEdit

            if isinstance(fw, QLineEdit):
                txt = fw.text() or ''
                # Only check if the text ends with the leaked character
                if txt.endswith(ch):
                    fw.setText(txt[:-1])
                    return

            elif isinstance(fw, (QTextEdit, QPlainTextEdit)):
                t = fw.toPlainText() or ''
                if t.endswith(ch):
                    # For TextEdits, we remove the last char
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
            self._cleanup_scanner_leak(fw, barcode)
        except Exception:
            pass
    def install_event_filter(self, app_or_widget):
        """
        Installs this BarcodeManager as an event filter on the given QApplication or QWidget.
        """
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
