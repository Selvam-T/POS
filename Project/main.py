#!/usr/bin/env python3
"""POS System main window loader. See Documentation/main_py_overview.md for details."""
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import sys
import os
import time
import config
from modules.ui_utils.overlay_manager import OverlayManager
from modules.ui_utils.greeting_state import load_greeting, save_greeting
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
from modules.table.table_operations import get_sales_data
from modules.sales.sales_frame_setup import setup_sales_frame
from modules.payment.payment_panel import setup_payment_panel
from modules.db_operation.paid_sale_committer import PaidSaleCommitter
from modules.devices.barcode_manager import BarcodeManager
from modules.wrappers.dialog_wrapper import DialogWrapper
from modules.db_operation import PRODUCT_CACHE
from modules.ui_utils.dialog_utils import report_exception, report_to_statusbar
# --- Menu frame dialog controllers ---
from modules.menu.logout_menu import launch_logout_dialog
from modules.menu.admin_menu import launch_admin_dialog
from modules.menu.history_menu import launch_history_dialog
from modules.menu.reports_menu import launch_reports_dialog
from modules.menu.greeting_menu import launch_greeting_dialog
from modules.menu.product_menu import launch_product_dialog
from modules.menu.vegetable_menu import launch_vegetable_menu_dialog
# --- Sales frame dialog controllers ---
from modules.sales.vegetable_entry import launch_vegetable_entry_dialog
from modules.sales.manual_entry import launch_manual_entry_dialog
from modules.sales.hold_sales import launch_hold_sales_dialog
from modules.sales.view_hold import launch_viewhold_dialog
from modules.sales.clear_cart import launch_clearcart_dialog

from config import (
    ICON_ADMIN,
    ICON_REPORTS,
    ICON_VEGETABLE,
    ICON_PRODUCT,
    ICON_GREETING,
    ICON_HISTORY,
    ICON_LOGOUT,
)
from modules.date_time.info_section import InfoSectionController

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')

_saved_greeting = load_greeting()
if _saved_greeting:
    config.GREETING_SELECTED = _saved_greeting


# Load and apply the main stylesheet if it exists.
def load_qss(app):
    qss_path = os.path.join(ASSETS_DIR, 'main.qss')
    if os.path.exists(qss_path):
        try:
            with open(qss_path, 'r', encoding='utf-8') as f:
                app.setStyleSheet(f.read())
        except Exception as e:
            try:
                from modules.ui_utils.error_logger import log_error
                log_error(f"Failed to load QSS: {e}")
            except Exception:
                pass

