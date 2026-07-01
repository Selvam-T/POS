#!/usr/bin/env python3
"""POS System main window loader. See Documentation/main_py_overview.md for details."""
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import sys
import os
import config
from modules.ui_utils.overlay_manager import OverlayManager
from modules.ui_utils.greeting_state import load_greeting, save_greeting
from PyQt5 import uic
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QDialog,
    QMessageBox,
)
from PyQt5.QtCore import Qt, QSize, QTimer, qInstallMessageHandler
from PyQt5.QtGui import QIcon

from modules.table_ui.table_operations import get_sales_data
from modules.sales.sales_panel import setup_sales_frame
from modules.payment.payment_panel import setup_payment_panel
from modules.payment.refund import launch_refund_dialog
from modules.payment.vendor import launch_vendor_dialog
from modules.db_operation.paid_sale_committer import PaidSaleCommitter
from modules.devices.barcode_manager import BarcodeManager
from modules.customer_display import CustomerDisplayWindow
from modules.wrappers.dialog_wrapper import DialogWrapper
from modules.db_operation import PRODUCT_CACHE, ensure_cash_outflows_table
from modules.ui_utils.dialog_utils import report_exception, report_to_statusbar
from modules.ui_utils.money_format import round_money
from modules.runtime.paths import load_stylesheet, stylesheet_path
# --- Menu frame dialog controllers ---
from modules.menu.logout_menu import launch_logout_dialog
from modules.menu.admin_menu import launch_admin_dialog
from modules.menu.receipt_menu import launch_receipt_dialog
from modules.menu.report_menu import launch_reports_dialog
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
    ICON_RECEIPT,
    ICON_LOGOUT,
)
from modules.info_section.info_section import InfoSectionController
from modules.status_footer import MainStatusFooterController

UI_DIR = config.UI_DIR
ASSETS_DIR = config.ASSETS_DIR

_saved_greeting = load_greeting()
if _saved_greeting:
    config.GREETING_SELECTED = _saved_greeting


# Load and apply the main stylesheet if it exists.
def load_qss(app):
    qss_path = stylesheet_path('main.qss')
    if os.path.exists(qss_path):
        try:
            app.setStyleSheet(load_stylesheet(qss_path))
        except Exception as e:
            try:
                from modules.ui_utils.error_logger import log_error_message
                log_error_message(f"Failed to load QSS: {e}")
            except Exception:
                pass

