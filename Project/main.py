from modules.ui_utils.overlay_manager import OverlayManager
#!/usr/bin/env python3
"""
POS System - Main UI Loader

This module composes `main_window.ui`, `sales_frame.ui`, and `payment_frame.ui`.
Loads a QSS file from `assets/style.qss` when present.

Barcode scanner logic, event filtering, modal blocking, and override handling are now fully managed by
`modules/devices/barcode_manager.py` (BarcodeManager). All redundant scanner code has been removed from main.py.
Dialogs and panels interact with the scanner only via BarcodeManager's modal block and override helpers.

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
from modules.devices.barcode_manager import BarcodeManager
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
        """Common wrapper for opening menu dialogs with overlay, sizing, and cleanup. Also blocks barcode scanner while dialog is open."""
        self.overlay_manager.toggle_dim_overlay(True)
        # Block scanner for all dialogs except product menu
        from modules.menu.product_menu import open_product_dialog
        is_product_menu = dialog_func is open_product_dialog
        if not is_product_menu:
            try:
                if hasattr(self, 'barcode_manager'):
                    self.barcode_manager._start_scanner_modal_block()
            except Exception:
                pass
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
                    self.overlay_manager.toggle_dim_overlay(False)
                    self.raise_()
                    self.activateWindow()
                    # Unblock scanner modal block
                    try:
                        if hasattr(self, 'barcode_manager'):
                            self.barcode_manager._end_scanner_modal_block()
                    except Exception:
                        pass
                dlg.finished.connect(_cleanup)
                # ...
                dlg.exec_()
                # ...
            else:
                # ...
                self.overlay_manager.toggle_dim_overlay(False)
                # Unblock scanner modal block
                try:
                    if hasattr(self, 'barcode_manager'):
                        self.barcode_manager._end_scanner_modal_block()
                except Exception:
                    pass
        except Exception as e:
            self.overlay_manager.toggle_dim_overlay(False)
            # Unblock scanner modal block
            try:
                if hasattr(self, 'barcode_manager'):
                    self.barcode_manager._end_scanner_modal_block()
            except Exception:
                pass
            print('Dialog failed:', e)

    def _open_sales_dialog(self, dialog_func):
        self.overlay_manager.toggle_dim_overlay(True)
        try:
            if hasattr(self, 'barcode_manager'):
                self.barcode_manager._start_scanner_modal_block()
        except Exception:
            pass
        try:
            dlg = dialog_func(self)
            def _cleanup(_):
                self.overlay_manager.toggle_dim_overlay(False)
                try:
                    self.raise_()
                    self.activateWindow()
                except Exception:
                    pass
                try:
                    if hasattr(self, 'barcode_manager'):
                        self.barcode_manager._end_scanner_modal_block()
                except Exception:
                    pass
            dlg.finished.connect(_cleanup)
            dlg.exec_()
        except Exception as e:
            self.overlay_manager.toggle_dim_overlay(False)
            try:
                if hasattr(self, 'barcode_manager'):
                    self.barcode_manager._end_scanner_modal_block()
            except Exception:
                pass
            print('Dialog failed:', e)

    def __init__(self):
        super().__init__()
        self.overlay_manager = OverlayManager(self)
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

        # Initialize barcode manager
        self.barcode_manager = BarcodeManager(self)
        # Install barcode manager as event filter for scanner key suppression
        try:
            app = QApplication.instance()
            if app is not None:
                self.barcode_manager.install_event_filter(app)
            else:
                self.barcode_manager.install_event_filter(self)
        except Exception:
            pass

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
                            if btn_name == 'vegBtn':
                                btn.clicked.connect(self.open_vegetable_panel)
                            elif btn_name == 'manualBtn':
                                btn.clicked.connect(self.open_manual_panel)

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
                            if btn_name == 'cancelsaleBtn':
                                from modules.sales.cancel_sale import open_cancel_sale_dialog
                                btn.clicked.connect(lambda _, b=btn: self._open_sales_dialog(open_cancel_sale_dialog))                       
                            elif btn_name == 'onholdBtn':
                                from modules.sales.on_hold import open_on_hold_dialog
                                btn.clicked.connect(lambda _, b=btn: self._open_sales_dialog(open_on_hold_dialog))
                            elif btn_name == 'viewholdBtn':
                                from modules.sales.view_hold import open_view_hold_dialog
                                btn.clicked.connect(lambda _, b=btn: self._open_sales_dialog(open_view_hold_dialog))
                                
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

        # BarcodeManager installs its own event filter and handles scanner activity

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
        """Launcher for Add Vegetable panel (delegates to controller)."""
        from modules.sales.vegetable_entry import open_vegetable_panel
        open_vegetable_panel(self)



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
        """Launcher for Manual Product Entry panel (delegates to controller)."""
        from modules.sales.manual_entry import open_manual_entry_panel
        open_manual_entry_panel(self, message=message)

    # ----------------- Barcode scanner handling -----------------
    # Barcode handling is now managed by BarcodeManager

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
    # Scanner activity is now managed by BarcodeManager

    # Event filter for scanner key suppression is now managed by BarcodeManager

    # Best-effort cleanup for a stray first character leaked into disallowed inputs during a scan
    # Scanner leak cleanup is now managed by BarcodeManager

    # Centralized helper to ignore a scan and clean any leaked first character in the current focus widget
    # Ignore scan logic is now managed by BarcodeManager

    # ------- Tiny helpers: overlay + scanner modal block + focus/override -------

    # Scanner modal block is now managed by BarcodeManager

    def _refocus_sales_table(self) -> None:
        try:
            if getattr(self, 'sales_table', None) is not None:
                self.sales_table.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass

    # Barcode override is now managed by BarcodeManager

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
