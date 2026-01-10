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

from modules.table import setup_sales_table, handle_barcode_scanned, bind_total_label
from modules.sales.sales_frame_setup import setup_sales_frame
from modules.devices.barcode_manager import BarcodeManager
from modules.wrappers.dialog_wrapper import DialogWrapper
# --- Menu frame dialog controllers ---
from modules.menu.logout_menu import open_logout_dialog as launch_logout_dialog
from modules.menu.admin_menu import open_admin_dialog as launch_admin_dialog
from modules.menu.history_menu import open_history_dialog as launch_history_dialog
from modules.menu.reports_menu import open_reports_dialog as launch_reports_dialog
from modules.menu.greeting_menu import open_greeting_dialog as launch_greeting_dialog
from modules.menu.product_menu import open_dialog_scanner_enabled as launch_product_dialog
from modules.menu.vegetable_menu import open_vegetable_menu_dialog as launch_vegetable_menu_dialog
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
    ICON_HISTORY,
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
    qss_path = os.path.join(ASSETS_DIR, 'main.qss')
    if os.path.exists(qss_path):
        try:
            with open(qss_path, 'r', encoding='utf-8') as f:
                app.setStyleSheet(f.read())
        except Exception as e:
            print('Failed to load QSS:', e)

class MainLoader(QMainWindow):
    # ========== Menu Frame Dialog Handlers ==========
    def open_logout_menu_dialog(self):
        """Open Logout dialog."""
        self.dialog_wrapper.open_dialog_scanner_blocked(
            launch_logout_dialog,
            dialog_key='logout_menu',
            on_finish=lambda: self._perform_logout()
        )

    def open_product_menu_dialog(self, **kwargs):
        """Open Product Management panel."""
        self.dialog_wrapper.open_dialog_scanner_enabled(launch_product_dialog, dialog_key='product_menu', **kwargs)
        
    def open_admin_menu_dialog(self):
        """Open Admin dialog."""
        self.dialog_wrapper.open_dialog_scanner_blocked(
            launch_admin_dialog,
            dialog_key='admin_menu',
            current_user='Admin',
            is_admin=True
        )
    def open_greeting_menu_dialog(self):
        """Open Greeting dialog."""
        self.dialog_wrapper.open_dialog_scanner_blocked(launch_greeting_dialog, dialog_key='greeting_menu')
        """self.dialog_wrapper.open_dialog_scanner_blocked(launch_greeting_dialog)"""

    def open_history_menu_dialog(self):
        """Open Receipt History dialog."""
        self.dialog_wrapper.open_dialog_scanner_blocked(launch_history_dialog, dialog_key='history_menu')

    def open_reports_menu_dialog(self):
        """Open Reports dialog."""
        self.dialog_wrapper.open_dialog_scanner_blocked(launch_reports_dialog, dialog_key='reports_menu')

    def open_vegetable_menu_dialog(self):
        """Open Vegetable Management dialog."""
        self.dialog_wrapper.open_dialog_scanner_blocked(
            launch_vegetable_menu_dialog,
            dialog_key='vegetable_menu'
        )

    # ========== Sales Frame Dialog Handlers ==========

    def open_vegetable_entry_dialog(self):
        """Open Add Vegetable panel."""
        self.dialog_wrapper.open_dialog_scanner_blocked(
            lambda parent: launch_vegetable_entry_dialog(parent, self.sales_table),
            dialog_key='vegetable_entry',
            on_finish=self._add_items_to_sales_table
        )

    def open_manual_entry_dialog(self):
        """Open Manual Product Entry panel."""
        self.dialog_wrapper.open_dialog_scanner_blocked(
            launch_manual_entry_dialog, 
            dialog_key='manual_entry',
            on_finish=self._add_items_to_sales_table
        )

    def open_onhold_panel(self):
        """Open On Hold panel."""
        self.dialog_wrapper.open_dialog_scanner_blocked(launch_onhold_dialog, dialog_key='on_hold')

    def open_viewhold_panel(self):
        """Open View Hold panel."""
        self.dialog_wrapper.open_dialog_scanner_blocked(launch_viewhold_dialog, dialog_key='view_hold')

    def open_cancelsale_dialog(self):
        """Open Cancel Sale confirmation dialog."""
        self.dialog_wrapper.open_dialog_scanner_blocked(
            launch_cancelsale_dialog,
            dialog_key='cancel_sale',
            on_finish=lambda: self._clear_sales_table()
        )

    # ========== Initialization ==========
    def __init__(self):
        super().__init__()
        self.overlay_manager = OverlayManager(self)
        self.dialog_wrapper = DialogWrapper(self)
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
        try:
            app = QApplication.instance()
            if app is not None:
                self.barcode_manager.install_event_filter(app)
            else:
                self.barcode_manager.install_event_filter(self)
        except Exception:
            pass

        # Insert sales_frame.ui into placeholder named 'salesFrame'
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
            'historyBtn': ICON_HISTORY,
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
                'historyBtn': 'History',
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
                elif obj_name == 'historyBtn':
                    btn.clicked.connect(self.open_history_menu_dialog)
                else:
                    try:
                        btn.setEnabled(False)
                        btn.setToolTip(title)
                    except Exception:
                        pass
        except Exception as e:
            print('Failed to wire menu buttons:', e)

    # ========== Post-Dialog Action Handlers ==========
    def _add_items_to_sales_table(self):
        """Unified handler to add items from dialogs to sales table.
        Reads dialog results (vegetable_rows or manual_entry_result), normalizes to row format,
        merges with existing sales table rows (handles duplicates), and rebuilds the table.
        """
        if not hasattr(self, 'sales_table'):
            return

        try:
            from PyQt5.QtWidgets import QLineEdit
            from modules.table.table_operations import set_table_rows
            from modules.table.unit_helpers import canonicalize_unit

            # Get the dialog that just closed
            dlg = self.dialog_wrapper._last_dialog
            if dlg is None or dlg.result() != QDialog.Accepted:
                return

            # Read and normalize dialog results
            new_rows = []
            vegetable_rows = getattr(dlg, 'vegetable_rows', None)
            manual_result = getattr(dlg, 'manual_entry_result', None)
            if vegetable_rows:
                # print(f"[main.py] Received vegetable_rows: {vegetable_rows}")
                new_rows = []
                for row in vegetable_rows:
                    row_copy = dict(row)
                    row_copy['product'] = row.get('product_name', row.get('product', ''))
                    row_copy['unit'] = canonicalize_unit(row_copy.get('unit', 'Each'))
                    new_rows.append(row_copy)
            elif manual_result:
                unit_val = canonicalize_unit(manual_result.get('unit', 'Each'))
                new_rows = [{
                    'product': manual_result['product_name'],
                    'quantity': manual_result['quantity'],
                    'unit_price': manual_result['unit_price'],
                    'unit': unit_val,
                    'editable': unit_val != 'Kg'
                }]
            else:
                return

            # Get existing rows from sales table
            existing_rows = []
            for r in range(self.sales_table.rowCount()):
                product_item = self.sales_table.item(r, 1)
                if product_item is None:
                    continue

                qty_container = self.sales_table.cellWidget(r, 2)
                qty = 1.0
                row_editable = True
                if qty_container is not None:
                    editor = qty_container.findChild(QLineEdit, 'qtyInput')
                    if editor is not None:
                        row_editable = not editor.isReadOnly()
                        numeric_val = editor.property('numeric_value')
                        if numeric_val is not None:
                            try:
                                qty = float(numeric_val)
                            except (ValueError, TypeError):
                                qty = 1.0
                        else:
                            try:
                                qty = float(editor.text()) if editor.text() else 1.0
                            except ValueError:
                                qty = 1.0

                price_item = self.sales_table.item(r, 4)
                price = 0.0
                if price_item is not None:
                    try:
                        price = float(price_item.text())
                    except ValueError:
                        price = 0.0

                unit_item = self.sales_table.item(r, 3)
                unit_val = canonicalize_unit(unit_item.text() if unit_item is not None else '')
                row_data = {
                    'product': product_item.text(),
                    'quantity': qty,
                    'unit_price': price,
                    'editable': row_editable,
                    'unit': unit_val
                }
                existing_rows.append(row_data)

            # Merge new rows into existing rows (handle duplicates for all sources)
            for new_row in new_rows:
                new_product = new_row.get('product', '')
                new_unit = new_row.get('unit', '')
                new_editable = new_row.get('editable', True)
                new_qty = new_row.get('quantity', 0.0)

                found_match = False
                for existing_row in existing_rows:
                    if (
                        existing_row['product'] == new_product and
                        existing_row.get('unit', '') == new_unit and
                        existing_row.get('editable', True) == new_editable
                    ):
                        existing_row['quantity'] += new_qty
                        found_match = True
                        break

                if not found_match:
                    existing_rows.append(new_row)

            # print(f"[main.py] FINAL rows to set_table_rows: {existing_rows}")
            set_table_rows(self.sales_table, existing_rows)
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _clear_sales_table(self):
        """Clear all items from sales table and reset total to zero.
        
        Called after user confirms Cancel All action.
        """
        if not hasattr(self, 'sales_table'):
            return
        
        try:
            # Check if dialog was confirmed
            dlg = self.dialog_wrapper._last_dialog
            if dlg is None or dlg.result() != QDialog.Accepted:
                return
            
            # Clear all rows from sales table
            self.sales_table.setRowCount(0)
            
            # Recompute total (will set to 0.00 and update label)
            from modules.table import recompute_total
            recompute_total(self.sales_table)
            
            # Future: When payment frame is implemented, reset it here
            # Example:
            # payment_inputs = ['cashInput', 'netsInput', 'paynowInput', 'voucherInput']
            # for input_name in payment_inputs:
            #     input_widget = self.findChild(QLineEdit, input_name)
            #     if input_widget:
            #         input_widget.clear()
        except Exception as e:
            print(f'Failed to clear sales table: {e}')
            import traceback
            traceback.print_exc()

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

    # ========== Window Lifecycle ==========
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
    """window.show()"""
    window.showMaximized()
    try:
        # Bring window to front in case it opens behind other windows
        window.raise_()
        window.activateWindow()
    except Exception:
        pass
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