class MainLoader(QMainWindow):
    # ========== Initialization ==========
    # Initialize the main loader, controllers, and wiring.
    def __init__(self):
        super().__init__()
        self.overlay_manager = OverlayManager(self)
        self.dialog_wrapper = DialogWrapper(self)
        main_ui = os.path.join(UI_DIR, 'main_window.ui')
        uic.loadUi(main_ui, self)
        self.receipt_context = {
            'active_receipt_id': None,
            'source': 'ACTIVE_SALE',
            'status': 'NONE',
            'last_receipt_no': None,
        }
        self._payment_in_progress = False
        self._payment_busy_status_ms = 3000
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
        self.sales_frame_controller = setup_sales_frame(self, UI_DIR)
        if self.sales_frame_controller is not None:
            self._wire_sales_frame_signals()

        self.payment_panel_controller = setup_payment_panel(self, UI_DIR)
        if self.payment_panel_controller is not None:
            self._wire_payment_panel_signals()

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
                    btn.clicked.connect(self.launch_vegetable_menu_dialog)
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
            try:
                from modules.ui_utils.error_logger import log_error
                log_error(f"Failed to wire menu buttons: {e}")
            except Exception:
                pass

    # Stop devices and close the app when logging out.
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

    # Block closing unless logout has granted permission.
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

    # ========== Menu Frame Dialog Handlers ==========
    # Trigger logout dialog via the dialog wrapper.
    def open_logout_menu_dialog(self):
        """Open Logout dialog."""
        self.dialog_wrapper.open_dialog_scanner_blocked(
            launch_logout_dialog,
            dialog_key='logout_menu',
            on_finish=lambda: self._perform_logout()
        )

    # Open the product management dialog with sale guards.
    def open_product_menu_dialog(self, **kwargs):
        """Open Product Management panel with Step 0 Sale-Active check."""
        # Standardize hard-fail handling: keep all launch-time work inside
        # DialogWrapper's try/except boundary.
        def _open(main_window):
            from modules.table.table_operations import is_transaction_active

            local_kwargs = dict(kwargs or {})

            # Protect an active transaction: force initial_mode='add'
            if is_transaction_active(getattr(main_window, 'sales_table', None)):
                local_kwargs['initial_mode'] = 'add'

            return launch_product_dialog(main_window, **local_kwargs)

        self.dialog_wrapper.open_dialog_scanner_blocked(
            _open,
            dialog_key='product_menu',
        )
        
    # Launch the admin menu dialog with admin context.
    def open_admin_menu_dialog(self):
        """Open Admin dialog."""
        self.dialog_wrapper.open_dialog_scanner_blocked(
            launch_admin_dialog,
            dialog_key='admin_menu',
            current_user='Admin',
            is_admin=True
        )
    # Show the greeting menu dialog.
    def open_greeting_menu_dialog(self):
        """Open Greeting dialog."""
        self.dialog_wrapper.open_dialog_scanner_blocked(
            launch_greeting_dialog,
            dialog_key='greeting_menu',
            on_finish=self._handle_greeting_selection
        )

    def _handle_greeting_selection(self) -> None:
        dlg = getattr(self.dialog_wrapper, '_last_dialog', None)
        if dlg is None:
            return
        selected = getattr(dlg, 'greeting_result', None)
        if not selected:
            return
        config.GREETING_SELECTED = selected
        try:
            save_greeting(selected)
        except Exception:
            pass

    # Display the receipt history dialog.
    def open_history_menu_dialog(self):
        """Open Receipt History dialog."""
        self.dialog_wrapper.open_dialog_scanner_blocked(launch_history_dialog, dialog_key='history_menu')

    # Open the reports dialog for analytics.
    def open_reports_menu_dialog(self):
        """Open Reports dialog."""
        self.dialog_wrapper.open_dialog_scanner_blocked(launch_reports_dialog, dialog_key='reports_menu')

    # Launch the vegetable management dialog when allowed.
    def launch_vegetable_menu_dialog(self):
        """Open Vegetable Management dialog."""
        ctx = getattr(self, 'receipt_context', {}) or {}
        if ctx.get('source') == 'HOLD_LOADED':
            from modules.ui_utils.ui_feedback import show_temp_status
            sb = getattr(self, 'statusbar', None)
            if sb:
                show_temp_status(sb, "Vegetable menu disabled for held receipts.", 3000)
            return

        self.dialog_wrapper.open_dialog_scanner_blocked(
            launch_vegetable_menu_dialog,
            dialog_key='vegetable_menu'
        )

    # ========== Sales Frame Dialog Handlers ==========

    # Request the vegetable entry dialog and merge its results.
    def launch_vegetable_entry_dialog(self):
        """Open Add Vegetable panel."""
        self.dialog_wrapper.open_dialog_scanner_blocked(
            lambda parent: launch_vegetable_entry_dialog(parent, self.sales_table),
            dialog_key='vegetable_entry',
            on_finish=self._add_items_to_sales_table
        )

    # Present manual entry dialog unless sale is held.
    def launch_manual_entry_dialog(self):
        """Open Manual Product Entry panel."""
        ctx = getattr(self, 'receipt_context', {})
        if (ctx or {}).get('source') == 'HOLD_LOADED':
            from modules.ui_utils.ui_feedback import show_temp_status
            sb = getattr(self, 'statusbar', None)
            if sb:
                show_temp_status(sb, "Manual entry disabled for held receipts.", 3000)
            return
        self.dialog_wrapper.open_dialog_scanner_blocked(
            launch_manual_entry_dialog, 
            dialog_key='manual_entry',
            on_finish=self._add_items_to_sales_table
        )

    # Open the hold sales dialog for active transactions.
    def launch_hold_sales_dialog(self):
        """Open On Hold panel."""
        from modules.ui_utils.ui_feedback import show_temp_status

        if not self._can_launch_hold_sales_dialog():
            sb = getattr(self, 'statusbar', None)
            if sb:
                show_temp_status(sb, "No active sale to place on hold.", 3000)
            return

        self.dialog_wrapper.open_dialog_scanner_blocked(launch_hold_sales_dialog, dialog_key='hold_sales')

    # Display the view hold panel when no sale is running.
    def open_viewhold_panel(self):
        """Open View Hold panel."""
        from modules.ui_utils.ui_feedback import show_temp_status

        sales_table = getattr(self, 'sales_table', None)
        ctx = getattr(self, 'receipt_context', {}) or {}

        # Allow view-hold only when no active sale rows and no active receipt id
        if sales_table is None or sales_table.rowCount() > 0 or ctx.get('active_receipt_id') is not None:
            sb = getattr(self, 'statusbar', None)
            if sb:
                show_temp_status(sb, "View Hold is available only when no sale is in progress.", 3000)
            return

        # Optional extra guard: ensure payment frame is effectively empty (total 0)
        pay_label = self.findChild(QLabel, 'totalValPayLabel')
        if pay_label is not None:
            text = (pay_label.text() or '').strip()
            try:
                pay_total = float(text.replace(',', '')) if text else 0.0
            except ValueError:
                pay_total = 0.0
            if pay_total != 0.0:
                sb = getattr(self, 'statusbar', None)
                if sb:
                    show_temp_status(sb, "Clear payment before viewing holds.", 3000)
                return

        self.dialog_wrapper.open_dialog_scanner_blocked(launch_viewhold_dialog, dialog_key='view_hold')

    # Prompt clear cart dialog only when a sale exists.
    def open_clearcart_dialog(self):
        """Open Clear Cart confirmation dialog, only if there is an active sale."""
        from modules.table.table_operations import is_transaction_active
        from modules.ui_utils.ui_feedback import show_temp_status

        sales_table = getattr(self, 'sales_table', None)
        if not is_transaction_active(sales_table):
            sb = getattr(self, 'statusbar', None)
            if sb:
                show_temp_status(sb, "Cart is empty.", 3000)
            return
        self.dialog_wrapper.open_dialog_scanner_blocked(
            launch_clearcart_dialog,
            dialog_key='clear_cart',
            on_finish=lambda: self._clear_sales_table()
        )

    # ========== Signal Wiring ==========
    # Connect sales frame signals to this window.
    def _wire_sales_frame_signals(self):
        frame = getattr(self, 'sales_frame_controller', None)
        if frame is None:
            return
        frame.saleTotalChanged.connect(self._on_sale_total_changed)
        frame.viewHoldLoaded.connect(self._on_view_hold_loaded)

    # Connect payment panel signals to handlers.
    def _wire_payment_panel_signals(self):
        panel = getattr(self, 'payment_panel_controller', None)
        if panel is None:
            return
        panel.payRequested.connect(self._on_payment_requested)
        panel.paymentSuccess.connect(self._on_payment_success)

    def _reset_receipt_context(self) -> None:
        ctx = self.receipt_context
        ctx['active_receipt_id'] = None
        ctx['source'] = 'ACTIVE_SALE'
        ctx['status'] = 'NONE'

    def _can_launch_hold_sales_dialog(self) -> bool:
        ctx = getattr(self, 'receipt_context', {}) or {}
        sales_table = getattr(self, 'sales_table', None)

        try:
            has_rows = sales_table is not None and sales_table.rowCount() > 0
        except Exception:
            has_rows = False

        source_ok = ctx.get('source') == 'ACTIVE_SALE'
        active_ok = ctx.get('active_receipt_id') is None
        status = ctx.get('status')
        status_ok = status in (None, 'NA', 'NONE')

        return bool(has_rows and source_ok and active_ok and status_ok)

    # ========== Signal Handlers ==========
    # Update payment defaults when sale total updates.
    def _on_sale_total_changed(self, total: float) -> None:
        panel = getattr(self, 'payment_panel_controller', None)
        if panel is not None:
            panel.set_payment_default(total)

    # Update receipt context when a held sale is loaded.
    def _on_view_hold_loaded(self, receipt_id: int, total: float) -> None:
        ctx = self.receipt_context
        ctx['active_receipt_id'] = receipt_id
        ctx['source'] = 'HOLD_LOADED'
        ctx['status'] = 'UNPAID'
        print(f"ReceiptContext updated for hold load: {ctx}")

    # Process payment requests from the payment panel.
    def _on_payment_requested(self, payment_split: dict) -> None:
        if self.pay_current_receipt(payment_split):
            panel = getattr(self, 'payment_panel_controller', None)
            if panel is not None:
                panel.notify_payment_success()

    # Clear state after successful payment completion.
    def _on_payment_success(self) -> None:
        self._reset_receipt_context()
        print(f"Payment success: {self.receipt_context}")
        self._clear_sales_table_core()
        panel = getattr(self, 'payment_panel_controller', None)
        if panel is not None:
            panel.clear_payment_frame()

    # ========== Payment Processing ==========
    # Orchestrates payment; atomic DB commit is delegated to PaidSaleCommitter.

    def _build_payment_rows(self, payment_split: dict) -> list[tuple[str, float, float]]:
        rows = []
        mapping = {
            'cash': 'CASH',
            'nets': 'NETS',
            'paynow': 'PAYNOW',
            'voucher': 'OTHER',
        }
        for key, ptype in mapping.items():
            try:
                amount = float(payment_split.get(key, 0.0) or 0.0)
            except Exception:
                amount = 0.0
            if amount > 0:
                if key == 'cash':
                    try:
                        tendered = float(payment_split.get('tender', amount) or amount)
                    except Exception:
                        tendered = amount
                else:
                    tendered = amount
                rows.append((ptype, amount, tendered))
        return rows

    def _build_sale_items_snapshot(self) -> list[dict]:
        sales_table = getattr(self, 'sales_table', None)
        rows = get_sales_data(sales_table) if sales_table is not None else []

        by_name: dict[str, str] = {}
        try:
            for code, rec in (PRODUCT_CACHE or {}).items():
                if not rec:
                    continue
                name = str(rec[0] or '').strip()
                if not name:
                    continue
                by_name.setdefault(name.lower(), str(code))
        except Exception:
            by_name = {}

        out = []
        for row in rows:
            name = str(row.get('product_name') or row.get('product') or '').strip()
            qty = float(row.get('quantity') or 0.0)
            unit_price = float(row.get('unit_price') or 0.0)
            out.append({
                'product_code': by_name.get(name.lower(), ''),
                'name': name,
                'category': '',
                'quantity': qty,
                'unit': str(row.get('unit') or ''),
                'price': unit_price,
                'line_total': round(qty * unit_price, 2),
            })
        return out

    def _should_open_cash_drawer(self, payment_split: dict) -> bool:
        try:
            cash = float(payment_split.get('cash', 0.0) or 0.0)
        except Exception:
            cash = 0.0
        try:
            tender = float(payment_split.get('tender', 0.0) or 0.0)
        except Exception:
            tender = 0.0
        return cash > 0 and tender > 0

    def _open_cash_drawer_if_needed(self, payment_split: dict) -> None:
        if not bool(getattr(config, 'ENABLE_CASH_DRAWER', True)):
            return
        if not self._should_open_cash_drawer(payment_split):
            return

        try:
            from modules.devices import printer as device_printer
            opened = device_printer.open_cash_drawer(
                pin=int(getattr(config, 'CASH_DRAWER_PIN', 2)),
                blocking=True,
                timeout=float(getattr(config, 'CASH_DRAWER_TIMEOUT', 2.0)),
            )
            if not opened:
                report_to_statusbar(
                    self,
                    "Cash drawer failed to open.",
                    is_error=True,
                    duration=4000,
                )
                try:
                    from modules.ui_utils.error_logger import log_error
                    log_error("Cash drawer open failed (helper returned False).")
                except Exception:
                    pass
        except Exception as e:
            report_to_statusbar(
                self,
                "Cash drawer error.",
                is_error=True,
                duration=4000,
            )
            try:
                from modules.ui_utils.error_logger import log_error
                log_error(f"Cash drawer helper call failed: {e}")
            except Exception:
                pass


    def pay_current_receipt(self, payment_split: dict) -> bool:
        """Process current payment via PaidSaleCommitter atomic service."""
        if self._payment_in_progress:
            report_to_statusbar(
                self,
                "Payment is already processing...",
                is_error=False,
                duration=self._payment_busy_status_ms,
            )
            return False

        ctx = self.receipt_context
        active_receipt_id = ctx.get('active_receipt_id')
        panel = getattr(self, 'payment_panel_controller', None)

        self._payment_in_progress = True
        if panel is not None:
            try:
                pay_btn = panel._widgets.get('pay_button')
                if pay_btn is not None:
                    pay_btn.setEnabled(False)
            except Exception:
                pass

        try:
            sales_items = self._build_sale_items_snapshot()
            payment_rows = self._build_payment_rows(payment_split)

            total = float(payment_split.get('total', 0.0) or 0.0)
            committer = PaidSaleCommitter()
            receipt_no = committer.commit_payment(
                active_receipt_id=active_receipt_id,
                sales_items=sales_items,
                payment_rows=payment_rows,
                total=total,
            )

            self.receipt_context['last_receipt_no'] = str(receipt_no)

            self._open_cash_drawer_if_needed(payment_split)

            report_to_statusbar(
                self,
                f"Payment completed: {receipt_no}",
                is_error=False,
                duration=5000,
            )
            return True

        except Exception as e:
            report_exception(
                self,
                "Payment processing",
                e,
                user_message="Payment failed. Please retry.",
                duration=6000,
            )
            return False

        finally:
            self._payment_in_progress = False
            if panel is not None:
                try:
                    panel.update_pay_button_state()
                except Exception:
                    pass

    # ========== Post-Dialog Action Handlers ==========
    # Merge items returned by dialogs into the sales table.
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
            set_table_rows(self.sales_table, existing_rows)
        except Exception as e:
            try:
                import traceback
                from modules.ui_utils.error_logger import log_error
                log_error(traceback.format_exc())
            except Exception:
                pass

    # Clear table rows and reset payment panel after cancel.
    def _clear_sales_table_core(self) -> None:
        """Clear sales table rows and recompute total without dialog checks."""
        if not hasattr(self, 'sales_table'):
            return
        try:
            self.sales_table.setRowCount(0)
            from modules.table import recompute_total
            recompute_total(self.sales_table)
        except Exception as e:
            try:
                from modules.ui_utils.error_logger import log_error
                log_error(f"Failed to clear sales table core: {e}")
            except Exception:
                pass

    def _clear_sales_table(self):
        """Clear all items from sales table and reset total to zero.
        
        Called after user confirms Cancel All action.
        """
        try:
            dlg = self.dialog_wrapper._last_dialog
            if dlg is None or dlg.result() != QDialog.Accepted:
                return

            self._clear_sales_table_core()
            self._reset_receipt_context()

            panel = getattr(self, 'payment_panel_controller', None)
            if panel is not None:
                panel.clear_payment_frame()
        except Exception as e:
            try:
                import traceback
                from modules.ui_utils.error_logger import log_error
                log_error(f"Failed to clear sales table: {e}\n{traceback.format_exc()}")
            except Exception:
                pass

    # Empty the sales table without dialog confirmation.
    def _clear_sales_table_force(self):
        """Clear sales table without dialog checks (used after payment success)."""
        try:
            self._clear_sales_table_core()
        except Exception as e:
            try:
                from modules.ui_utils.error_logger import log_error
                log_error(f"Failed to force-clear sales table: {e}")
            except Exception:
                pass


# Bootstrap the QApplication and launch the main window.
def main():
    app = QApplication(sys.argv)
    load_qss(app)

    cache_load_failed = False

    # Load product cache once at startup so name/code lookups and completers
    # can rely on in-memory PRODUCT_CACHE during runtime.
    try:
        from modules.db_operation import load_product_cache, PRODUCT_CACHE
        load_product_cache()
    except Exception as e:
        cache_load_failed = True
        try:
            from modules.ui_utils.error_logger import log_error
            log_error(f"Failed to load PRODUCT_CACHE: {e}")
        except Exception:
            pass

    window = MainLoader()
    """window.show()"""
    window.showMaximized()
    try:
        # Bring window to front in case it opens behind other windows
        window.raise_()
        window.activateWindow()
    except Exception:
        pass

    # If cache load failed earlier, surface it once the status bar exists.
    if cache_load_failed:
        report_to_statusbar(
            window,
            'Error: Failed to load product list (search may be limited)',
            is_error=True,
            duration=6000,
        )
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
