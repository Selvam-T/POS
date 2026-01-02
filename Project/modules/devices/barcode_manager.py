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
        try:
            from config import DEBUG_SCANNER_FOCUS, DEBUG_CACHE_LOOKUP
            if DEBUG_SCANNER_FOCUS and hasattr(parent, '_debug_print_focus'):
                parent._debug_print_focus(context='on_barcode_scanned', barcode=barcode)
        except Exception:
            pass
        barcode = (barcode or '').strip()
        try:
            from modules.db_operation import get_product_info, PRODUCT_CACHE
            found, product_name, unit_price, _ = get_product_info(barcode)
            if DEBUG_CACHE_LOOKUP:
                raw = barcode
                norm = (raw or '').strip().upper()
                found_key = None
                if norm in PRODUCT_CACHE:
                    found_key = norm
                elif raw in PRODUCT_CACHE:
                    found_key = raw
                elif (raw or '').lower() in PRODUCT_CACHE:
                    found_key = (raw or '').lower()
                elif (raw or '').upper() in PRODUCT_CACHE:
                    found_key = (raw or '').upper()
                cache_size = len(PRODUCT_CACHE)
                print('[Scanner][Cache]', f"code='{raw}'", f"norm='{norm}'", f"found={'yes' if found else 'no'}", f"key='{found_key}'", f"name='{product_name}'", f"price={unit_price:.2f}", f"cacheSize={cache_size}")
        except Exception as _e:
            print('[Scanner][Cache] debug failed:', _e)

        # Generalized barcode override logic for all dialogs with *ProductCodeLineEdit
        try:
            from PyQt5.QtWidgets import QApplication, QLineEdit, QLabel
            override = getattr(self, '_barcodeOverride', None)
            fw = QApplication.instance().focusWidget() if QApplication.instance() else None
            obj_name = fw.objectName() if fw and hasattr(fw, 'objectName') else ''
            # Allow scan only if focus is in a product code field (endswith convention)
            if callable(override):
                if obj_name.endswith('ProductCodeLineEdit'):
                    handled = False
                    try:
                        handled = override(barcode)
                    except Exception:
                        handled = False
                    if handled:
                        self._cleanup_scanner_leak(fw, barcode)
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
            if not found:
                # Product not found - open Product Management in ADD mode with code prefilled
                if status_bar and hasattr(status_bar, 'showMessage'):
                    status_bar.showMessage(f"⚠ Product '{barcode}' not found - Opening Product Management (ADD)", 3000)
                if hasattr(parent, 'open_product_menu_dialog'):
                    parent.open_product_menu_dialog(initial_mode='add', initial_code=barcode)
                return
            # Product found - add to sales table
            if hasattr(parent, 'sales_table') and parent.sales_table is not None:
                handle_barcode_scanned(parent.sales_table, barcode, status_bar)
            elif status_bar and hasattr(status_bar, 'showMessage'):
                status_bar.showMessage(f"📷 Scanned: {barcode}", 3000)
        except Exception:
            pass

    def _on_scanner_activity(self, when_ts: float):
        """
        Swallow Enter/Return keys briefly during scanner activity to avoid triggering default buttons
        """
        import time
        parent = self.parent()
        now = time.time()
        prev = getattr(self, '_scannerPrevTs', 0.0) or 0.0
        dt = when_ts - prev if prev > 0 else None
        if dt is not None and dt <= 0.08:
            self._scannerActiveUntil = max(getattr(self, '_scannerActiveUntil', 0.0), now + 0.25)
            self._suppressEnterUntil = max(getattr(self, '_suppressEnterUntil', 0.0), now + 0.15)
        self._scannerPrevTs = when_ts
    def eventFilter(self, obj, event):
        import time
        from PyQt5.QtCore import QEvent, Qt
        from PyQt5.QtWidgets import QApplication
        if event.type() == QEvent.KeyPress:
            k = event.key()
            now = time.time()
            try:
                if getattr(self, '_modalBlockScanner', False):
                    # Check if focus is on an editable input widget
                    app = QApplication.instance()
                    fw = app.focusWidget() if app else None
                    obj_name = ''
                    try:
                        obj_name = fw.objectName() if fw is not None else ''
                    except Exception:
                        obj_name = ''
                    
                    # Allow input in specific editable fields or QPushButton even during modal block
                    from PyQt5.QtWidgets import QPushButton
                    is_allowed_input = obj_name in (
                        'qtyInput', 'productCodeLineEdit', 'refundInput',
                        'inputProductName', 'inputSellingPrice',
                        'inputSupplier', 'inputCostPrice',
                        'inputQuantity', 'inputUnitPrice',
                        'vegMCostPriceLineEdit', 'vegMProductNameLineEdit',
                        'vegMSellingPriceLineEdit', 'vegMSupplierLineEdit',
                        'addProductNameLineEdit', 'addCostPriceLineEdit',
                        'addSellingPriceLineEdit', 'addSupplierLineEdit',
                        'updateProductNameLineEdit', 'updateCostPriceLineEdit',
                        'updateSellingPriceLineEdit', 'updateSupplierLineEdit',
                        'removeSearchComboLineEdit', 'updateSearchComboLineEdit',
                        # Manual entry dialog fields:
                        'manualProductCodeLineEdit', 'manualNameSearchLineEdit', 'manualQuantityLineEdit'
                    )
                    # Also allow if the focused widget is a QPushButton
                    if fw is not None:
                        try:
                            from PyQt5.QtWidgets import QPushButton
                            if isinstance(fw, QPushButton):
                                is_allowed_input = True
                        except Exception:
                            pass
                    if not is_allowed_input:
                        text = ''
                        try:
                            text = event.text() or ''
                        except Exception:
                            text = ''
                        is_printable = len(text) == 1 and (31 < ord(text) < 127)
                        if is_printable or k in (Qt.Key_Return, Qt.Key_Enter):
                            return True
            except Exception:
                pass
            if k in (Qt.Key_Return, Qt.Key_Enter) and now <= getattr(self, '_suppressEnterUntil', 0.0):
                return True
            if now <= getattr(self, '_scannerActiveUntil', 0.0):
                app = QApplication.instance()
                fw = app.focusWidget() if app else None
                obj_name = ''
                try:
                    obj_name = fw.objectName() if fw is not None else ''
                except Exception:
                    obj_name = ''
                is_qty = (obj_name == 'qtyInput')
                is_allowed = (obj_name in ('productCodeLineEdit', 'refundInput')) and not is_qty
                text = ''
                try:
                    text = event.text() or ''
                except Exception:
                    text = ''
                is_printable = len(text) == 1 and (31 < ord(text) < 127)
                if is_printable and not is_allowed:
                    return True
        from PyQt5.QtCore import QObject
        return super().eventFilter(obj, event)
    def _cleanup_scanner_leak(self, fw, barcode):
        try:
            if fw is None or not barcode:
                return
            ch = barcode[0]
            name = getattr(fw, 'objectName', lambda: '')()
            try:
                from PyQt5.QtWidgets import QLineEdit
                if isinstance(fw, QLineEdit):
                    txt = fw.text() or ''
                    if txt.endswith(ch) and len(txt) <= 3:
                        fw.setText(txt[:-1])
                    return
            except Exception:
                pass
            try:
                from PyQt5.QtWidgets import QTextEdit, QPlainTextEdit
                from PyQt5.QtGui import QTextCursor
                if isinstance(fw, (QTextEdit, QPlainTextEdit)):
                    t = fw.toPlainText()
                    if t.endswith(ch) and len(t) <= 3:
                        if isinstance(fw, QTextEdit):
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
        except Exception:
            pass

    def _ignore_scan(self, barcode: str, reason: str = ''):
        try:
            from PyQt5.QtWidgets import QApplication
            parent = self.parent()
            fw = QApplication.instance().focusWidget() if QApplication.instance() else None
            self._cleanup_scanner_leak(fw, barcode)
            try:
                from config import DEBUG_SCANNER_FOCUS
                if DEBUG_SCANNER_FOCUS and hasattr(parent, '_describe_widget'):
                    print('[Scanner][Ignore]', f"reason='{reason}'", 'focus=', parent._describe_widget(fw))
            except Exception:
                pass
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