class MainLoader(QMainWindow):
    def statusBar(self):
        """Return the custom footer status bar loaded from main_window.ui."""
        custom_statusbar = getattr(self, 'statusbar', None)
        if custom_statusbar is not None:
            return custom_statusbar
        return super().statusBar()

    def launch_login_dialog_blocked(self):
        """Show login dialog in barcode-blocked mode, open main app on success."""
        from modules.sales.login import launch_login_dialog
        self.dialog_wrapper._show_overlay()
        self.dialog_wrapper._block_scanner()
        login_success = launch_login_dialog(self)
        self.dialog_wrapper._hide_overlay()
        self.dialog_wrapper._unblock_scanner()
        if login_success:
            self.show()  # Open main app window
        else:
            # Optionally show a message or stay blocked
            pass
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
        # App-level logged-in user context (to be wired by login flow).
        self.current_user_id = None
        self.current_username = ""
        self.current_is_admin = False
        self._sales_table_ready = False
        self._sales_table_failure_logged = False
        self._sales_table_error = ""
        self._sales_table_unavailable_message = (
            "Sales table unavailable. Transactions are disabled. Restart the application."
        )
        self._payment_in_progress = False
        self._payment_busy_status_ms = 3000
        self._payment_db_failure_count = 0
        self._payment_db_failure_limit = 3
        self._payment_failure_lock_active = False
        self._payment_failure_status_message = "Payment recovery required: print receipt if needed, then clear sales table."
        self._payment_failure_status_reapply_pending = False
        self.status_footer = MainStatusFooterController().bind(self)
        try:
            self.statusbar.messageChanged.connect(self._on_statusbar_message_changed)
        except Exception:
            pass
        try:
            ensure_cash_outflows_table()
        except Exception as exc:
            try:
                from modules.ui_utils.error_logger import log_error_message
                log_error_message(f"Cash outflows table ensure failed: {exc}")
            except Exception:
                pass
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
            self._sales_table_ready = getattr(self, 'sales_table', None) is not None
            self._wire_sales_frame_signals()
        elif not self._sales_table_failure_logged:
            self._mark_sales_table_unavailable(
                RuntimeError("Sales frame initialization did not produce a sales table"),
                where="Sales table initialization",
            )

        # Ensure sales label matches initial receipt context.
        self._refresh_sales_label_from_context()

        self.payment_panel_controller = setup_payment_panel(self, UI_DIR)
        if self.payment_panel_controller is not None:
            self._wire_payment_panel_signals()

        self._init_customer_display()

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
            'receiptBtn': ICON_RECEIPT,
            'logoutBtn': ICON_LOGOUT,
        }
        try:
            def set_btn_icon_path(btn: QPushButton, icon_path: str, size: int = 60) -> bool:
                """Set a button icon from a config-defined runtime path.
                Returns True on success, False if file missing or error.
                """
                try:
                    if os.path.exists(icon_path):
                        btn.setIcon(QIcon(icon_path))
                        btn.setIconSize(QSize(size, size))
                        return True
                    # Icon file missing; fall back to text label
                    return False
                except Exception as _e:
                    # Ignore icon errors and fall back to text label.
                    return False

            menu_buttons = {
                'adminBtn': 'Admin',
                'reportsBtn': 'Reports',
                'vegetableBtn': 'Vegetable',
                'productBtn': 'Product',
                'greetingBtn': 'Greeting',
                'receiptBtn': 'Receipt',
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
                    btn.clicked.connect(self.open_report_menu_dialog)
                elif obj_name == 'receiptBtn':
                    btn.clicked.connect(self.open_receipt_menu_dialog)
                else:
                    try:
                        btn.setEnabled(False)
                        btn.setToolTip(title)
                    except Exception:
                        pass
        except Exception as e:
            try:
                from modules.ui_utils.error_logger import log_error_message
                log_error_message(f"Failed to wire menu buttons: {e}")
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
                        sb.showMessage('Use the Logout button in the menu to exit.', config.MAIN_STATUS_DURATION_MS)
                except Exception:
                    pass
                event.ignore()
                return
        except Exception:
            pass
        super().closeEvent(event)

    def resizeEvent(self, event):
        """Keep modal overlay sized to the main window."""
        try:
            self.overlay_manager.resize_overlay()
        except Exception:
            pass
        super().resizeEvent(event)

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
            from modules.table_ui.table_operations import is_transaction_active

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
        if not bool(getattr(self, 'current_is_admin', False)):
            report_to_statusbar(
                self,
                "Admin access denied.",
                is_error=True,
                duration=config.MAIN_STATUS_ERROR_DURATION_MS,
            )
            return

        current_user_id = getattr(self, 'current_user_id', None)
        self.dialog_wrapper.open_dialog_scanner_blocked(
            launch_admin_dialog,
            dialog_key='admin_menu',
            user_id=current_user_id,
            is_admin=True,
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
    def open_receipt_menu_dialog(self):
        """Open Receipt History dialog."""
        self.dialog_wrapper.open_dialog_scanner_blocked(launch_receipt_dialog, dialog_key='receipt_menu')

    # Open the reports dialog for analytics.
    def open_report_menu_dialog(self):
        """Open Reports dialog."""
        self.dialog_wrapper.open_dialog_scanner_blocked(launch_reports_dialog, dialog_key='report_menu')

    # Launch the vegetable management dialog when allowed.
    def launch_vegetable_menu_dialog(self):
        """Open Vegetable Management dialog."""
        ctx = getattr(self, 'receipt_context', {}) or {}
        if ctx.get('source') == 'HOLD_LOADED':
            from modules.ui_utils.ui_feedback import show_temp_status
            sb = getattr(self, 'statusbar', None)
            if sb:
                show_temp_status(sb, "Vegetable menu disabled for held receipts.", config.MAIN_STATUS_DURATION_MS)
            return

        self.dialog_wrapper.open_dialog_scanner_blocked(
            launch_vegetable_menu_dialog,
            dialog_key='vegetable_menu'
        )

    # ========== Sales Frame Dialog Handlers ==========

    def _show_sales_table_unavailable(self) -> None:
        report_to_statusbar(
            self,
            self._sales_table_unavailable_message,
            is_error=True,
            duration=config.MAIN_STATUS_LONG_DURATION_MS,
        )

    def _mark_sales_table_unavailable(self, exc: Exception, *, where: str) -> None:
        self._sales_table_ready = False
        self._sales_table_error = f"{where}: {exc!r}"
        if not self._sales_table_failure_logged:
            try:
                import traceback
                from modules.ui_utils.error_logger import log_error_message

                details = traceback.format_exc()
                message = self._sales_table_error
                if details and details.strip() != "NoneType: None":
                    message = f"{message}\n{details}"
                log_error_message(message)
            except Exception:
                pass
            self._sales_table_failure_logged = True
        self._show_sales_table_unavailable()

    def _require_sales_table_ready(self) -> bool:
        table = getattr(self, 'sales_table', None)
        if self._sales_table_ready and table is not None:
            try:
                table.rowCount()
                return True
            except Exception as exc:
                self._mark_sales_table_unavailable(exc, where="Sales table readiness check")
                return False

        if not self._sales_table_failure_logged:
            self._mark_sales_table_unavailable(
                RuntimeError("Sales table is not initialized"),
                where="Sales table readiness check",
            )
        else:
            self._show_sales_table_unavailable()
        return False

    # Request the vegetable entry dialog and merge its results.
    def launch_vegetable_entry_dialog(self):
        """Open Add Vegetable panel."""
        if not self._require_sales_table_ready():
            return
        display = getattr(self, 'customer_display', None)
        if display is not None:
            display.hide_payment_result_overlay()
        
        if self._is_hold_loaded_in_cart():
            from modules.ui_utils.ui_feedback import show_temp_status
            sb = getattr(self, 'statusbar', None)
            if sb:
                show_temp_status(sb, "On Hold Receipt loaded. Vegetable entry not allowed.", config.MAIN_STATUS_DURATION_MS)
            return

        self.dialog_wrapper.open_dialog_scanner_blocked(
            lambda parent: launch_vegetable_entry_dialog(parent, self.sales_table),
            dialog_key='vegetable_entry',
            on_finish=self._add_items_to_sales_table
        )

    # Present manual entry dialog unless sale is held.
    def launch_manual_entry_dialog(self):
        """Open Manual Product Entry panel."""
        if not self._require_sales_table_ready():
            return
        display = getattr(self, 'customer_display', None)
        if display is not None:
            display.hide_payment_result_overlay()
        
        if self._is_hold_loaded_in_cart():
            from modules.ui_utils.ui_feedback import show_temp_status
            sb = getattr(self, 'statusbar', None)
            if sb:
                show_temp_status(sb, "On Hold Receipt loaded. Manual entry not allowed.", config.MAIN_STATUS_DURATION_MS)
            return
        self.dialog_wrapper.open_dialog_scanner_blocked(
            launch_manual_entry_dialog, 
            dialog_key='manual_entry',
            on_finish=self._add_items_to_sales_table
        )

    def open_refund_dialog(self):
        """Open Refund panel."""
        self.dialog_wrapper.open_dialog_scanner_blocked(
            launch_refund_dialog,
            dialog_key='refund',
        )

    def open_vendor_dialog(self):
        """Open Vendor panel."""
        self.dialog_wrapper.open_dialog_scanner_blocked(
            launch_vendor_dialog,
            dialog_key='vendor',
        )

    # Open the hold sales dialog for active transactions.
    def launch_hold_sales_dialog(self):
        """Open On Hold panel."""
        from modules.ui_utils.ui_feedback import show_temp_status

        if not self._require_sales_table_ready():
            return

        if self._is_hold_loaded_in_cart():
            sb = getattr(self, 'statusbar', None)
            if sb:
                show_temp_status(sb, "On Hold Receipt loaded. Hold Sales disabled.", config.MAIN_STATUS_DURATION_MS)
            return

        if not self._can_launch_hold_sales_dialog():
            sb = getattr(self, 'statusbar', None)
            if sb:
                show_temp_status(sb, "No active sale to place on hold.", config.MAIN_STATUS_DURATION_MS)
            return

        self.dialog_wrapper.open_dialog_scanner_blocked(
            launch_hold_sales_dialog,
            dialog_key='hold_sales',
            on_finish=self._on_hold_sales_completed,
        )

    def _on_hold_sales_completed(self) -> None:
        dlg = getattr(self.dialog_wrapper, '_last_dialog', None)
        if dlg is None or not getattr(dlg, 'held_receipt_no', None):
            return

        self._reset_receipt_context()
        self._update_customer_display_from_sales()

        display = getattr(self, 'customer_display', None)
        if display is not None:
            try:
                display.show_hold_result_message(duration_ms=3000)
            except Exception:
                pass

    # Display the view hold panel when no sale is running.
    def open_viewhold_panel(self):
        """Open View Hold panel."""
        from modules.ui_utils.ui_feedback import show_temp_status

        if not self._require_sales_table_ready():
            return

        if self._is_hold_loaded_in_cart():
            sb = getattr(self, 'statusbar', None)
            if sb:
                show_temp_status(sb, "On Hold Receipt loaded. View Holds disabled.", config.MAIN_STATUS_DURATION_MS)
            return

        sales_table = getattr(self, 'sales_table', None)
        ctx = getattr(self, 'receipt_context', {}) or {}

        # Allow view-hold only when no active sale rows and no active receipt id
        if sales_table is None or sales_table.rowCount() > 0 or ctx.get('active_receipt_id') is not None:
            sb = getattr(self, 'statusbar', None)
            if sb:
                show_temp_status(sb, "Sales in progress. View Holds disabled.", config.MAIN_STATUS_DURATION_MS)
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
                    show_temp_status(sb, "Clear payment before viewing holds.", config.MAIN_STATUS_DURATION_MS)
                return

        self.dialog_wrapper.open_dialog_scanner_blocked(launch_viewhold_dialog, dialog_key='view_hold')

    def _is_hold_loaded_in_cart(self) -> bool:
        """True when the current cart originated from a loaded hold receipt."""
        ctx = getattr(self, 'receipt_context', {}) or {}
        return ctx.get('source') == 'HOLD_LOADED'

    # Prompt clear cart dialog only when a sale exists.
    def open_clearcart_dialog(self):
        """Open Clear Cart confirmation dialog, only if there is an active sale."""
        from modules.table_ui.table_operations import is_transaction_active
        from modules.ui_utils.ui_feedback import show_temp_status

        if not self._require_sales_table_ready():
            return

        sales_table = getattr(self, 'sales_table', None)
        if not is_transaction_active(sales_table):
            sb = getattr(self, 'statusbar', None)
            if sb:
                show_temp_status(sb, "Cart is empty.", config.MAIN_STATUS_DURATION_MS)
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

    def _init_customer_display(self) -> None:
        self.customer_display = None
        if not bool(getattr(config, 'CUSTOMER_DISPLAY_ENABLED', True)):
            return
        try:
            self.customer_display = CustomerDisplayWindow(self)
        except Exception as exc:
            try:
                from modules.ui_utils.error_logger import log_error_message
                log_error_message(f"Customer display init failed: {exc}")
            except Exception:
                pass

    def _update_customer_display_from_sales(self, state: str | None = None) -> None:
        display = getattr(self, 'customer_display', None)
        if display is None:
            return
        sales_table = getattr(self, 'sales_table', None)
        if sales_table is None:
            display.set_mode_full_idle()
            display.show_idle()
            return

        try:
            rows = get_sales_data(sales_table)
        except Exception:
            rows = []

        if rows:
            display.set_mode_split()
        else:
            display.set_mode_full_idle()

        items = []
        total = 0.0
        for row in rows:
            qty = float(row.get('quantity') or 0.0)
            name = str(row.get('product_name') or row.get('product') or '')
            price = float(row.get('unit_price') or 0.0)
            line_total = qty * price
            total += line_total
            items.append({
                'quantity': qty,
                'description': name,
                'amount': line_total,
                'unit': row.get('unit') if isinstance(row, dict) else None,
            })

        # Display returns to idle if no rows and state is not payment
        if not rows and state not in (display.STATE_PAYMENT,):
            display.show_idle()
            return

        payload = {
            # Active sales default to the payment QR page in the right frame.
            'state': state or (display.STATE_PAYMENT if rows else display.STATE_IDLE),
            'items': items,
            'total': total,
        }
        display.update_transaction(payload)

    def _reset_receipt_context(self) -> None:
        # Safety invariant: context reset should only happen after clearing the cart.
        # This is logging-only (no behavior change).
        try:
            sales_table = getattr(self, 'sales_table', None)
            has_rows = sales_table is not None and int(sales_table.rowCount()) > 0
        except Exception:
            has_rows = False
        if has_rows:
            try:
                from modules.ui_utils.error_logger import log_error_message
                log_error_message(
                    "WARNING: _reset_receipt_context() called while sales_table has rows; "
                    "expected clear cart/payment reset first."
                )
            except Exception:
                pass

        ctx = self.receipt_context
        ctx['active_receipt_id'] = None
        ctx['source'] = 'ACTIVE_SALE'
        ctx['status'] = 'NONE'
        self._apply_hold_loaded_sales_lock(False)
        self._refresh_sales_label_from_context()

    def _refresh_sales_label_from_context(self) -> None:
        """Update the SalesFrame header label based on current ReceiptContext."""
        try:
            ctx = getattr(self, 'receipt_context', {}) or {}
            source = str(ctx.get('source') or '').strip()
        except Exception:
            source = ''

        if source == 'HOLD_LOADED':
            text = 'On Hold receipt loaded.'
        else:
            # Default for ACTIVE sale mode (includes legacy values like "Sales").
            text = 'Sales'

        self._set_sales_label_text(text)

    def _set_sales_label_text(self, text: str) -> None:
        """Set the text of the sales frame's `salesLabel` if present."""
        label = None
        try:
            frame = getattr(self, 'sales_frame_controller', None)
            if frame is not None and getattr(frame, 'widget', None) is not None:
                label = frame.widget.findChild(QLabel, 'salesLabel')
        except Exception:
            label = None

        if label is None:
            try:
                label = self.findChild(QLabel, 'salesLabel')
            except Exception:
                label = None

        if label is not None:
            try:
                label.setText(text)
            except Exception:
                pass

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
        focus_payment = True
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            fw = app.focusWidget() if app is not None else None
            if fw is not None and getattr(fw, 'objectName', lambda: '')() == 'qtyInput':
                focus_payment = False
        except Exception:
            pass
        panel = getattr(self, 'payment_panel_controller', None)
        if panel is not None:
            panel.set_payment_default(total, focus=focus_payment)
        self._update_customer_display_from_sales()

    def _on_qty_commit_total_changed(self, total: float) -> None:
        panel = getattr(self, 'payment_panel_controller', None)
        if panel is not None:
            panel.set_payment_default(total, focus=True)
        self._update_customer_display_from_sales()

    # Update receipt context when a held sale is loaded.
    def _on_view_hold_loaded(self, receipt_id: int, total: float) -> None:
        ctx = self.receipt_context
        ctx['active_receipt_id'] = receipt_id
        ctx['source'] = 'HOLD_LOADED'
        ctx['status'] = 'UNPAID'
        self._apply_hold_loaded_sales_lock(True)
        self._refresh_sales_label_from_context()
        self._update_customer_display_from_sales()

    def _apply_hold_loaded_sales_lock(self, locked: bool) -> None:
        """Lock qty editing in the sales table when a hold receipt is loaded.

        App design rule:
        - ReceiptContext is reset back to ACTIVE_SALE only after the sales table is cleared.
        - Therefore unlocking is a no-op (there are no qty editors to restore).
        """
        if not locked:
            return

        try:
            from PyQt5.QtCore import Qt
            from PyQt5.QtWidgets import QLineEdit
        except Exception:
            return

        table = getattr(self, 'sales_table', None)
        if table is None:
            return

        try:
            row_count = int(table.rowCount())
        except Exception:
            row_count = 0

        for r in range(row_count):
            try:
                qty_container = table.cellWidget(r, 2)
                if qty_container is None:
                    continue
                editor = qty_container.findChild(QLineEdit, 'qtyInput')
                if editor is None:
                    continue
                editor.setReadOnly(True)
                editor.setFocusPolicy(Qt.NoFocus)
            except Exception:
                continue

    # Process payment requests from the payment panel.
    def _on_payment_requested(self, payment_split: dict) -> None:
        if not self._require_sales_table_ready():
            return
        display = getattr(self, 'customer_display', None)
        if display is not None:
            display.hide_payment_result_overlay()
        
        # Store current payment total for use in success handler
        try:
            self._current_payment_total = float(payment_split.get('total', 0.0) or 0.0)
        except Exception:
            self._current_payment_total = 0.0
        
        if display is not None:
            display.show_payment_result(total=self._current_payment_total)
        if self.pay_current_receipt(payment_split):
            panel = getattr(self, 'payment_panel_controller', None)
            if panel is not None:
                panel.notify_payment_success()
        elif display is not None:
            try:
                display.keep_payment_result_overlay_visible()
            except Exception:
                pass

    # Clear state after successful payment completion.
    def _on_payment_success(self) -> None:
        self._clear_sales_table_core()
        panel = getattr(self, 'payment_panel_controller', None)
        if panel is not None:
            panel.clear_payment_frame()
        self._reset_receipt_context()
        sales_frame = getattr(self, 'sales_frame_controller', None)
        if sales_frame is not None and sales_frame.widget is not None:
            vegetable_entry_btn = sales_frame.widget.findChild(QPushButton, 'vegEntryBtn')
            if vegetable_entry_btn is not None:
                QTimer.singleShot(
                    0,
                    lambda: vegetable_entry_btn.setFocus(Qt.OtherFocusReason),
                )

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
            code = by_name.get(name.lower(), '')
            cat = ''
            try:
                if code and (PRODUCT_CACHE or {}).get(code):
                    rec = (PRODUCT_CACHE or {}).get(code)
                    if rec and len(rec) > 3:
                        cat = rec[3] or ''
            except Exception:
                cat = ''
            out.append({
                'product_code': code,
                'name': name,
                'category': cat,
                'quantity': qty,
                'unit': str(row.get('unit') or ''),
                'unit_price': unit_price,
                'price': unit_price,
                'line_total': round_money(qty * unit_price),
            })
        return out

    def _should_open_cash_drawer(self, payment_split: dict) -> bool:
        try:
            cash = float(payment_split.get('cash', 0.0) or 0.0)
        except Exception:
            cash = 0.0
        return cash > 0

    def _open_cash_drawer_if_needed(self, payment_split: dict) -> None:
        if not bool(getattr(config, 'ENABLE_CASH_DRAWER', True)):
            return
        if not self._should_open_cash_drawer(payment_split):
            return

        try:
            from modules.devices import printer_and_drawer as device_printer
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
                    duration=config.MAIN_STATUS_ERROR_DURATION_MS,
                )
                try:
                    from modules.ui_utils.error_logger import log_error_message
                    log_error_message("Cash drawer open failed (helper returned False).")
                except Exception:
                    pass
        except Exception as e:
            report_to_statusbar(
                self,
                "Cash drawer error.",
                is_error=True,
                duration=config.MAIN_STATUS_ERROR_DURATION_MS,
            )
            try:
                from modules.ui_utils.error_logger import log_error_message
                log_error_message(f"Cash drawer helper call failed: {e}")
            except Exception:
                pass

    def _set_payment_failure_lock(self, locked: bool) -> None:
        self._payment_failure_lock_active = bool(locked)
        panel = getattr(self, 'payment_panel_controller', None)
        if panel is not None:
            try:
                panel.set_pay_error_locked(self._payment_failure_lock_active)
            except Exception:
                pass
        if self._payment_failure_lock_active:
            self._show_payment_failure_status()
        else:
            self._clear_payment_failure_status()

    def _reset_payment_failure_retry_state(self) -> None:
        self._payment_db_failure_count = 0
        self._set_payment_failure_lock(False)

    def _show_payment_failure_status(self) -> None:
        sb = getattr(self, 'statusbar', None)
        if sb is None:
            return
        try:
            sb.setStyleSheet("color: red;")
            sb.showMessage(self._payment_failure_status_message, config.PERSISTENT_DURATION_MS)
        except Exception:
            pass

    def _clear_payment_failure_status(self) -> None:
        sb = getattr(self, 'statusbar', None)
        if sb is None:
            return
        try:
            if sb.currentMessage() == self._payment_failure_status_message:
                sb.clearMessage()
        except Exception:
            pass

    def _on_statusbar_message_changed(self, message: str) -> None:
        if not bool(getattr(self, '_payment_failure_lock_active', False)):
            return
        if message == self._payment_failure_status_message:
            return
        if self._payment_failure_status_reapply_pending:
            return
        self._payment_failure_status_reapply_pending = True
        QTimer.singleShot(0, self._restore_payment_failure_status_if_needed)

    def _restore_payment_failure_status_if_needed(self) -> None:
        self._payment_failure_status_reapply_pending = False
        if bool(getattr(self, '_payment_failure_lock_active', False)):
            self._show_payment_failure_status()

    def _record_payment_db_failure(self) -> None:
        self._payment_db_failure_count += 1
        if self._payment_db_failure_count >= self._payment_db_failure_limit:
            self._set_payment_failure_lock(True)
            return

        report_to_statusbar(
            self,
            (
                "Payment failed to update DB. Please retry. "
                f"({self._payment_db_failure_count}/{self._payment_db_failure_limit})"
            ),
            is_error=True,
            duration=config.MAIN_STATUS_LONG_DURATION_MS,
        )

    def print_payment_failure_receipt(self, payment_split: dict) -> None:
        from modules.payment.recovery_receipt import print_payment_failure_receipt
        print_payment_failure_receipt(self, payment_split)

    def pay_current_receipt(self, payment_split: dict) -> bool:
        """Process current payment via PaidSaleCommitter atomic service."""
        if not self._require_sales_table_ready():
            return False
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

        # Ensure payment panel's validation agrees with processing rules.
        try:
            if panel is not None and not panel._is_payment_valid():
                report_to_statusbar(self, "Payment invalid: please correct allocation/tender.", is_error=True, duration=config.MAIN_STATUS_ERROR_DURATION_MS)
                return False
        except Exception:
            # If validation routine is unavailable, continue and let commit handle failures.
            pass

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
            cid = getattr(self, 'current_user_id', None)
            if cid is None:
                report_to_statusbar(self, "No logged-in user. Please login.", is_error=True, duration=config.MAIN_STATUS_ERROR_DURATION_MS)
                return False
            committer = PaidSaleCommitter()
            receipt_no = committer.commit_paid_sale(
                active_receipt_id=active_receipt_id,
                sales_items=sales_items,
                payment_rows=payment_rows,
                total=total,
                cashier_id=int(cid),
            )

            self.receipt_context['last_receipt_no'] = str(receipt_no)
            self._reset_payment_failure_retry_state()

            self._open_cash_drawer_if_needed(payment_split)

            report_to_statusbar(
                self,
                f"Payment completed: {receipt_no}",
                is_error=False,
                duration=config.MAIN_STATUS_EXTENDED_DURATION_MS,
            )
            return True

        except Exception as e:
            report_exception(
                self,
                "Payment processing",
                e,
                user_message="Payment failed to update DB. Please retry.",
                duration=config.MAIN_STATUS_LONG_DURATION_MS,
            )
            self._record_payment_db_failure()
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
        # Hide payment result overlay when items are being added
        display = getattr(self, 'customer_display', None)
        if display is not None:
            display.hide_payment_result_overlay()
        
        if not hasattr(self, 'sales_table'):
            return

        try:
            from modules.table_ui.table_operations import set_table_rows
            from modules.domain.unit_helpers import canonicalize_unit

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

            existing_rows = []
            for row in get_sales_data(self.sales_table):
                row_data = dict(row)
                row_data['product'] = row_data.get('product_name', row_data.get('product', ''))
                row_data['unit'] = canonicalize_unit(row_data.get('unit', ''))
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
            try:
                set_table_rows(self.sales_table, existing_rows)
            except Exception as exc:
                self._mark_sales_table_unavailable(
                    exc,
                    where="Populate sales table from entry dialog",
                )
                return
            self._update_customer_display_from_sales()
        except Exception:
            try:
                import traceback
                from modules.ui_utils.error_logger import log_error_message
                log_error_message(traceback.format_exc())
            except Exception:
                pass

    # Clear table rows and reset payment panel after cancel.
    def _clear_sales_table_core(self, update_display: bool = True) -> None:
        """Clear sales table rows and recompute total without dialog checks."""
        if not hasattr(self, 'sales_table'):
            return
        try:
            self.sales_table.setRowCount(0)
            from modules.table_ui import recompute_total
            recompute_total(self.sales_table)
            if update_display:
                display = getattr(self, 'customer_display', None)
                if display is not None:
                    display.show_idle()
        except Exception as e:
            try:
                from modules.ui_utils.error_logger import log_error_message
                log_error_message(f"Failed to clear sales table core: {e}")
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

            display = getattr(self, 'customer_display', None)
            if display is not None:
                display.hide_payment_result_overlay()

            payment_failure_lock_active = bool(getattr(self, '_payment_failure_lock_active', False))
            panel = getattr(self, 'payment_panel_controller', None)
            cash_allocated = 0.0
            if payment_failure_lock_active and panel is not None:
                try:
                    cash_allocated = float(panel.get_allocated_cash_amount() or 0.0)
                except Exception:
                    cash_allocated = 0.0

            if payment_failure_lock_active:
                self._reset_payment_failure_retry_state()

            if payment_failure_lock_active and cash_allocated > 0:
                self._open_cash_drawer_if_needed({'cash': cash_allocated})

            self._clear_sales_table_core(update_display=False)
            if panel is not None:
                panel.clear_payment_frame()

            self._reset_receipt_context()
            self._update_customer_display_from_sales()
        except Exception as e:
            try:
                import traceback
                from modules.ui_utils.error_logger import log_error_message
                log_error_message(f"Failed to clear sales table: {e}\n{traceback.format_exc()}")
            except Exception:
                pass

    # Empty the sales table without dialog confirmation.
    def _clear_sales_table_force(self):
        """Clear sales table without dialog checks (used after payment success)."""
        try:
            self._clear_sales_table_core()
        except Exception as e:
            try:
                from modules.ui_utils.error_logger import log_error_message
                log_error_message(f"Failed to force-clear sales table: {e}")
            except Exception:
                pass


# Bootstrap the QApplication and launch the main window.
def main():
    def _install_qt_message_handler() -> None:
        try:
            from modules.ui_utils.error_logger import log_error_message
        except Exception:
            log_error_message = None

        def _handler(msg_type, context, message):
            if log_error_message is None:
                return
            try:
                mt = int(msg_type)
            except Exception:
                mt = -1

            # Qt message types: Debug=0, Warning=1, Critical=2, Fatal=3, Info=4
            if mt in (1, 2, 3):
                # Suppress non-focusable fullscreen window activation warnings.
                if "requestActivate()" in message and "WindowDoesNotAcceptFocus" in message:
                    return
                # Suppress noisy Qt teardown messages seen on Windows when the
                # event dispatcher wakes or stops timers after a handle is gone.
                if "QEventDispatcherWin32::wakeUp: Failed to post a message" in message:
                    return
                if "QObject::~QObject: Timers cannot be stopped from another thread" in message:
                    return
                try:
                    log_error_message(f"Qt: {message}")
                except Exception:
                    pass

        try:
            qInstallMessageHandler(_handler)
        except Exception:
            pass

    _install_qt_message_handler()

    app = QApplication(sys.argv)
    load_qss(app)

    cache_load_failed = False

    try:
        from modules.db_operation.sqlite_runtime import get_db_path
        get_db_path()
    except FileNotFoundError as exc:
        try:
            from modules.ui_utils.error_logger import log_error_message
            log_error_message(f"Startup database validation failed: {exc}")
        except Exception:
            pass
        QMessageBox.critical(
            None,
            'Database Not Found',
            f'{exc}\n\nThe application will close.',
        )
        return 1

    # Load product cache once at startup so name/code lookups and completers
    # can rely on in-memory PRODUCT_CACHE during runtime.
    try:
        from modules.db_operation import load_product_cache
        load_product_cache()
    except Exception as e:
        cache_load_failed = True
        try:
            from modules.ui_utils.error_logger import log_error_message
            log_error_message(f"Failed to load PRODUCT_CACHE: {e}")
        except Exception:
            pass

    # Build main window first so BarcodeManager event filter is installed
    # before opening login; this prevents scanner text leakage into login inputs.
    window = MainLoader()

    from modules.runtime.trial import is_trial_expired, trial_expired_message
    from modules.sales.login import launch_login_dialog
    # Respect config.LOGIN_ON: set to False in `config.py` to skip login.
    try:
        if not bool(getattr(config, 'LOGIN_ON', True)):
            if is_trial_expired():
                QMessageBox.warning(None, 'Trial Expired', trial_expired_message())
                login_user = None
            else:
                login_user = {
                    'user_id': int(getattr(config, 'AUTO_LOGIN_UID', 1)),
                    'username': str(getattr(config, 'AUTO_LOGIN_USERNAME', 'dev') or 'dev'),
                    'is_admin': bool(getattr(config, 'AUTO_LOGIN_IS_ADMIN', True)),
                }
        else:
            window.dialog_wrapper._show_overlay()
            window.dialog_wrapper._block_scanner()
            login_user = launch_login_dialog(None, return_user=True)
            window.dialog_wrapper._hide_overlay()
            window.dialog_wrapper._unblock_scanner()
    except Exception:
        # Fallback to normal login on any unexpected error reading config
        window.dialog_wrapper._show_overlay()
        window.dialog_wrapper._block_scanner()
        login_user = launch_login_dialog(None, return_user=True)
        window.dialog_wrapper._hide_overlay()
        window.dialog_wrapper._unblock_scanner()

    if login_user is not None:
        try:
            uid = login_user.get('user_id')
            window.current_user_id = int(uid) if uid is not None else None
        except Exception:
            window.current_user_id = None
        window.current_username = str(login_user.get('username') or '')
        window.current_is_admin = bool(login_user.get('is_admin'))
        try:
            window.status_footer.set_username(window.current_username)
        except Exception:
            pass
        # Show the main window first so any subsequent dialogs use the
        # dialog wrapper overlay (modal over main window) like normal UI flows.
        try:
            window.showMaximized()
            window.raise_()
            window.activateWindow()
        except Exception:
            pass

        # Enforce persistent must-change-password flag: if set for this user,
        # open the admin dialog in forced-change mode once the window geometry settles.
        try:
            from modules.db_operation.users_repo import get_must_change_password
            if window.current_user_id is not None and get_must_change_password(int(window.current_user_id)):
                # Only allow admin users to perform the forced update via admin dialog.
                if bool(window.current_is_admin):
                    def _open_forced_admin():
                        window.dialog_wrapper.open_dialog_scanner_blocked(
                            launch_admin_dialog,
                            dialog_key='admin_menu',
                            user_id=window.current_user_id,
                            is_admin=True,
                            force_change=True,
                        )

                    # Defer dialog open to ensure main window has final size,
                    # so dialog ratio sizing is accurate.
                    QTimer.singleShot(150, _open_forced_admin)
        except Exception:
            pass
        # If cache load failed earlier, surface it once the status bar exists.
        if cache_load_failed:
            report_to_statusbar(
                window,
                'Error: Failed to load product list (search may be limited)',
                is_error=True,
                duration=config.MAIN_STATUS_LONG_DURATION_MS,
            )
        sys.exit(app.exec_())
    else:
        sys.exit(0)


if __name__ == '__main__':
    sys.exit(main())
