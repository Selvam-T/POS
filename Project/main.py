#!/usr/bin/env python3
"""
POS System - UI loader that composes `main_window.ui`, `sales_frame.ui`, and `payment_frame.ui`.
Loads a QSS file from `assets/style.qss` when present.
"""
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import sys
import os
import time
from PyQt5 import uic
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QTableWidget,
    QPushButton,
    QLineEdit,
    QLabel,
    QDialog,
    QComboBox,
    QSlider,
    QCompleter,
    QTabWidget,
)
from PyQt5.QtCore import Qt, QSize, QEvent
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtGui import QFontMetrics, QIcon
from modules.sales.salesTable import setup_sales_table, handle_barcode_scanned, bind_total_label
from modules.devices import BarcodeScanner
from modules.menu.logout_menu import open_logout_dialog as open_logout_dialog_menu
from modules.menu.admin_menu import open_admin_dialog as open_admin_dialog_menu
from modules.menu.devices_menu import open_devices_dialog as open_devices_dialog_menu
from modules.menu.reports_menu import open_reports_dialog as open_reports_dialog_menu
from modules.menu.greeting_menu import open_greeting_dialog as open_greeting_dialog_menu
from modules.menu.product_menu import open_product_dialog as open_product_dialog_menu
from modules.menu.vegetable_menu import VegetableMenuDialog

from config import (
    ICON_ADMIN,
    ICON_REPORTS,
    ICON_VEGETABLE,
    ICON_PRODUCT,
    ICON_GREETING,
    ICON_DEVICE,
    ICON_LOGOUT,
    DEBUG_SCANNER_FOCUS,
    DEBUG_FOCUS_CHANGES,
    DEBUG_CACHE_LOOKUP,
)
from modules.date_time.info_section import InfoSectionController

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')


def load_qss(app):
    qss_path = os.path.join(ASSETS_DIR, 'style.qss')
    if os.path.exists(qss_path):
        try:
            with open(qss_path, 'r', encoding='utf-8') as f:
                app.setStyleSheet(f.read())
        except Exception as e:
            print('Failed to load QSS:', e)


