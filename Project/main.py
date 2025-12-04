#!/usr/bin/env python3
"""POS System main window loader. See Documentation/main_py_overview.md for details."""
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import sys
import os
import time
from modules.ui_utils.overlay_manager import OverlayManager
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
from PyQt5.QtCore import Qt, QSize, QEvent, QTimer
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtGui import QFontMetrics, QIcon

from modules.sales.salesTable import setup_sales_table, handle_barcode_scanned, bind_total_label
from modules.sales.sales_frame_setup import setup_sales_frame
from modules.devices.barcode_manager import BarcodeManager
# --- Menu frame dialog controllers ---
from modules.menu.logout_menu import open_logout_dialog as launch_logout_dialog
from modules.menu.admin_menu import open_admin_dialog as launch_admin_dialog
from modules.menu.devices_menu import open_devices_dialog as launch_devices_dialog
from modules.menu.reports_menu import open_reports_dialog as launch_reports_dialog
from modules.menu.greeting_menu import open_greeting_dialog as launch_greeting_dialog
from modules.menu.product_menu import open_product_dialog as launch_product_dialog
from modules.menu.vegetable_menu import VegetableMenuDialog
# --- Sales frame dialog controllers ---
from modules.sales.vegetable_entry import open_vegetable_entry_dialog as launch_vegetable_entry_dialog
from modules.sales.manual_entry import open_manual_entry_dialog as launch_manual_entry_dialog
from modules.sales.on_hold import open_on_hold_dialog as launch_onhold_dialog
from modules.sales.view_hold import open_view_hold_dialog as launch_viewhold_dialog
from modules.sales.cancel_sale import open_cancel_sale_dialog as launch_cancelsale_dialog

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
# from modules.debug.debug_utils import describe_widget, debug_print_focus  # Uncomment for focus debugging

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
    # Menu dialog launchers (use common wrapper)
    def open_logout_menu_dialog(self):
        """Open Logout dialog."""
        self.open_dialog_wrapper(launch_logout_dialog)

    def open_product_menu_dialog(self, **kwargs):
        """Open Product Management panel."""
        self.open_product_menu_dialog(launch_product_dialog)
        
    def open_admin_menu_dialog(self):
        """Open Admin dialog."""
        self.open_dialog_wrapper(launch_admin_dialog, current_user='Admin', is_admin=True)

    def open_greeting_menu_dialog(self):
        """Open Greeting dialog."""
        self.open_dialog_wrapper(launch_greeting_dialog)

    def open_devices_menu_dialog(self):
        """Open Devices dialog."""
        self.open_dialog_wrapper(launch_devices_dialog)

    def open_reports_menu_dialog(self):
        """Open Reports dialog."""
        self.open_dialog_wrapper(launch_reports_dialog)

    def open_vegetable_menu_dialog(self):
        """Open Vegetable Label Edit dialog."""
        self.open_dialog_wrapper(VegetableMenuDialog)

    # Sales frame dialog launchers (use common wrapper)
    def open_vegetable_entry_dialog(self):
        """Open Add Vegetable panel."""
        self.open_dialog_wrapper(launch_vegetable_entry_dialog)

    def open_manual_panel(self):
        """Open Manual Product Entry panel."""
        self.open_dialog_wrapper(launch_manual_entry_dialog)

    def open_onhold_panel(self):
        """Open On Hold panel."""
        self.open_dialog_wrapper(launch_onhold_dialog)

    def open_viewhold_panel(self):
        """Open View Hold panel."""
        self.open_dialog_wrapper(launch_viewhold_dialog)

    def open_cancelsale_panel(self):
        """Open Cancel Sale panel."""
        self.open_dialog_wrapper(launch_cancelsale_dialog)

    # All dialog launchers use the common wrapper (excpect product menu)
    def open_dialog_wrapper(self, dialog_func, width_ratio=0.45, height_ratio=0.4, *args, **kwargs):
        """Open dialog with overlay and scanner block."""
        self.overlay_manager.toggle_dim_overlay(True)
        try:
            if hasattr(self, 'barcode_manager'):
                self.barcode_manager._start_scanner_modal_block()
        except Exception:
            pass
        try:
            dlg = dialog_func(self, *args, **kwargs)
            # Case A: Function returned a QDialog object (e.g. Vegetable Menu)
            if isinstance(dlg, QDialog):
                mw, mh = self.frameGeometry().width(), self.frameGeometry().height()
                dw, dh = max(360, int(mw * width_ratio)), max(220, int(mh * height_ratio))
                dlg.setFixedSize(dw, dh)
                mx, my = self.frameGeometry().x(), self.frameGeometry().y()
                dlg.move(mx + (mw - dw) // 2, my + (mh - dh) // 2)
                
                def _cleanup(_):
                    self.overlay_manager.toggle_dim_overlay(False)
                    try:
                        if hasattr(self, 'barcode_manager'):
                            self.barcode_manager._end_scanner_modal_block()
                    except Exception:
                        pass
                    self.raise_()
                    self.activateWindow()
                    self._refocus_sales_table()
                # Connect cleanup to finished signal (covers X, Cancel, OK, etc.)
                dlg.finished.connect(_cleanup)
                dlg.exec_()

            # Case B: Function ran exec_() itself (e.g. Logout, Admin)    
            else:
                self.overlay_manager.toggle_dim_overlay(False)
                try:
                    if hasattr(self, 'barcode_manager'):
                        self.barcode_manager._end_scanner_modal_block()
                except Exception:
                    pass

                self.raise_()
                self.activateWindow()
                self._refocus_sales_table()

        except Exception as e:
            self.overlay_manager.toggle_dim_overlay(False)
            try:
                if hasattr(self, 'barcode_manager'):
                    self.barcode_manager._end_scanner_modal_block()
            except Exception:

                pass
            print('Dialog failed:', e)

    def open_product_menu_dialog(self, *args, **kwargs):
        """
        Open Product Management panel with dedicated handling.
        """
        self.overlay_manager.toggle_dim_overlay(True)
        
        try:
            launch_product_dialog(self, **kwargs)
        except Exception as e:
            print('Product dialog failed:', e)
        finally:
            # 1. Hide Overlay
            self.overlay_manager.toggle_dim_overlay(False)
            
            # 2. Force Qt to process the 'Hide' event immediately. 
            # This ensures the Overlay widget is removed from the focus chain.
            QApplication.processEvents()
            
            try:
                self._clear_barcode_override()
            except Exception:
                pass

            # 3. Define the focus restoration logic
            def _force_focus_restore():
                try:
                    # Ensure main window is visually active
                    self.show()
                    self.raise_()
                    self.activateWindow()
                    
                    # Force Qt to drop focus from the "Product" button or hidden overlay
                    fw = QApplication.focusWidget()
                    if fw:
                        fw.clearFocus()
                    
                    # Finally, give focus to the table
                    self._refocus_sales_table()
                except Exception:
                    pass

            # 4. Trigger with a short delay (10ms is usually sufficient if processEvents is used)
            QTimer.singleShot(10, _force_focus_restore)

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

        # Insert sales_frame.ui into placeholder named 'salesFrame' (refactored: see modules/sales/sales_frame_setup.py)
        # This sets self.sales_table for use elsewhere in MainLoader.
        setup_sales_frame(self, UI_DIR)

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


    # Focus debug helpers have been moved to modules.debug.debug_utils.
    # To use them for debugging, uncomment the import at the top and call as follows:
    # debug_print_focus(context, barcode, main_window=self)
    # describe_widget(widget)
    # These are not required for normal operation and are intended for development/debugging only.

    def _on_focus_changed(self, old: QWidget, new: QWidget):
        try:
            print('[FocusChanged]', self._describe_widget(old), '->', self._describe_widget(new))
        except Exception:
            pass


    def _refocus_sales_table(self) -> None:
        try:
            table = getattr(self, 'sales_table', None)
            if table is not None:
                table.setFocusPolicy(Qt.StrongFocus)
                table.setFocus(Qt.OtherFocusReason)
                if table.rowCount() > 0 and table.columnCount() > 0:
                    table.setCurrentCell(0, 0)
            # else: do nothing if table not found
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
