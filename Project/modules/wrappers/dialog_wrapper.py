"""Unified dialog wrapper for all modal dialogs."""
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import QTimer
from modules.ui_utils import ui_feedback


class DialogWrapper:
    """Manages dialog execution, cleanup, and post-exec callbacks."""

    # Dialog size ratios (width_ratio, height_ratio) as fraction of main window
    DIALOG_RATIOS = {
        'vegetable_entry': (0.5, 0.8),
        'manual_entry': (0.4, 0.3),
        'logout_menu': (0.25, 0.25),
        'admin_menu': (0.4, 0.3),
        'history_menu': (0.4, 0.4),
        'reports_menu': (0.7, 0.7),
        'greeting_menu': (0.3, 0.3),
        'product_menu': (0.5, 0.7),
        'vegetable_menu': (0.32, 0.7),
        'on_hold': (0.7, 0.7),
        'view_hold': (0.7, 0.7),
        'cancel_sale': (0.7, 0.7),
    }

    def __init__(self, main_window):
        """Initialize wrapper with reference to main window.
        
        Args:
            main_window: MainLoader instance (QMainWindow).
        """
        self.main = main_window
        self._last_dialog = None  # Track last executed dialog for callbacks

    # ============ Helper Functions ============

    def _show_overlay(self):
        """Show overlay (dim background)."""
        self.main.overlay_manager.toggle_dim_overlay(True)

    def _hide_overlay(self):
        """Hide overlay."""
        self.main.overlay_manager.toggle_dim_overlay(False)

    def _block_scanner(self):
        """Block barcode scanner input during modal dialog."""
        try:
            if hasattr(self.main, 'barcode_manager'):
                self.main.barcode_manager._start_scanner_modal_block()
        except Exception:
            pass

    def _unblock_scanner(self):
        """Re-enable barcode scanner after modal dialog."""
        try:
            if hasattr(self.main, 'barcode_manager'):
                self.main.barcode_manager._end_scanner_modal_block()
        except Exception:
            pass

    def _refocus_sales_table(self):
        """Restore focus to sales table after dialog closes."""
        try:
            from PyQt5.QtCore import Qt
            table = getattr(self.main, 'sales_table', None)
            if table is not None:
                table.setFocusPolicy(Qt.StrongFocus)
                table.setFocus(Qt.OtherFocusReason)
                if table.rowCount() > 0 and table.columnCount() > 0:
                    table.setCurrentCell(0, 0)
        except Exception:
            pass

    def _restore_focus(self):
        """Restore focus to sales table and activate main window."""
        try:
            self.main.raise_()
            self.main.activateWindow()
            self._refocus_sales_table()
        except Exception:
            pass

    def _clear_scanner_override(self):
        """Clear barcode override set by product menu dialog."""
        try:
            bm = getattr(self.main, 'barcode_manager', None)
            if bm is None:
                return
            if hasattr(bm, 'clear_barcode_override'):
                bm.clear_barcode_override()
            else:
                bm._barcodeOverride = None
        except Exception:
            pass

    def _setup_dialog_geometry(self, dlg, width_ratio=0.5, height_ratio=0.5):
        """Setup dialog size and position on main window based on ratios.
        
        Dialog size is calculated as a percentage of the main window dimensions,
        with minimumSize from .ui file enforced as safety floor.
        Dialog is then centered on the main window.
        
        Args:
            dlg: QDialog to size and position.
            width_ratio: Desired width as fraction of main window (0.0-1.0). Default 0.5 (50%).
            height_ratio: Desired height as fraction of main window (0.0-1.0). Default 0.5 (50%).
        """
        mw = self.main.frameGeometry().width()
        mh = self.main.frameGeometry().height()
        mx = self.main.frameGeometry().x()
        my = self.main.frameGeometry().y()
        
        # Calculate target size based on ratios
        target_width = int(mw * width_ratio)
        target_height = int(mh * height_ratio)
        
        # Get minimum size from .ui file (safety floor)
        min_w = dlg.minimumWidth()
        min_h = dlg.minimumHeight()
        
        # Enforce minimum size constraint
        final_width = max(min_w, target_width)
        final_height = max(min_h, target_height)
        
        # Apply calculated size
        dlg.resize(final_width, final_height)
        
        dw, dh = dlg.width(), dlg.height()
        
        # Calculate centered position
        dialog_x = mx + (mw - dw) // 2
        dialog_y = my + (mh - dh) // 2
        
        # Clamp to keep dialog within window bounds (safety for oversized dialogs)
        dialog_x = max(mx, min(dialog_x, mx + mw - dw))
        dialog_y = max(my, min(dialog_y, my + mh - dh))
        
        dlg.move(dialog_x, dialog_y)

    def _create_cleanup(self, on_finish=None):
        """Factory: Create cleanup callback with optional post-finish logic.
        
        Args:
            on_finish: Optional callable to invoke after cleanup (e.g., logout).
        
        Returns:
            Cleanup function to connect to dlg.finished signal.
        """
        def _cleanup(result):
            self._hide_overlay()
            self._unblock_scanner()
            self._restore_focus()
            # Only call on_finish if dialog was accepted (e.g., OK pressed)
            if on_finish and result == QDialog.Accepted:
                on_finish()
        return _cleanup

    # ============ Main Wrapper Functions ============

    def open_dialog_scanner_blocked(
        self,
        dialog_func,
        dialog_key=None,
        on_finish=None,
        *args,
        **kwargs
    ):
        """Unified wrapper for dialogs with scanner input blocked.
        
        Dialog size is calculated based on ratios of main window dimensions,
        with minimumSize from .ui file enforced as safety floor.
        
        Args:
            dialog_func: Function that returns QDialog instance.
            dialog_key: Optional key to lookup ratios in DIALOG_RATIOS. If None, uses defaults (0.5, 0.5).
            on_finish: Optional callback after dialog closes (e.g., _perform_logout).
            *args, **kwargs: Arguments to pass to dialog_func.
        """
        self._show_overlay()
        self._block_scanner()

        try:
            dlg = dialog_func(self.main, *args, **kwargs)

            if not isinstance(dlg, QDialog):
                raise ValueError(f"Expected QDialog, got {type(dlg)}")

            # Get ratios from mapping, or use defaults if key not found
            if dialog_key and dialog_key in self.DIALOG_RATIOS:
                width_ratio, height_ratio = self.DIALOG_RATIOS[dialog_key]
            else:
                width_ratio, height_ratio = 0.5, 0.5

            self._setup_dialog_geometry(dlg, width_ratio, height_ratio)
            dlg.finished.connect(self._create_cleanup(on_finish))
            self._last_dialog = dlg  # Store reference for callbacks
            #dlg.exec_()
            
            result = dlg.exec_()

            # Check if the dialog set a message for the main status bar
            msg = getattr(dlg, 'main_status_msg', None)

            if msg:
                # Use our new feedback helper
                is_error = (result == QDialog.Rejected)
                ui_feedback.show_main_status(self.main, msg, is_error=is_error)

        except Exception as e:
            self._hide_overlay()
            self._unblock_scanner()
            print(f'Dialog failed: {e}')

    def open_dialog_scanner_enabled(self, dialog_func, dialog_key=None, **kwargs):
        """Wrapper for dialogs that allow scanner input (e.g., product_menu).
        
        Product dialog:
        - Does NOT block scanner (allows barcode input in product code field)
        - Resets barcode override on close
        - Uses timer-deferred focus restoration
        - Dialog size calculated based on ratios of main window dimensions
        
        Args:
            dialog_func: Function that returns QDialog (product dialog).
            dialog_key: Optional key to lookup ratios in DIALOG_RATIOS. If None, uses defaults (0.5, 0.5).
            **kwargs: Arguments to pass to dialog_func.
        """
        self._show_overlay()
        # Note: scanner is NOT blocked for product menu

        try:
            dlg = dialog_func(self.main, **kwargs)

            if not isinstance(dlg, QDialog):
                raise ValueError(f"Expected QDialog, got {type(dlg)}")

            # Get ratios from mapping, or use defaults if key not found
            if dialog_key and dialog_key in self.DIALOG_RATIOS:
                width_ratio, height_ratio = self.DIALOG_RATIOS[dialog_key]
            else:
                width_ratio, height_ratio = 0.5, 0.5

            self._setup_dialog_geometry(dlg, width_ratio, height_ratio)

            def _product_cleanup(_):
                self._hide_overlay()
                self._clear_scanner_override()
                # Timer-deferred focus restoration (handles overlay hide event processing)
                def _restore():
                    self._restore_focus()
                QTimer.singleShot(10, _restore)

            dlg.finished.connect(_product_cleanup)
            dlg.exec_()

        except Exception as e:
            self._hide_overlay()
            print(f'Product dialog failed: {e}')