class MainLoader(QMainWindow):
    def open_logout_menu_dialog(self):
        """Open the Logout dialog via standardized method using the common wrapper."""
        self.open_menu_dialog_wrapper(open_logout_dialog_menu)

    def open_product_menu_dialog(self, **kwargs):
        """Open the Product Management panel via standardized method using the common wrapper.
        Accepts kwargs for context (e.g., initial_mode, initial_code) to control tab and prefill logic.
        """
        self.open_menu_dialog_wrapper(open_product_dialog_menu, **kwargs)

    def open_admin_menu_dialog(self):
        """Open the Admin dialog via standardized method using the common wrapper."""
        self.open_menu_dialog_wrapper(open_admin_dialog_menu, current_user='Admin', is_admin=True)

    def open_greeting_menu_dialog(self):
        """Open the Greeting dialog via standardized method using the common wrapper."""
        self.open_menu_dialog_wrapper(open_greeting_dialog_menu)

    def open_devices_menu_dialog(self):
        """Open the Devices dialog via standardized method using the common wrapper."""
        self.open_menu_dialog_wrapper(open_devices_dialog_menu)

    def open_reports_menu_dialog(self):
        """Open the Reports dialog via standardized method using the common wrapper."""
        self.open_menu_dialog_wrapper(open_reports_dialog_menu)

    def open_vegetable_menu_dialog(self):
        """Open the Vegetable Label Edit dialog via standardized method using the common wrapper."""
        self.open_menu_dialog_wrapper(VegetableMenuDialog)


    # open_logout_menu_dialog now uses the common wrapper; no separate logic needed
    def open_menu_dialog_wrapper(self, dialog_func, width_ratio=0.45, height_ratio=0.4, *args, **kwargs):
        """Common wrapper for opening menu dialogs with overlay, sizing, and cleanup."""
    # ...
        self._show_dim_overlay()
        try:
            dlg = dialog_func(self, *args, **kwargs)
            # ...
            # If the dialog function returns a QDialog, set size/position; else assume it handles itself
            if isinstance(dlg, QDialog):
                mw, mh = self.frameGeometry().width(), self.frameGeometry().height()
                dw, dh = max(360, int(mw * width_ratio)), max(220, int(mh * height_ratio))
                dlg.setFixedSize(dw, dh)
                mx, my = self.frameGeometry().x(), self.frameGeometry().y()
                dlg.move(mx + (mw - dw) // 2, my + (mh - dh) // 2)
                def _cleanup(_):
                    self._hide_dim_overlay()
                    self.raise_()
                    self.activateWindow()
                dlg.finished.connect(_cleanup)
                # ...
                dlg.exec_()
                # ...
            else:
                # ...
                self._hide_dim_overlay()
        except Exception as e:
            self._hide_dim_overlay()
            print('Dialog failed:', e)

    
    def __init__(self):
        super().__init__()
        main_ui = os.path.join(UI_DIR, 'main_window.ui')
        uic.loadUi(main_ui, self)
        # Remove the window close button (X) to force using Logout
        try:
            flags = self.windowFlags()
            flags |= Qt.CustomizeWindowHint | Qt.WindowTitleHint
            flags &= ~Qt.WindowCloseButtonHint
            self.setWindowFlags(flags)
            self._allow_close = False
        except Exception:
            self._allow_close = False
        # Ensure header layout stretches keep center truly centered
        try:
            info_layout = self.findChild(QHBoxLayout, 'infoSection')
            if info_layout is not None:
                info_layout.setStretch(0, 1)
                info_layout.setStretch(1, 0)
                info_layout.setStretch(2, 1)
        except Exception:
            pass

        # Use InfoSectionController for header info section
        self.info = InfoSectionController().bind(self).start_clock()

        # Initialize barcode scanner
        self.scanner = BarcodeScanner()
        self.scanner.barcode_scanned.connect(self.on_barcode_scanned)
        self.scanner.start()

        # Insert sales_frame.ui into placeholder named 'salesFrame'
        sales_placeholder = getattr(self, 'salesFrame', None)
        sales_ui = os.path.join(UI_DIR, 'sales_frame.ui')
        if sales_placeholder is not None and os.path.exists(sales_ui):
            sales_widget = uic.loadUi(sales_ui)
            sales_layout = sales_placeholder.layout()
            if sales_layout is None:
                sales_layout = QVBoxLayout(sales_placeholder)
                sales_placeholder.setLayout(sales_layout)
            try:
                sales_layout.setContentsMargins(8, 8, 8, 8)
                sales_layout.setSpacing(10)
            except Exception:
                pass
            sales_layout.addWidget(sales_widget)

            # Restore sales frame layout logic for table and containers
            try:
                # Children order: 0=salesLabel, 1=salesTable, 2=totalContainer, 3=addBtnLayout, 4=receiptLayout
                sales_layout.setStretch(0, 0)
                sales_layout.setStretch(1, 7)
                sales_layout.setStretch(2, 2)
                sales_layout.setStretch(3, 2)
                sales_layout.setStretch(4, 2)

                def em_px(widget: QWidget, units: float) -> int:
                    fm = QFontMetrics(widget.font())
                    return int(round(units * fm.lineSpacing()))

                total_container = sales_widget.findChild(QWidget, 'totalContainer')
                if total_container is not None:
                    total_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                    h = em_px(total_container, 3.6)
                    total_container.setMinimumHeight(h)
                    total_container.setMaximumHeight(h)

                add_container = sales_widget.findChild(QWidget, 'addContainer')
                if add_container is not None:
                    add_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                    h = em_px(add_container, 4.0)
                    add_container.setMinimumHeight(h)
                    add_container.setMaximumHeight(h)
                    for btn_name in ('vegBtn', 'manualBtn'):
                        btn = sales_widget.findChild(QPushButton, btn_name)
                        if btn is not None:
                            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

                receipt_container = sales_widget.findChild(QWidget, 'receiptContainer')
                if receipt_container is not None:
                    receipt_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                    h = em_px(receipt_container, 4.0)
                    receipt_container.setMinimumHeight(h)
                    receipt_container.setMaximumHeight(h)
                    for btn_name in ('cancelsaleBtn', 'onholdBtn', 'viewholdBtn'):
                        btn = sales_widget.findChild(QPushButton, btn_name)
                        if btn is not None:
                            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

                sale_table = sales_widget.findChild(QTableWidget, 'salesTable')
                if sale_table is not None:
                    sale_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                    sale_table.setMinimumHeight(em_px(sales_widget, 10))
                    setup_sales_table(sale_table)
                    self.sales_table = sale_table
            except Exception:
                pass

        # Insert payment_frame.ui into placeholder named 'paymentFrame'
        payment_placeholder = getattr(self, 'paymentFrame', None)
        payment_ui = os.path.join(UI_DIR, 'payment_frame.ui')
        if payment_placeholder is not None and os.path.exists(payment_ui):
            payment_widget = uic.loadUi(payment_ui)
            payment_layout = payment_placeholder.layout()
            if payment_layout is None:
                payment_layout = QVBoxLayout(payment_placeholder)
                payment_placeholder.setLayout(payment_layout)
            try:
                payment_layout.setContentsMargins(8, 8, 8, 8)
            except Exception:
                pass
            payment_layout.addWidget(payment_widget)

        # Insert menu_frame.ui into placeholder named 'menuFrame'
        menu_placeholder = getattr(self, 'menuFrame', None)
        menu_ui = os.path.join(UI_DIR, 'menu_frame.ui')
        if menu_placeholder is not None and os.path.exists(menu_ui):
            menu_widget = uic.loadUi(menu_ui)
            menu_layout = menu_placeholder.layout()
            if menu_layout is None:
                menu_layout = QVBoxLayout(menu_placeholder)
                menu_placeholder.setLayout(menu_layout)
            try:
                menu_layout.setContentsMargins(8, 8, 8, 8)
            except Exception:
                pass
            menu_layout.addWidget(menu_widget)

        # ----------------- Menu buttons wiring and icons -----------------
        # Map buttons to config-defined icons (must be in outer scope for try block)
        button_icons = {
            'adminBtn': ICON_ADMIN,
            'reportsBtn': ICON_REPORTS,
            'vegetableBtn': ICON_VEGETABLE,
            'productBtn': ICON_PRODUCT,
            'greetingBtn': ICON_GREETING,
            'deviceBtn': ICON_DEVICE,
            'logoutBtn': ICON_LOGOUT,
        }
        try:
            def set_btn_icon_path(btn: QPushButton, rel_path: str, size: int = 60) -> bool:
                """Set a button icon from a config-defined relative path.
                Returns True on success, False if file missing or error.
                """
                try:
                    abs_path = os.path.join(BASE_DIR, rel_path)
                    if os.path.exists(abs_path):
                        btn.setIcon(QIcon(abs_path))
                        btn.setIconSize(QSize(size, size))
                        return True
                    # Icon file missing; fall back to text label
                    return False
                except Exception as _e:
                    # Ignore icon errors and fall back to text label                    
                    return False

            menu_buttons = {
                'adminBtn': 'Admin',
                'reportsBtn': 'Reports',
                'vegetableBtn': 'Vegetable',
                'productBtn': 'Product',
                'greetingBtn': 'Greeting',
                'deviceBtn': 'Device',
                'logoutBtn': 'Logout',
            }

            for obj_name, title in menu_buttons.items():
                btn = self.findChild(QPushButton, obj_name)
                if btn is None:
                    continue
                # Set icon if available
                icon_rel = button_icons.get(obj_name)
                success = False
                if icon_rel:
                    success = set_btn_icon_path(btn, icon_rel)
                # If icon loaded, keep icon-only; else show text fallback
                try:
                    if success:
                        btn.setProperty('iconFallback', False)
                        btn.setText('')
                    else:
                        btn.setProperty('iconFallback', True)
                        btn.setText(title)
                    # Refresh QSS to apply property changes
                    btn.style().unpolish(btn)
                    btn.style().polish(btn)
                    btn.setToolTip(title)
                except Exception:
                    pass
                # Wire click handlers per button
                if obj_name == 'productBtn':
                    btn.clicked.connect(self.open_product_menu_dialog)
                elif obj_name == 'logoutBtn':
                    btn.clicked.connect(self.open_logout_menu_dialog)
                elif obj_name == 'vegetableBtn':
                    btn.clicked.connect(self.open_vegetable_menu_dialog)
                elif obj_name == 'greetingBtn':
                    btn.clicked.connect(self.open_greeting_menu_dialog)
                elif obj_name == 'adminBtn':
                    btn.clicked.connect(self.open_admin_menu_dialog)
                elif obj_name == 'reportsBtn':
                    btn.clicked.connect(self.open_reports_menu_dialog)
                elif obj_name == 'deviceBtn':
                    btn.clicked.connect(self.open_devices_menu_dialog)
                else:
                    try:
                        btn.setEnabled(False)
                        btn.setToolTip(title)
                    except Exception:
                        pass
        except Exception as e:
            print('Failed to wire menu buttons:', e)

        # Install a global event filter to control key delivery during scanner sequences
        try:
            self._suppressEnterUntil = 0.0
            self._scannerPrevTs = 0.0
            self._scannerActiveUntil = 0.0
            # Install at application level so we see events for all widgets
            try:
                QApplication.instance().installEventFilter(self)
            except Exception:
                # Fallback to filtering only within this window hierarchy
                self.installEventFilter(self)
            try:
                # Extend suppression window on each scanner key press
                self.scanner.scanner_activity.connect(self._on_scanner_activity)
            except Exception:
                pass
        except Exception:
            pass

        # Optional: verbose focus change logging
        try:
            if DEBUG_FOCUS_CHANGES:
                app = QApplication.instance()
                if app is not None:
                    app.focusChanged.connect(self._on_focus_changed)
        except Exception:
            pass

    # ----------------- Vegetable panel wiring -----------------
    def open_vegetable_panel(self):
        """Open the Add Vegetable panel as a modal dialog:
        - Size = 60% of main window, centered
        - Dim the main window background while open
        - Only Close (X) button shown (no minimize/maximize)
        - Close on X, OK, or CANCEL; restore brightness on close
        """
        veg_ui = os.path.join(UI_DIR, 'vegetable_entry.ui')
        if not os.path.exists(veg_ui):
            print('vegetable_entry.ui not found at', veg_ui)
            return

        # Create dimming overlay over the main window
        try:
            self._show_dim_overlay()
        except Exception:
            pass

        # Build a modal dialog and embed the loaded UI inside
        try:
            content = uic.loadUi(veg_ui)
        except Exception as e:
            print('Failed to load vegetable_entry.ui:', e)
            try:
                self._hide_dim_overlay()
            except Exception:
                pass
            return

        dlg = QDialog(self)
        dlg.setModal(True)
        dlg.setWindowTitle('Digital Weight Input')
        # Window flags: remove min/max, keep title + close
        dlg.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        # Fixed size at 60% of main window, centered
        try:
            mw = self.frameGeometry().width()
            mh = self.frameGeometry().height()
            dw = max(400, int(mw * 0.6))
            dh = max(300, int(mh * 0.6))
            dlg.setFixedSize(dw, dh)
            # Center relative to main window
            mx = self.frameGeometry().x()
            my = self.frameGeometry().y()
            dlg.move(mx + (mw - dw) // 2, my + (mh - dh) // 2)
        except Exception:
            pass

        # Install content into dialog
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(content)

        # Configure the vegetable table headers and behavior
        try:
            vtable: QTableWidget = content.findChild(QTableWidget, 'vegetableTable')
            if vtable is not None:
                vtable.setColumnCount(4)
                vtable.setHorizontalHeaderLabels(['No.', 'Item', 'Weight (kg)', 'Total'])

                header: QHeaderView = vtable.horizontalHeader()
                header.setStretchLastSection(False)
                header.setSectionResizeMode(0, QHeaderView.Fixed)   # No.
                header.setSectionResizeMode(1, QHeaderView.Stretch) # Item grows
                header.setSectionResizeMode(2, QHeaderView.Fixed)   # Weight
                header.setSectionResizeMode(3, QHeaderView.Fixed)   # Total
                header.resizeSection(0, 48)
                header.resizeSection(2, 120)
                header.resizeSection(3, 110)

                vtable.setAlternatingRowColors(True)
                vtable.setEditTriggers(QTableWidget.NoEditTriggers)
                vtable.setSelectionBehavior(QTableWidget.SelectRows)
                vtable.setSelectionMode(QTableWidget.SingleSelection)
        except Exception as e:
            print('Vegetable table setup failed:', e)

        # Wire keypad buttons to update message label and close on OK/CANCEL (updated to btnVeg1..btnVeg14)
        try:
            msg: QLabel = content.findChild(QLabel, 'messageLabel')
            for name in (
                'btnVeg1','btnVeg2','btnVeg3','btnVeg4',
                'btnVeg5','btnVeg6','btnVeg7','btnVeg8',
                'btnVeg9','btnVeg10','btnVeg11','btnVeg12',
                'btnVeg13','btnVeg14',
            ):
                btn = content.findChild(QPushButton, name)
                if btn is not None and msg is not None:
                    btn.clicked.connect(lambda _, b=btn: msg.setText(f"Selected: {b.text()}"))

            ok_btn = content.findChild(QPushButton, 'btnVegOk')
            cancel_btn = content.findChild(QPushButton, 'btnVegCancel')
            if ok_btn is not None:
                ok_btn.clicked.connect(lambda: dlg.accept())
            if cancel_btn is not None:
                cancel_btn.clicked.connect(lambda: dlg.reject())
        except Exception as e:
            print('Vegetable keypad wiring failed:', e)

        # Ensure overlay hides and focus returns when dialog closes
        def _cleanup_overlay(_code):
            try:
                self._hide_dim_overlay()
            except Exception:
                pass
            # Bring main window back to front
            try:
                self.raise_()
                self.activateWindow()
            except Exception:
                pass
            # Remove barcode override when dialog closes
            try:
                self._clear_barcode_override()
            except Exception:
                pass

        dlg.finished.connect(_cleanup_overlay)

        # Block scanner while this dialog is open
        try:
            self._start_scanner_modal_block()
        except Exception:
            pass

        # Execute modally
        dlg.exec_()
        try:
            self._end_scanner_modal_block()
        except Exception:
            pass



    # (Logout dialog logic moved to modules.menu.logout_menu.open_logout_dialog)

    def _perform_logout(self):
        """Perform logout action: stop devices and close app."""
        # Stop scanner if running
        try:
            if getattr(self, 'scanner', None) is not None:
                self.scanner.stop()
        except Exception:
            pass
        # Allow closing and quit
        try:
            self._allow_close = True
        except Exception:
            pass
        try:
            # Prefer closing the main window; app will quit due to no top-level windows
            self.close()
        except Exception:
            try:
                QApplication.instance().quit()
            except Exception:
                pass

    # ----------------- Manual product entry panel wiring -----------------
    def open_manual_panel(self, message="Manual Product Entry"):
        """Open the Manual Product Entry panel as a modal dialog:
        - Size = 60% of main window, centered
        - Dim the main window background while open
        - Only Close (X) button shown (no minimize/maximize)
        - Close on X or when finished
        
        Args:
            message: Message to display in the QTextEdit widget
        """
        manual_ui = os.path.join(UI_DIR, 'manual_entry.ui')
        if not os.path.exists(manual_ui):
            print('manual_entry.ui not found at', manual_ui)
            return

        # Create dimming overlay over the main window (reuse same overlay as vegetable panel)
        try:
            self._show_dim_overlay()
        except Exception:
            pass

        # Build a modal dialog and embed the loaded UI inside
        try:
            content = uic.loadUi(manual_ui)
        except Exception as e:
            print('Failed to load manual_entry.ui:', e)
            try:
                self._hide_dim_overlay()
            except Exception:
                pass
            return

        dlg = QDialog(self)
        dlg.setModal(True)
        dlg.setWindowTitle('Manual Entry of Product')
        # Window flags: remove min/max, keep title + close
        dlg.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        # Fixed size at 60% of main window, centered
        try:
            mw = self.frameGeometry().width()
            mh = self.frameGeometry().height()
            dw = max(400, int(mw * 0.6))
            dh = max(300, int(mh * 0.6))
            dlg.setFixedSize(dw, dh)
            # Center relative to main window
            mx = self.frameGeometry().x()
            my = self.frameGeometry().y()
            dlg.move(mx + (mw - dw) // 2, my + (mh - dh) // 2)
        except Exception:
            pass

        # Install content into dialog
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(content)

        # Set the message in the QTextEdit widget
        try:
            text_edit = content.findChild(QWidget, 'manualText')
            if text_edit is not None:
                text_edit.setPlainText(message)
                try:
                    # Make it read-only to prevent any visual key leaks
                    text_edit.setReadOnly(True)
                except Exception:
                    pass
        except Exception as e:
            print('Failed to set manual text:', e)

        # Mark that a generic modal is open to block scanner routing
        try:
            self._start_scanner_modal_block()
        except Exception:
            pass

        # Ensure overlay hides and focus returns when dialog closes
        def _cleanup_overlay(_code):
            try:
                self._hide_dim_overlay()
            except Exception:
                pass
            # Bring main window back to front
            try:
                self.raise_()
                self.activateWindow()
            except Exception:
                pass
            # Unblock scanner and restore focus to sales table
            try:
                self._end_scanner_modal_block()
            except Exception:
                pass
            try:
                self._refocus_sales_table()
            except Exception:
                pass

        dlg.finished.connect(_cleanup_overlay)

        # Execute modally
        dlg.exec_()

    # ----------------- Barcode scanner handling -----------------
    def on_barcode_scanned(self, barcode: str):
        """
        Handle barcode scanned event.
        Routes barcode to appropriate handler based on current context.
        
        Args:
            barcode: The scanned barcode string
        """
        # Debug: print where the focus is when a scan is received
        try:
            if DEBUG_SCANNER_FOCUS:
                self._debug_print_focus(context='on_barcode_scanned', barcode=barcode)
        except Exception:
            pass
        # Normalize input once
        barcode = (barcode or '').strip()

        # Early cache lookup and debug so it always prints, even if later ignored/overridden
        from modules.db_operation import get_product_info, PRODUCT_CACHE
        found, product_name, unit_price = get_product_info(barcode)
        try:
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

        # If a modal has installed a barcode override, handle it focus-safely
        try:
            override = getattr(self, '_barcodeOverride', None)
            if callable(override):
                handled = False
                try:
                    handled = override(barcode)
                except Exception:
                    handled = False
                if handled:
                    return  # accepted by dialog
                else:
                    # dialog open but not focused on code field → ignore, cleanup any leak
                    try:
                        self._ignore_scan(barcode, reason='override-not-focused')
                    except Exception:
                        pass
                    return
        except Exception:
            pass

        # Get status bar reference
        status_bar = getattr(self, 'statusbar', None)

        # If a generic modal (e.g., manual entry) is open, ignore scan and cleanup any leaked char
        try:
            if getattr(self, '_modalBlockScanner', False):
                self._ignore_scan(barcode, reason='modal-block-open')
                return
        except Exception:
            pass

        # If focus is in salesTable quantity editor, ignore scan
        try:
            fw = QApplication.instance().focusWidget() if QApplication.instance() else None
            if fw is not None and getattr(fw, 'objectName', lambda: '')() == 'qtyInput':
                # Remove any stray first character leaked into qty input
                try:
                    self._ignore_scan(barcode, reason='qtyInput-focused')
                except Exception:
                    pass
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
        
        if not found:
            # Product not found - open Product Management in ADD mode with code prefilled
            if status_bar:
                status_bar.showMessage(f"⚠ Product '{barcode}' not found - Opening Product Management (ADD)", 3000)
            self.open_product_menu_dialog(initial_mode='add', initial_code=barcode)
            return
        
        # Product found - add to sales table
        if self.sales_table is not None:
            handle_barcode_scanned(self.sales_table, barcode, status_bar)
        else:
            # Fallback: just display in status bar
            if status_bar:
                status_bar.showMessage(f"📷 Scanned: {barcode}", 3000)

    # ...existing code...

    # ----------------- Focus debug helpers -----------------
    def _describe_widget(self, w: QWidget) -> str:
        try:
            if w is None:
                return 'None'
            name = w.objectName() or ''
            cls = w.metaObject().className() if hasattr(w, 'metaObject') else w.__class__.__name__
            if name:
                return f"{cls}(objectName='{name}')"
            return cls
        except Exception:
            return '<unknown>'

    def _debug_print_focus(self, context: str, barcode: str = ''):
        try:
            app = QApplication.instance()
            aw = app.activeWindow() if app else None
            fw = app.focusWidget() if app else None
            # Build parent chain from focus widget up to window
            chain = []
            cur = fw
            seen = 0
            while cur is not None and seen < 10:  # limit to avoid accidental loops
                chain.append(self._describe_widget(cur))
                cur = cur.parent()
                seen += 1
            chain_str = ' -> '.join(reversed(chain)) if chain else 'None'
            win_title = ''
            try:
                if aw and hasattr(aw, 'windowTitle'):
                    win_title = aw.windowTitle()
            except Exception:
                pass
            override = getattr(self, '_barcodeOverride', None)
            print('[Scanner][Focus]',
                  f"context={context}",
                  f"barcode='{barcode}'",
                  f"activeWindow={self._describe_widget(aw)}",
                  f"windowTitle='{win_title}'",
                  f"focusPath={chain_str}",
                  f"override={'yes' if callable(override) else 'no'}")
        except Exception as _e:
            print('[Scanner][Focus] debug failed:', _e)

    def _on_focus_changed(self, old: QWidget, new: QWidget):
        try:
            print('[FocusChanged]', self._describe_widget(old), '->', self._describe_widget(new))
        except Exception:
            pass

    # Swallow Enter/Return keys briefly during scanner activity to avoid triggering default buttons
    def _on_scanner_activity(self, when_ts: float):
        try:
            now = time.time()
            prev = getattr(self, '_scannerPrevTs', 0.0) or 0.0
            dt = when_ts - prev if prev > 0 else None
            # Consider it scanner-like if two consecutive keys are very fast
            if dt is not None and dt <= 0.08:
                # Activate a short window during which we will swallow keys to non-whitelisted fields
                self._scannerActiveUntil = max(getattr(self, '_scannerActiveUntil', 0.0), now + 0.25)
                # Also suppress Enter slightly to avoid button activation
                self._suppressEnterUntil = max(getattr(self, '_suppressEnterUntil', 0.0), now + 0.15)
            # Remember timestamp for next delta computation
            self._scannerPrevTs = when_ts
        except Exception:
            pass

    def eventFilter(self, obj, event):
        try:
            if event.type() == QEvent.KeyPress:
                k = event.key()
                now = time.time()
                # If a generic modal is blocking the scanner, swallow printable keys and Enter immediately
                try:
                    if getattr(self, '_modalBlockScanner', False):
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
                # Swallow Enter during suppression window
                if k in (Qt.Key_Return, Qt.Key_Enter) and now <= getattr(self, '_suppressEnterUntil', 0.0):
                    return True
                # If scanner is active, block character keys to disallowed widgets
                if now <= getattr(self, '_scannerActiveUntil', 0.0):
                    # Determine current focus
                    app = QApplication.instance()
                    fw = app.focusWidget() if app else None
                    # Identify allowed targets
                    obj_name = ''
                    try:
                        obj_name = fw.objectName() if fw is not None else ''
                    except Exception:
                        obj_name = ''
                    # Allowed only in product code field and refund input; disallow qtyInput
                    is_qty = (obj_name == 'qtyInput')
                    is_allowed = (obj_name in ('productCodeLineEdit', 'refundInput')) and not is_qty
                    # Printable char? If so, swallow unless allowed
                    text = ''
                    try:
                        text = event.text() or ''
                    except Exception:
                        text = ''
                    is_printable = len(text) == 1 and (31 < ord(text) < 127)
                    if is_printable and not is_allowed:
                        return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

    # Best-effort cleanup for a stray first character leaked into disallowed inputs during a scan
    def _cleanup_scanner_leak(self, fw: QWidget, barcode: str) -> None:
        try:
            if fw is None or not barcode:
                return
            ch = barcode[0]
            name = getattr(fw, 'objectName', lambda: '')()
            # Handle QLineEdit-like widgets
            try:
                from PyQt5.QtWidgets import QLineEdit
                if isinstance(fw, QLineEdit):
                    txt = fw.text() or ''
                    if txt.endswith(ch) and len(txt) <= 3:
                        fw.setText(txt[:-1])
                    return
            except Exception:
                pass
            # Handle QTextEdit/QPlainTextEdit
            try:
                from PyQt5.QtWidgets import QTextEdit, QPlainTextEdit
                from PyQt5.QtGui import QTextCursor
                if isinstance(fw, (QTextEdit, QPlainTextEdit)):
                    # Remove the last character if it matches first barcode char
                    t = fw.toPlainText()
                    if t.endswith(ch) and len(t) <= 3:
                        if isinstance(fw, QTextEdit):
                            cur = fw.textCursor()
                            cur.movePosition(QTextCursor.End)
                            cur.deletePreviousChar()
                            fw.setTextCursor(cur)
                        else:
                            # QPlainTextEdit: simpler reset of last char
                            fw.setPlainText(t[:-1])
                            fw.moveCursor(QTextCursor.End)
                    return
            except Exception:
                pass
        except Exception:
            pass

    # Centralized helper to ignore a scan and clean any leaked first character in the current focus widget
    def _ignore_scan(self, barcode: str, reason: str = '') -> None:
        try:
            app = QApplication.instance()
            fw = app.focusWidget() if app else None
            self._cleanup_scanner_leak(fw, barcode)
            if DEBUG_SCANNER_FOCUS:
                try:
                    print('[Scanner][Ignore]', f"reason='{reason}'", 'focus=', self._describe_widget(fw))
                except Exception:
                    pass
        except Exception:
            pass

    # ------- Tiny helpers: overlay + scanner modal block + focus/override -------
    def _show_dim_overlay(self) -> None:
        try:
            if not hasattr(self, '_dimOverlay') or self._dimOverlay is None:
                self._dimOverlay = QWidget(self)
                self._dimOverlay.setObjectName('dimOverlay')
                self._dimOverlay.setStyleSheet('#dimOverlay { background-color: rgba(0, 0, 0, 110); }')
            # Set overlay to block mouse events (modal dimmer)
            self._dimOverlay.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self._dimOverlay.setGeometry(self.rect())
            self._dimOverlay.show()
            self._dimOverlay.raise_()
        except Exception:
            pass

    def _hide_dim_overlay(self) -> None:
        try:
            if hasattr(self, '_dimOverlay') and self._dimOverlay is not None:
                self._dimOverlay.hide()
        except Exception:
            pass

    def _start_scanner_modal_block(self) -> None:
        try:
            self._modalBlockScanner = True
        except Exception:
            pass

    def _end_scanner_modal_block(self) -> None:
        try:
            self._modalBlockScanner = False
        except Exception:
            pass

    def _refocus_sales_table(self) -> None:
        try:
            if getattr(self, 'sales_table', None) is not None:
                self.sales_table.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass

    def _clear_barcode_override(self) -> None:
        try:
            if hasattr(self, '_barcodeOverride'):
                self._barcodeOverride = None
        except Exception:
            pass

    # Block closing via X/Alt+F4 unless allowed by logout
    def closeEvent(self, event):
        try:
            if not getattr(self, '_allow_close', False):
                # Show hint in status bar
                try:
                    sb = getattr(self, 'statusbar', None)
                    if sb is not None:
                        sb.showMessage('Use the Logout button in the menu to exit.', 3000)
                except Exception:
                    pass
                event.ignore()
                return
        except Exception:
            pass
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    load_qss(app)
    window = MainLoader()
    window.show()
    try:
        # Bring window to front in case it opens behind other windows
        window.raise_()
        window.activateWindow()
    except Exception:
        pass
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
