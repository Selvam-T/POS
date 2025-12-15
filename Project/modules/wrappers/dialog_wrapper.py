"""Unified dialog wrapper for all modal dialogs."""
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import QTimer


class DialogWrapper:
    """Manages dialog execution, cleanup, and post-exec callbacks."""

    def __init__(self, main_window):
        """Initialize wrapper with reference to main window.
        
        Args:
            main_window: MainLoader instance (QMainWindow).
        """
        self.main = main_window

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
            if hasattr(self.main, 'barcode_manager'):
                self.main.barcode_manager._barcodeOverride = None
        except Exception:
            pass

    def _size_and_center(self, dlg, width_ratio=0.45, height_ratio=0.4):
        """Size and center dialog on main window.
        
        Args:
            dlg: QDialog to size and position.
            width_ratio: Width as fraction of main window (default 0.45).
            height_ratio: Height as fraction of main window (default 0.4).
        """
        mw, mh = self.main.frameGeometry().width(), self.main.frameGeometry().height()
        dw, dh = max(360, int(mw * width_ratio)), max(220, int(mh * height_ratio))
        dlg.setFixedSize(dw, dh)
        mx, my = self.main.frameGeometry().x(), self.main.frameGeometry().y()
        dlg.move(mx + (mw - dw) // 2, my + (mh - dh) // 2)

    def _create_cleanup(self, on_finish=None):
        """Factory: Create cleanup callback with optional post-finish logic.
        
        Args:
            on_finish: Optional callable to invoke after cleanup (e.g., logout).
        
        Returns:
            Cleanup function to connect to dlg.finished signal.
        """
        def _cleanup(_):
            self._hide_overlay()
            self._unblock_scanner()
            self._restore_focus()
            if on_finish:
                on_finish()
        return _cleanup

    # ============ Main Wrapper Functions ============

    def open_standard_dialog(
        self,
        dialog_func,
        width_ratio=0.45,
        height_ratio=0.4,
        on_finish=None,
        *args,
        **kwargs
    ):
        """Unified wrapper for standard dialogs (Case A pattern).
        
        All dialogs return QDialog; wrapper handles exec_(), sizing, and cleanup.
        
        Args:
            dialog_func: Function that returns QDialog instance.
            width_ratio: Dialog width as fraction of main window.
            height_ratio: Dialog height as fraction of main window.
            on_finish: Optional callback after dialog closes (e.g., _perform_logout).
            *args, **kwargs: Arguments to pass to dialog_func.
        """
        self._show_overlay()
        self._block_scanner()

        try:
            dlg = dialog_func(self.main, *args, **kwargs)

            if not isinstance(dlg, QDialog):
                raise ValueError(f"Expected QDialog, got {type(dlg)}")

            self._size_and_center(dlg, width_ratio, height_ratio)
            dlg.finished.connect(self._create_cleanup(on_finish))
            dlg.exec_()

        except Exception as e:
            self._hide_overlay()
            self._unblock_scanner()
            print(f'Dialog failed: {e}')

    def open_product_dialog(self, dialog_func, **kwargs):
        """Special wrapper for product_menu dialog (allows barcode input).
        
        Product dialog:
        - Does NOT block scanner (allows barcode input in product code field)
        - Resets barcode override on close
        - Uses timer-deferred focus restoration
        - Wrapper controls exec_() but dialog manages itself
        
        Args:
            dialog_func: Function that returns QDialog (product dialog).
            **kwargs: Arguments to pass to dialog_func.
        """
        self._show_overlay()
        # Note: scanner is NOT blocked for product menu

        try:
            dlg = dialog_func(self.main, **kwargs)

            if not isinstance(dlg, QDialog):
                raise ValueError(f"Expected QDialog, got {type(dlg)}")

            self._size_and_center(dlg)

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
