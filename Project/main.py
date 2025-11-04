#!/usr/bin/env python3
"""
POS System - UI loader that composes `main_window.ui`, `sales_frame.ui`, and `payment_frame.ui`.
Loads a QSS file from `assets/style.qss` when present.
"""

import sys
import os
from PyQt5 import uic
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLineEdit,
    QLabel,
    QDialog,
    QComboBox,
)
from PyQt5.QtCore import Qt, QSize, QTimer, QDateTime, QLocale
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtGui import QFontMetrics, QIcon
from modules.sales.salesTable import setup_sales_table, handle_barcode_scanned
from modules.devices import BarcodeScanner
from config import (
    DATE_FMT,
    DAY_FMT,
    TIME_FMT,
    COMPANY_NAME,
    ICON_ADMIN,
    ICON_REPORTS,
    ICON_VEGETABLE,
    ICON_PRODUCT,
    ICON_GREETING,
    ICON_DEVICE,
    ICON_LOGOUT,
)

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
    def __init__(self):
        super().__init__()
        main_ui = os.path.join(UI_DIR, 'main_window.ui')
        uic.loadUi(main_ui, self)
        # Ensure header layout stretches keep center truly centered
        try:
            info_layout = self.findChild(QHBoxLayout, 'infoSection')
            if info_layout is not None:
                info_layout.setStretch(0, 1)  # left section
                info_layout.setStretch(1, 0)  # center label
                info_layout.setStretch(2, 1)  # right section
                # New combined Day/Time label on the right
                try:
                    day_time_label = self.findChild(QLabel, 'labelDayTime')
                    if day_time_label is not None:
                        # Ensure it hugs the right edge of its section
                        day_time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        day_time_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                    # Ensure labelDate is left-aligned and expands to fill its section
                    date_label = self.findChild(QLabel, 'labelDate')
                    if date_label is not None:
                        date_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        date_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                    # Set company name text (baked-in)
                    company_label = self.findChild(QLabel, 'labelCompany')
                    if company_label is not None:
                        company_label.setText(COMPANY_NAME)
                except Exception:
                    pass
        except Exception:
            pass
        
        # ----------------- Real-time Date / Day / Time Setup -----------------
        try:
            # Optionally force English locale for month/day abbreviations
            # Comment this line if you prefer system locale.
            self._clockLocale = QLocale(QLocale.English)

            # Cache label references
            self._dateLabel: QLabel = self.findChild(QLabel, 'labelDate')
            self._dayTimeLabel: QLabel = self.findChild(QLabel, 'labelDayTime')

            # Start a 1-second timer to update the clock
            self._clockTimer = QTimer(self)
            self._clockTimer.timeout.connect(self._update_clock)
            self._clockTimer.start(1000)
            # Initial paint
            self._update_clock()
        except Exception as e:
            print('Clock setup failed:', e)
        
    # Initialize barcode scanner
        self.scanner = BarcodeScanner()
        self.scanner.barcode_scanned.connect(self.on_barcode_scanned)
        self.scanner.start()
        
        # Store reference to sales table for barcode handling
        self.sales_table = None

        # Ensure horizontal spacing between the window and central content
        # (set here rather than in the .ui to avoid XML type issues)
        layout = getattr(self, 'mainWindowLayout', None)
        if layout is not None:
            try:
                layout.setContentsMargins(12, 6, 12, 6)
            except Exception:
                # Fail silently; margins are not critical
                pass

        # Make titleBar behave: left column takes available space
        titleBar = getattr(self, 'titleBar', None)
        # Prefer titleBar stretch so the left section expands
        if titleBar is not None:
            try:
                titleBar.setStretch(0, 1)
            except Exception:
                pass

        # Set desired stretch factors for workArea (sales, payment, menu)
        work_area = getattr(self, 'workArea', None)
        if work_area is not None:
            try:
                work_area.setStretch(0, 2)  # salesFrame wider
                work_area.setStretch(1, 1)  # paymentFrame medium
                work_area.setStretch(2, 0)  # menuFrame fixed/narrow
            except Exception:
                pass

        # Note: Removed user info panel; no user label to populate.

        # Insert sales_frame.ui into placeholder named 'salesFrame' if present
        sales_placeholder = getattr(self, 'salesFrame', None)
        sales_ui = os.path.join(UI_DIR, 'sales_frame.ui')
        if sales_placeholder is not None and os.path.exists(sales_ui):
            sales_widget = uic.loadUi(sales_ui)
            # Ensure the placeholder has a layout
            layout = sales_placeholder.layout()
            if layout is None:
                layout = QVBoxLayout(sales_placeholder)
                sales_placeholder.setLayout(layout)
            # Keep consistent frame margins so headers align
            try:
                layout.setContentsMargins(8, 8, 8, 8)
            except Exception:
                pass
            # Set proportional vertical space for SalesFrame children and apply em-based heights
            try:
                from PyQt5.QtWidgets import QVBoxLayout as _QVBoxLayout, QWidget as _QWidget, QPushButton as _QPushButton
                main_sales_layout = sales_widget.findChild(_QVBoxLayout, 'mainSalesLayout')
                if main_sales_layout is not None:
                    # Keep inter-item spacing of 10px
                    main_sales_layout.setSpacing(10)
                    # Children order: 0=salesLabel, 1=salesTable, 2=totalContainer, 3=addBtnLayout, 4=receiptLayout
                    # Stretch factors define relative proportions for extra space.
                    # Label stays fixed (0); others share 7:2:2:2 by default.
                    main_sales_layout.setStretch(0, 0)
                    main_sales_layout.setStretch(1, 7)
                    main_sales_layout.setStretch(2, 2)
                    main_sales_layout.setStretch(3, 2)
                    main_sales_layout.setStretch(4, 2)
                # Helper to convert em to px based on current font metrics
                def em_px(widget: QWidget, units: float) -> int:
                    fm = QFontMetrics(widget.font())
                    # Use line spacing for a slightly roomier baseline than raw ascent+descent
                    return int(round(units * fm.lineSpacing()))

                # Ensure the totals container can expand vertically when stretch allocates space
                total_container = sales_widget.findChild(_QWidget, 'totalContainer')
                if total_container is not None:
                    total_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                    h = em_px(total_container, 3.6)  # increased height ~3.6em
                    total_container.setMinimumHeight(h)
                    total_container.setMaximumHeight(h)

                # Add row container: control height in em and let buttons fill
                add_container = sales_widget.findChild(_QWidget, 'addContainer')
                if add_container is not None:
                    add_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                    h = em_px(add_container, 4.0)  # unify with receipt and increase size
                    add_container.setMinimumHeight(h)
                    add_container.setMaximumHeight(h)
                    # Ensure buttons expand vertically to fill container
                    for btn_name in ('vegBtn', 'manualBtn'):
                        btn = sales_widget.findChild(_QPushButton, btn_name)
                        if btn is not None:
                            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

                # Receipt row container: control height in em
                receipt_container = sales_widget.findChild(_QWidget, 'receiptContainer')
                if receipt_container is not None:
                    receipt_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                    h = em_px(receipt_container, 4.0)  # match addContainer height
                    receipt_container.setMinimumHeight(h)
                    receipt_container.setMaximumHeight(h)
                    # Let action buttons fill vertically
                    for btn_name in ('cancelsaleBtn', 'onholdBtn', 'viewholdBtn'):
                        btn = sales_widget.findChild(_QPushButton, btn_name)
                        if btn is not None:
                            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

                # Give the table a reasonable minimum (in em) but let stretch control extra space
                sale_table = sales_widget.findChild(_QWidget, 'salesTable')
                if sale_table is not None:
                    sale_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                    sale_table.setMinimumHeight(em_px(sales_widget, 10))
            except Exception:
                # Non-fatal; layout will fall back to intrinsic sizes
                pass
            layout.addWidget(sales_widget)

            # Configure the Sales table headers
            try:
                sale_table = sales_widget.findChild(QTableWidget, 'salesTable')
                if sale_table:
                    setup_sales_table(sale_table)
                    # Store reference for barcode handling
                    self.sales_table = sale_table
            except Exception as e:
                print('Sales table setup failed:', e)

            # Wire up the "Vegetable Entry" button to open the vegetable panel
            try:
                veg_btn = sales_widget.findChild(QPushButton, 'vegBtn')
                if veg_btn is not None:
                    veg_btn.clicked.connect(self.open_vegetable_panel)
            except Exception as e:
                print('Failed to wire vegBtn:', e)

            # Wire up the "Manual Entry" button to open the manual entry panel
            try:
                manual_btn = sales_widget.findChild(QPushButton, 'manualBtn')
                if manual_btn is not None:
                    manual_btn.clicked.connect(lambda: self.open_manual_panel("You Clicked Add Manual Button"))
            except Exception as e:
                print('Failed to wire manualBtn:', e)

        # Insert payment_frame.ui into placeholder named 'paymentFrame' if present
        payment_placeholder = getattr(self, 'paymentFrame', None)
        payment_ui = os.path.join(UI_DIR, 'payment_frame.ui')
        if payment_placeholder is not None and os.path.exists(payment_ui):
            payment_widget = uic.loadUi(payment_ui)
            layout = payment_placeholder.layout()
            if layout is None:
                layout = QVBoxLayout(payment_placeholder)
                payment_placeholder.setLayout(layout)
            try:
                layout.setContentsMargins(8, 8, 8, 8)
            except Exception:
                pass
            layout.addWidget(payment_widget)

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
        try:
            def set_btn_icon_path(btn: QPushButton, rel_path: str, size: int = 32) -> bool:
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
                'adminBtn': ('Admin', (
                    "Permission: Admin\n"
                    "- login\n- password\n- profile picture\n- Cashier role: Admin vs Staff"
                )),
                'reportsBtn': ('Reports', (
                    "Permission: Admin\n"
                    "- Sales report\n- report 2\n- report 3"
                )),
                'vegetableBtn': ('Vegetable', (
                    "Permission: Admin\n"
                    "- Rename Vegetable button\n"
                    "  States: name or Unused (Unused = gray, disabled)"
                )),
                'productBtn': ('Product', (
                    "Permission: Admin\n"
                    "- ADD, REMOVE, UPDATE product"
                )),
                'greetingBtn': ('Greeting', (
                    "Permission: Admin\n"
                    "- Custom vs default\n"
                    "  custom: Happy Christmas, Happy New Year\n"
                    "  default: Thank you."
                )),
                'deviceBtn': ('Device', (
                    "Permission: Admin\n"
                    "- Barcode baud rate\n- Weighing scale"
                )),
                'logoutBtn': ('Logout', (
                    "Permission: Admin\n- Confirm logout?"
                )),
            }

            # Map buttons to config-defined icons
            button_icons = {
                'adminBtn': ICON_ADMIN,
                'reportsBtn': ICON_REPORTS,
                'vegetableBtn': ICON_VEGETABLE,
                'productBtn': ICON_PRODUCT,
                'greetingBtn': ICON_GREETING,
                'deviceBtn': ICON_DEVICE,
                'logoutBtn': ICON_LOGOUT,
            }

            for obj_name, (title, msg) in menu_buttons.items():
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
                # Wire click handlers: Product opens product panel; others show info dialog
                if obj_name == 'productBtn':
                    btn.clicked.connect(self.open_product_panel)
                else:
                    btn.clicked.connect(lambda _, t=title, m=msg: self.open_menu_dialog(t, m))
        except Exception as e:
            print('Failed to wire menu buttons:', e)

    # ----------------- Vegetable panel wiring -----------------
    def open_vegetable_panel(self):
        """Open the Add Vegetable panel as a modal dialog:
        - Size = 60% of main window, centered
        - Dim the main window background while open
        - Only Close (X) button shown (no minimize/maximize)
        - Close on X, OK, or CANCEL; restore brightness on close
        """
        veg_ui = os.path.join(UI_DIR, 'vegetable.ui')
        if not os.path.exists(veg_ui):
            print('vegetable.ui not found at', veg_ui)
            return

        # Create dimming overlay over the main window
        try:
            if not hasattr(self, '_dimOverlay') or self._dimOverlay is None:
                self._dimOverlay = QWidget(self)
                self._dimOverlay.setObjectName('dimOverlay')
                self._dimOverlay.setStyleSheet('#dimOverlay { background-color: rgba(0, 0, 0, 110); }')
                self._dimOverlay.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self._dimOverlay.setGeometry(self.rect())
            self._dimOverlay.show()
            self._dimOverlay.raise_()
        except Exception:
            pass

        # Build a modal dialog and embed the loaded UI inside
        try:
            content = uic.loadUi(veg_ui)
        except Exception as e:
            print('Failed to load vegetable.ui:', e)
            try:
                self._dimOverlay.hide()
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

        # Wire keypad buttons to update message label and close on OK/CANCEL
        try:
            msg: QLabel = content.findChild(QLabel, 'messageLabel')
            for name in (
                'btnVegTomato','btnVegPotato','btnVegOnion','btnVegCarrot',
                'btnVegCabbage','btnVegSpinach','btnVegCucumber','btnVegPumpkin',
                'btnVegCapsicum','btnVegBeetroot','btnVegRadish','btnVegPeas',
                'btnVegOkra','btnVegCauliflower',
            ):
                btn = content.findChild(QPushButton, name)
                if btn is not None and msg is not None:
                    btn.clicked.connect(lambda _, b=btn: msg.setText(f"Selected: {b.text()}"))

            ok_btn = content.findChild(QPushButton, 'btnOK')
            cancel_btn = content.findChild(QPushButton, 'btnCancel')
            if ok_btn is not None:
                ok_btn.clicked.connect(lambda: dlg.accept())
            if cancel_btn is not None:
                cancel_btn.clicked.connect(lambda: dlg.reject())
        except Exception as e:
            print('Vegetable keypad wiring failed:', e)

        # Ensure overlay hides and focus returns when dialog closes
        def _cleanup_overlay(_code):
            try:
                if hasattr(self, '_dimOverlay') and self._dimOverlay is not None:
                    self._dimOverlay.hide()
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
                if hasattr(self, '_barcodeOverride'):
                    self._barcodeOverride = None
            except Exception:
                pass

        dlg.finished.connect(_cleanup_overlay)

        # Execute modally
        dlg.exec_()

    def open_product_panel(self, initial_mode: str = None, initial_code: str = None):
        """Open the Product Management dialog from ui/product.ui as a modal dialog.
        - Size = 60% of main window, centered
        - Dim the main window background while open
        - Only Close (X) button shown (no minimize/maximize)
        - Wire basic actions for Add/Remove/Update and OK/Cancel
        """
        product_ui = os.path.join(UI_DIR, 'product.ui')
        if not os.path.exists(product_ui):
            print('product.ui not found at', product_ui)
            return

        # Create dimming overlay over the main window (reuse same overlay)
        try:
            if not hasattr(self, '_dimOverlay') or self._dimOverlay is None:
                self._dimOverlay = QWidget(self)
                self._dimOverlay.setObjectName('dimOverlay')
                self._dimOverlay.setStyleSheet('#dimOverlay { background-color: rgba(0, 0, 0, 110); }')
                self._dimOverlay.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self._dimOverlay.setGeometry(self.rect())
            self._dimOverlay.show()
            self._dimOverlay.raise_()
        except Exception:
            pass

        # Load UI content
        try:
            content = uic.loadUi(product_ui)
        except Exception as e:
            print('Failed to load product.ui:', e)
            try:
                self._dimOverlay.hide()
            except Exception:
                pass
            return

        # Build modal dialog container
        dlg = QDialog(self)
        dlg.setModal(True)
        dlg.setWindowTitle('Product Management')
        dlg.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        try:
            mw = self.frameGeometry().width()
            mh = self.frameGeometry().height()
            dw = max(400, int(mw * 0.6))
            dh = max(300, int(mh * 0.6))
            dlg.setFixedSize(dw, dh)
            mx = self.frameGeometry().x()
            my = self.frameGeometry().y()
            dlg.move(mx + (mw - dw) // 2, my + (mh - dh) // 2)
        except Exception:
            pass

        # Install content into dialog
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(content)

        # Setup Product dialog behavior (modes, lookup, validation, status)
        try:
            # Controls
            sub_hdr: QLabel = content.findChild(QLabel, 'subHeaderLabel')
            btn_add: QPushButton = content.findChild(QPushButton, 'addButton')
            btn_remove: QPushButton = content.findChild(QPushButton, 'removeButton')
            btn_update: QPushButton = content.findChild(QPushButton, 'updateButton')
            ok_btn: QPushButton = content.findChild(QPushButton, 'okButton')
            cancel_btn: QPushButton = content.findChild(QPushButton, 'cancelButton')

            code_label: QLabel = content.findChild(QLabel, 'productCodeLabel')
            name_label: QLabel = content.findChild(QLabel, 'productNameLabel')
            category_label: QLabel = content.findChild(QLabel, 'categoryLabel')
            sell_label: QLabel = content.findChild(QLabel, 'sellingPriceLabel')
            cost_label: QLabel = content.findChild(QLabel, 'costPriceLabel')
            unit_label: QLabel = content.findChild(QLabel, 'unitLabel')
            supplier_label: QLabel = content.findChild(QLabel, 'supplierLabel')
            last_updated_label: QLabel = content.findChild(QLabel, 'lastUpdatedLabel')

            code_edit: QLineEdit = content.findChild(QLineEdit, 'productCodeLineEdit')
            name_edit: QLineEdit = content.findChild(QLineEdit, 'productNameLineEdit')
            category_combo: QComboBox = content.findChild(QComboBox, 'categoryComboBox')
            cost_edit: QLineEdit = content.findChild(QLineEdit, 'costPriceLineEdit')
            sell_edit: QLineEdit = content.findChild(QLineEdit, 'sellingPriceLineEdit')
            unit_combo: QComboBox = content.findChild(QComboBox, 'unitComboBox')
            supplier_edit: QLineEdit = content.findChild(QLineEdit, 'supplierLineEdit')
            last_updated_edit: QLineEdit = content.findChild(QLineEdit, 'lastUpdatedLineEdit')
            status_lbl: QLabel = content.findChild(QLabel, 'statusLabel')

            current_mode = {'mode': 'none'}
            mode_locked = {'locked': False}

            def set_mode_buttons_enabled(enabled: bool):
                try:
                    if btn_add is not None:
                        btn_add.setEnabled(enabled)
                    if btn_remove is not None:
                        btn_remove.setEnabled(enabled)
                    if btn_update is not None:
                        btn_update.setEnabled(enabled)
                except Exception as _e:
                    pass

            def focus_next_widget():
                try:
                    # Move focus forward in the tab order (acts like pressing Tab)
                    dlg.focusNextPrevChild(True)
                except Exception as _e:
                    pass

            def set_ok_button_enabled(enabled: bool):
                try:
                    if ok_btn is not None:
                        ok_btn.setEnabled(enabled)
                except Exception as _e:
                    print('set_ok_button_enabled failed:', _e)

            def set_code_error_style(error: bool):
                try:
                    if code_edit is None:
                        return
                    if error:
                        code_edit.setStyleSheet(code_edit.styleSheet() + "; border: 1px solid #b00020;")
                    else:
                        # Reset border by clearing inline style; relies on global QSS
                        code_edit.setStyleSheet("")
                except Exception as _e:
                    print('set_code_error_style failed:', _e)

            def set_status(text: str, ok: bool):
                if status_lbl is None:
                    return
                status_lbl.setText(text)
                try:
                    status_lbl.setStyleSheet('color: %s; font-weight: 600;' % ('#0a8f08' if ok else '#b00020'))
                except Exception:
                    pass

            def set_fields_enabled(enabled: bool):
                try:
                    if name_edit is not None:
                        name_edit.setEnabled(enabled)
                    if category_combo is not None:
                        category_combo.setEnabled(enabled)
                    if cost_edit is not None:
                        cost_edit.setEnabled(enabled)
                    if sell_edit is not None:
                        sell_edit.setEnabled(enabled)
                    if unit_combo is not None:
                        unit_combo.setEnabled(enabled)
                    if supplier_edit is not None:
                        supplier_edit.setEnabled(enabled)
                    # last updated is always inactive (read-only & disabled)
                    if last_updated_edit is not None:
                        last_updated_edit.setEnabled(False)
                        try:
                            last_updated_edit.setReadOnly(True)
                        except Exception:
                            pass
                except Exception as _e:
                    pass

            def set_form_visible(visible: bool):
                try:
                    # Subheader
                    if sub_hdr is not None:
                        sub_hdr.setVisible(visible)
                    # Labels
                    for lbl in (code_label, name_label, category_label, sell_label, cost_label, unit_label, supplier_label, last_updated_label):
                        if lbl is not None:
                            lbl.setVisible(visible)
                    # Inputs
                    for w in (code_edit, name_edit, category_combo, cost_edit, sell_edit, unit_combo, supplier_edit, last_updated_edit):
                        if w is not None:
                            w.setVisible(visible)
                    # Status and action buttons
                    if status_lbl is not None:
                        status_lbl.setVisible(visible)
                    if ok_btn is not None:
                        ok_btn.setVisible(visible)
                    if cancel_btn is not None:
                        cancel_btn.setVisible(visible)
                except Exception:
                    pass

            def clear_fields(except_code: bool = True):
                try:
                    if not except_code and code_edit is not None:
                        code_edit.clear()
                    if name_edit is not None:
                        name_edit.clear()
                    if sell_edit is not None:
                        sell_edit.clear()
                    if cost_edit is not None:
                        cost_edit.clear()
                    if supplier_edit is not None:
                        supplier_edit.clear()
                    if last_updated_edit is not None:
                        last_updated_edit.clear()
                    if category_combo is not None and category_combo.count() > 0:
                        category_combo.setCurrentIndex(0)
                    if unit_combo is not None and unit_combo.count() > 0:
                        unit_combo.setCurrentIndex(0)
                except Exception as _e:
                    pass

            def apply_mode(mode: str):
                if mode == 'add':
                    if sub_hdr is not None:
                        sub_hdr.setText('Add New Product')
                    if code_label is not None:
                        code_label.setText('Product Code*')
                    if name_label is not None:
                        name_label.setText('Product Name*')
                    if category_label is not None:
                        category_label.setText('Category*')
                    if sell_label is not None:
                        sell_label.setText('Selling Price*')
                    if code_edit is not None:
                        code_edit.setPlaceholderText('')
                    if ok_btn is not None:
                        ok_btn.setText('ADD')
                elif mode == 'remove':
                    if sub_hdr is not None:
                        sub_hdr.setText('Remove Product')
                    if code_label is not None:
                        code_label.setText('Product Code')
                    if name_label is not None:
                        name_label.setText('Product Name')
                    if category_label is not None:
                        category_label.setText('Category')
                    if sell_label is not None:
                        sell_label.setText('Selling Price')
                    if code_edit is not None:
                        code_edit.setPlaceholderText('Provide Product Code')
                    if ok_btn is not None:
                        ok_btn.setText('DELETE')
                elif mode == 'update':
                    if sub_hdr is not None:
                        sub_hdr.setText('Update / View Product')
                    if code_label is not None:
                        code_label.setText('Product Code')
                    if name_label is not None:
                        name_label.setText('Product Name')
                    if category_label is not None:
                        category_label.setText('Category')
                    if sell_label is not None:
                        sell_label.setText('Selling Price')
                    if code_edit is not None:
                        code_edit.setPlaceholderText('Provide Product Code')
                    if ok_btn is not None:
                        ok_btn.setText('UPDATE')

            def enter_mode(mode: str):
                current_mode['mode'] = mode
                set_status('', True)
                apply_mode(mode)
                # Ensure form becomes visible when a mode is chosen
                set_form_visible(True)
                if mode == 'add':
                    set_fields_enabled(True)
                    set_ok_button_enabled(True)
                    set_code_error_style(False)
                else:
                    # remove/update start with only code enabled
                    clear_fields(except_code=True)
                    set_fields_enabled(False)

            def on_mode_button_clicked(mode: str):
                # Lock mode selection on first explicit choice; user must OK or Cancel to change
                if not mode_locked['locked']:
                    mode_locked['locked'] = True
                    set_mode_buttons_enabled(False)
                enter_mode(mode)
                # Always focus Product Code field on entering any mode
                if code_edit is not None:
                    code_edit.setFocus()

            def on_code_changed(text: str):
                mode = current_mode['mode']
                t = (text or '').strip()
                if mode == 'add':
                    # Immediate duplicate check while adding
                    if not t:
                        set_status('', True)
                        set_code_error_style(False)
                        set_ok_button_enabled(True)
                        return
                    # Check cache first, then DB as fallback
                    try:
                        from modules.db_operation import get_product_info, get_product_full
                        c_found, _, _ = get_product_info(t)
                    except Exception as _e:
                        c_found = False
                    if c_found:
                        set_status('Error: Product code already exists.', False)
                        set_code_error_style(True)
                        set_ok_button_enabled(False)
                        return
                    try:
                        d_found, _pdata = get_product_full(t)
                    except Exception:
                        d_found = False
                    if d_found:
                        set_status('Error: Product code already exists.', False)
                        set_code_error_style(True)
                        set_ok_button_enabled(False)
                        return
                    # Available
                    set_status('', True)
                    set_code_error_style(False)
                    set_ok_button_enabled(True)
                    return
                if mode not in ('remove', 'update'):
                    return
                if not t:
                    clear_fields(except_code=True)
                    set_fields_enabled(False)
                    set_status('', True)
                    return
                try:
                    from modules.db_operation import get_product_full
                except Exception as _e:
                    return
                    return
                found, pdata = get_product_full(t)
                if not found or not pdata:
                    # Fallback to in-memory cache for newly added items in this session
                    try:
                        from modules.db_operation import get_product_info
                        c_found, c_name, c_price = get_product_info(t)
                    except Exception as _e:
                        c_found, c_name, c_price = False, '', 0.0
                    if not c_found:
                        clear_fields(except_code=True)
                        set_fields_enabled(False)
                        set_status('Product not found.', False)
                        return
                    pdata = {
                        'name': c_name,
                        'price': c_price,
                        'category': '',
                        'supplier': '',
                        'cost_price': None,
                        'unit': '',
                        'last_updated': '',
                    }
                # Populate known fields
                try:
                    if name_edit is not None:
                        name_edit.setText(str(pdata.get('name', '')))
                    if sell_edit is not None:
                        sell_edit.setText(f"{float(pdata.get('price', 0.0)):.2f}")
                    if cost_edit is not None:
                        cp = pdata.get('cost_price', None)
                        cost_edit.setText('' if cp in (None, '') else str(cp))
                    if supplier_edit is not None:
                        supplier_edit.setText(str(pdata.get('supplier', '')))
                    if last_updated_edit is not None:
                        last_updated_edit.setText(str(pdata.get('last_updated', '')))
                    # Category combo match
                    if category_combo is not None:
                        val = str(pdata.get('category', '')).strip().lower()
                        matched = False
                        for i in range(category_combo.count()):
                            if category_combo.itemText(i).strip().lower() == val:
                                category_combo.setCurrentIndex(i)
                                matched = True
                                break
                        if not matched and category_combo.count() > 0:
                            category_combo.setCurrentIndex(0)
                    # Unit combo match with simple normalization
                    if unit_combo is not None:
                        val = str(pdata.get('unit', '')).strip().lower()
                        norm = 'pieces' if val in ('piece', 'pieces', 'pcs', 'pc') else ('grams' if val in ('g', 'gram', 'grams') else val)
                        matched = False
                        for i in range(unit_combo.count()):
                            if unit_combo.itemText(i).strip().lower() == norm:
                                unit_combo.setCurrentIndex(i)
                                matched = True
                                break
                        if not matched and unit_combo.count() > 0:
                            unit_combo.setCurrentIndex(0)
                except Exception as _e:
                    pass
                # Enable edits only for UPDATE
                set_fields_enabled(mode == 'update')
                set_status('Product found.', True)

            def on_ok_clicked():
                mode = current_mode['mode']
                if mode == 'add':
                    missing = []
                    if code_edit is not None and not code_edit.text().strip():
                        missing.append('Product Code')
                    if name_edit is not None and not name_edit.text().strip():
                        missing.append('Product Name')
                    if sell_edit is not None and not sell_edit.text().strip():
                        missing.append('Selling Price')
                    if missing:
                        set_status('Error: Please provide ' + ', '.join(missing), False)
                        return
                    # Persist to DB (full fields)
                    try:
                        from modules.db_operation import add_product
                        # Build parameters
                        code = code_edit.text().strip()
                        name_val = name_edit.text().strip() if name_edit is not None else ''
                        price = float(sell_edit.text()) if sell_edit is not None else 0.0
                        cat = category_combo.currentText().strip() if category_combo is not None else None
                        supplier = supplier_edit.text().strip() if supplier_edit is not None else None
                        cost_val = float(cost_edit.text()) if (cost_edit is not None and cost_edit.text().strip()) else None
                        unit_val = unit_combo.currentText().strip() if unit_combo is not None else None
                        now_str = QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss')
                        ok, msg = add_product(code, name_val, price, cat, supplier, cost_val, unit_val, now_str)
                        price = float(sell_edit.text()) if sell_edit is not None else 0.0
                        if not ok:
                            set_status(f"Error: {msg}", False)
                            return
                    except Exception as _e:
                        set_status(f"Error: {_e}", False)
                        return
                    # Set last updated and success
                    try:
                        if last_updated_edit is not None:
                            last_updated_edit.setText(now_str)
                    except Exception:
                        pass
                    # Refresh in-memory cache to ensure immediate availability for scanner
                    try:
                        from modules.db_operation import refresh_product_cache
                        refresh_product_cache()
                    except Exception:
                        pass
                    set_status('Added successfully.', True)
                    # If this dialog was opened due to a scan (initial_code provided),
                    # add the product to the sales table immediately as if scanned.
                    try:
                        code_to_add = str(initial_code).strip() if initial_code else (
                            code_edit.text().strip() if code_edit is not None else ''
                        )
                        if code_to_add and getattr(self, 'sales_table', None) is not None:
                            status_bar = getattr(self, 'statusbar', None)
                            # Schedule on next tick so UI remains responsive
                            QTimer.singleShot(0, lambda c=code_to_add, sb=status_bar: handle_barcode_scanned(self.sales_table, c, sb))
                    except Exception:
                        pass
                    QTimer.singleShot(1000, dlg.accept)
                elif mode == 'remove':
                    if code_edit is None or not code_edit.text().strip():
                        set_status('Error: Provide Product Code to delete.', False)
                        return
                    # Delete from DB
                    try:
                        from modules.db_operation import delete_product
                        ok, msg = delete_product(code_edit.text().strip())
                        if not ok:
                            set_status(f"Error: {msg}", False)
                            return
                    except Exception as _e:
                        set_status(f"Error: {_e}", False)
                        return
                    # Refresh in-memory cache to ensure immediate consistency
                    try:
                        from modules.db_operation import refresh_product_cache
                        refresh_product_cache()
                    except Exception:
                        pass
                    set_status('Deleted successfully.', True)
                    QTimer.singleShot(1000, dlg.accept)
                elif mode == 'update':
                    if code_edit is None or not code_edit.text().strip():
                        set_status('Error: Provide Product Code to update.', False)
                        return
                    # Update DB (full fields except last_updated which is auto)
                    try:
                        from modules.db_operation import update_product
                        price_val = float(sell_edit.text()) if (sell_edit is not None and sell_edit.text().strip()) else None
                        name_val = name_edit.text().strip() if (name_edit is not None and name_edit.text().strip()) else None
                        cat = category_combo.currentText().strip() if category_combo is not None else None
                        supplier = supplier_edit.text().strip() if (supplier_edit is not None and supplier_edit.text().strip()) else None
                        cost_val = float(cost_edit.text()) if (cost_edit is not None and cost_edit.text().strip()) else None
                        unit_val = unit_combo.currentText().strip() if unit_combo is not None else None
                        ok, msg = update_product(code_edit.text().strip(), name_val, price_val, cat, supplier, cost_val, unit_val)
                        if not ok:
                            set_status(f"Error: {msg}", False)
                            return
                    except Exception as _e:
                        set_status(f"Error: {_e}", False)
                        return
                    try:
                        if last_updated_edit is not None:
                            last_updated_edit.setText(QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss'))
                    except Exception:
                        pass
                    # Refresh in-memory cache to ensure immediate consistency
                    try:
                        from modules.db_operation import refresh_product_cache
                        refresh_product_cache()
                    except Exception:
                        pass
                    set_status('Updated successfully.', True)
                    QTimer.singleShot(1000, dlg.accept)

            def on_code_return_pressed():
                """Enter on Product Code should behave like Tab: perform lookup, lock modes, then focus next widget (not click)."""
                try:
                    mode = current_mode['mode']
                    if mode in ('remove', 'update'):
                        # Ensure fields are populated for the current code
                        if code_edit is not None:
                            on_code_changed(code_edit.text())
                        # Lock modes if not already locked
                        if not mode_locked['locked']:
                            mode_locked['locked'] = True
                            set_mode_buttons_enabled(False)
                        # Move focus forward (like Tab) on the next event loop tick to avoid
                        # the same Enter key event activating the newly-focused button.
                        QTimer.singleShot(0, focus_next_widget)
                    else:
                        # In ADD mode, also move focus forward for consistency.
                        QTimer.singleShot(0, focus_next_widget)
                except Exception:
                    pass

            # Wire buttons and signals
            if btn_add is not None:
                btn_add.clicked.connect(lambda: on_mode_button_clicked('add'))
            if btn_remove is not None:
                btn_remove.clicked.connect(lambda: on_mode_button_clicked('remove'))
            if btn_update is not None:
                btn_update.clicked.connect(lambda: on_mode_button_clicked('update'))
            if ok_btn is not None:
                try:
                    ok_btn.clicked.disconnect()
                except Exception:
                    pass
                ok_btn.clicked.connect(on_ok_clicked)
                try:
                    # Ensure OK is not default until explicitly focused
                    ok_btn.setAutoDefault(True)
                    ok_btn.setDefault(False)
                except Exception:
                    pass
            if cancel_btn is not None:
                try:
                    cancel_btn.clicked.disconnect()
                except Exception:
                    pass
                def _on_cancel():
                    # Not strictly necessary since dialog closes, but restore in case of reuse
                    set_mode_buttons_enabled(True)
                    try:
                        if ok_btn is not None:
                            ok_btn.setDefault(False)
                    except Exception:
                        pass
                    dlg.reject()
                cancel_btn.clicked.connect(_on_cancel)
            if code_edit is not None:
                try:
                    code_edit.textChanged.disconnect()
                except Exception:
                    pass
                code_edit.textChanged.connect(on_code_changed)
                try:
                    code_edit.returnPressed.disconnect()
                except Exception:
                    pass
                code_edit.returnPressed.connect(on_code_return_pressed)
            # Make Enter behave like Tab on other line edits as well
            def _wire_lineedit_return_as_tab(le: QLineEdit):
                if le is None:
                    return
                try:
                    le.returnPressed.disconnect()
                except Exception:
                    pass
                le.returnPressed.connect(focus_next_widget)
            _wire_lineedit_return_as_tab(name_edit)
            _wire_lineedit_return_as_tab(cost_edit)
            _wire_lineedit_return_as_tab(sell_edit)
            _wire_lineedit_return_as_tab(supplier_edit)

            # Start hidden until a mode is selected
            set_form_visible(False)
            set_fields_enabled(False)

            # If caller requested a starting mode/code (e.g., from scanner when not found)
            try:
                if isinstance(initial_mode, str) and initial_mode.lower() in ('add', 'remove', 'update'):
                    on_mode_button_clicked(initial_mode.lower())
                    if initial_code and code_edit is not None:
                        code_edit.setText(str(initial_code))
                        code_edit.setFocus()
                        # For remove/update, trigger lookup population
                        if current_mode['mode'] in ('remove', 'update'):
                            on_code_changed(str(initial_code))
            except Exception:
                pass
        except Exception as e:
            print('Product dialog setup failed:', e)

        # Cleanup overlay on close and restore focus
        def _cleanup_overlay(_code):
            try:
                if hasattr(self, '_dimOverlay') and self._dimOverlay is not None:
                    self._dimOverlay.hide()
            except Exception:
                pass
            try:
                self.raise_()
                self.activateWindow()
            except Exception:
                pass

        dlg.finished.connect(_cleanup_overlay)
        # While this dialog is open, route scanner input into Product Code and suppress Manual Entry
        try:
            def _barcode_to_product_code(code: str) -> bool:
                try:
                    if not code:
                        return False
                    if code_edit is not None:
                        code_edit.setText(code)
                        code_edit.setFocus()
                    # For remove/update, trigger lookup to populate fields
                    try:
                        if current_mode['mode'] in ('remove', 'update'):
                            on_code_changed(code)
                    except Exception:
                        pass
                    return True
                except Exception:
                    return False
            self._barcodeOverride = _barcode_to_product_code
        except Exception:
            pass

        dlg.exec_()

    def open_menu_dialog(self, title: str, message: str):
        """Open a generic modal dialog for menu actions with a temporary message."""
        # Create dimming overlay over the main window (reuse same overlay)
        try:
            if not hasattr(self, '_dimOverlay') or self._dimOverlay is None:
                self._dimOverlay = QWidget(self)
                self._dimOverlay.setObjectName('dimOverlay')
                self._dimOverlay.setStyleSheet('#dimOverlay { background-color: rgba(0, 0, 0, 110); }')
                self._dimOverlay.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self._dimOverlay.setGeometry(self.rect())
            self._dimOverlay.show()
            self._dimOverlay.raise_()
        except Exception:
            pass

        dlg = QDialog(self)
        dlg.setModal(True)
        dlg.setWindowTitle(title)
        dlg.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        try:
            mw = self.frameGeometry().width()
            mh = self.frameGeometry().height()
            dw = max(360, int(mw * 0.45))
            dh = max(220, int(mh * 0.4))
            dlg.setFixedSize(dw, dh)
            mx = self.frameGeometry().x()
            my = self.frameGeometry().y()
            dlg.move(mx + (mw - dw) // 2, my + (mh - dh) // 2)
        except Exception:
            pass

        v = QVBoxLayout(dlg)
        v.setContentsMargins(16, 16, 16, 16)
        info = QLabel(message)
        info.setWordWrap(True)
        v.addWidget(info)
        ok = QPushButton('OK')
        ok.clicked.connect(dlg.accept)
        v.addWidget(ok, alignment=Qt.AlignRight)

        def _cleanup(_code):
            try:
                if hasattr(self, '_dimOverlay') and self._dimOverlay is not None:
                    self._dimOverlay.hide()
            except Exception:
                pass

        dlg.finished.connect(_cleanup)
        dlg.exec_()

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
        manual_ui = os.path.join(UI_DIR, 'manual.ui')
        if not os.path.exists(manual_ui):
            print('manual.ui not found at', manual_ui)
            return

        # Create dimming overlay over the main window (reuse same overlay as vegetable panel)
        try:
            if not hasattr(self, '_dimOverlay') or self._dimOverlay is None:
                self._dimOverlay = QWidget(self)
                self._dimOverlay.setObjectName('dimOverlay')
                self._dimOverlay.setStyleSheet('#dimOverlay { background-color: rgba(0, 0, 0, 110); }')
                self._dimOverlay.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self._dimOverlay.setGeometry(self.rect())
            self._dimOverlay.show()
            self._dimOverlay.raise_()
        except Exception:
            pass

        # Build a modal dialog and embed the loaded UI inside
        try:
            content = uic.loadUi(manual_ui)
        except Exception as e:
            print('Failed to load manual.ui:', e)
            try:
                self._dimOverlay.hide()
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
        except Exception as e:
            print('Failed to set manual text:', e)

        # Ensure overlay hides and focus returns when dialog closes
        def _cleanup_overlay(_code):
            try:
                if hasattr(self, '_dimOverlay') and self._dimOverlay is not None:
                    self._dimOverlay.hide()
            except Exception:
                pass
            # Bring main window back to front
            try:
                self.raise_()
                self.activateWindow()
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
        # Normalize input once
        barcode = (barcode or '').strip()

        # If a modal has installed a barcode override, let it handle and short-circuit
        try:
            override = getattr(self, '_barcodeOverride', None)
            if callable(override):
                handled = False
                try:
                    handled = override(barcode)
                except Exception:
                    handled = False
                if handled:
                    return
        except Exception:
            pass
        
        # Get status bar reference
        status_bar = getattr(self, 'statusbar', None)
        
        # Import here to avoid circular dependency
        from modules.db_operation import get_product_info
        
        # Check if product exists in database
        found, product_name, unit_price = get_product_info(barcode)
        
        if not found:
            # Product not found - open Product Management in ADD mode with code prefilled
            if status_bar:
                status_bar.showMessage(f"⚠ Product '{barcode}' not found - Opening Product Management (ADD)", 3000)
            self.open_product_panel(initial_mode='add', initial_code=barcode)
            return
        
        # Product found - add to sales table
        if self.sales_table is not None:
            handle_barcode_scanned(self.sales_table, barcode, status_bar)
        else:
            # Fallback: just display in status bar
            if status_bar:
                status_bar.showMessage(f"📷 Scanned: {barcode}", 3000)

    # ----------------- Clock update handler -----------------
    def _update_clock(self):
        try:
            now = QDateTime.currentDateTime()

            # Date text (e.g., 3 Nov 2025)
            if self._dateLabel is not None:
                # Use locale formatting for month/day names
                date_text = self._clockLocale.toString(now.date(), DATE_FMT)
                self._dateLabel.setText(date_text)

            # Day + Time (e.g., FRI 12:22 am)
            if self._dayTimeLabel is not None:
                day_text = self._clockLocale.toString(now.date(), DAY_FMT)
                time_text = now.toString(TIME_FMT).upper()  # am/pm lower via 'ap'
                self._dayTimeLabel.setText(f"{day_text}   {time_text}")
        except Exception as e:
            # Non-fatal; avoid crashing timer
            print('Clock update failed:', e)


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
