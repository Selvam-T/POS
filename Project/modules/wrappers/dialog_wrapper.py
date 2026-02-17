"""Unified dialog wrapper for all modal dialogs."""
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import QTimer
from modules.ui_utils.dialog_utils import report_to_statusbar


class DialogWrapper:
    """Manages dialog execution, cleanup, and post-exec callbacks."""

    # Dialog size ratios are now imported from config.py
    from config import DIALOG_RATIOS

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
            # Fail-safe: never allow a dialog-installed barcode override to leak
            # back into the main window after the dialog closes.
            self._clear_scanner_override()
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
        Handles None return (e.g., max rows reached) gracefully.
        """
        self._show_overlay()
        self._block_scanner()

        try:
            dlg = dialog_func(self.main, *args, **kwargs)

            if dlg is None:
                # Dialog intentionally not shown (e.g., max rows reached)
                self._hide_overlay()
                self._unblock_scanner()
                self._clear_scanner_override()
                # If a controller deferred a status message (e.g., UI missing),
                # surface it now that the overlay has been removed.
                try:
                    msg = getattr(self.main, '_pending_main_status_msg', None)
                    if msg:
                        is_error = bool(getattr(self.main, '_pending_main_status_is_error', True))
                        duration = getattr(self.main, '_pending_main_status_duration', 6000)
                        report_to_statusbar(
                            self.main,
                            msg,
                            is_error=is_error,
                            duration=int(duration) if duration is not None else 6000,
                        )
                except Exception:
                    pass
                finally:
                    try:
                        if hasattr(self.main, '_pending_main_status_msg'):
                            delattr(self.main, '_pending_main_status_msg')
                        if hasattr(self.main, '_pending_main_status_is_error'):
                            delattr(self.main, '_pending_main_status_is_error')
                        if hasattr(self.main, '_pending_main_status_duration'):
                            delattr(self.main, '_pending_main_status_duration')
                    except Exception:
                        pass
                return

            if not isinstance(dlg, QDialog):
                raise ValueError(f"Expected QDialog, got {type(dlg)}")

            # Get ratios from mapping, or use defaults if key not found
            if dialog_key and dialog_key in self.DIALOG_RATIOS:
                width_ratio, height_ratio = self.DIALOG_RATIOS[dialog_key]
            else:
                width_ratio, height_ratio = 0.5, 0.5

            # Optional convention: dialogs may provide a barcode override handler.
            # Wrapper installs it (best-effort) and cleanup always clears it.
            try:
                handler = getattr(dlg, 'barcode_override_handler', None)
                if callable(handler):
                    bm = getattr(self.main, 'barcode_manager', None)
                    if bm is not None and hasattr(bm, 'set_barcode_override'):
                        bm.set_barcode_override(handler)
            except Exception:
                pass

            self._setup_dialog_geometry(dlg, width_ratio, height_ratio)
            dlg.finished.connect(self._create_cleanup(on_finish))
            self._last_dialog = dlg  # Store reference for callbacks
            result = dlg.exec_()

            # Check if the dialog set a message for the main status bar
            msg = getattr(dlg, 'main_status_msg', None)

            if msg:
                # Allow dialogs to override severity/duration (e.g., Cancel as non-error).
                is_error = getattr(dlg, 'main_status_is_error', (result == QDialog.Rejected))
                duration = getattr(dlg, 'main_status_duration', None)
                try:
                    report_to_statusbar(
                        self.main,
                        msg,
                        is_error=bool(is_error),
                        duration=int(duration) if duration is not None else 4000,
                    )
                except Exception:
                    report_to_statusbar(self.main, msg, is_error=bool(is_error), duration=4000)

        except Exception as e:
            self._hide_overlay()
            self._unblock_scanner()
            self._clear_scanner_override()
            try:
                import traceback
                from modules.ui_utils.error_logger import log_error
                log_error(f"Dialog failed: {e}\n{traceback.format_exc()}")
            except Exception:
                pass

            # Best-effort user hint (after cleanup so it doesn't show under a modal overlay).
            try:
                report_to_statusbar(
                    self.main,
                    'Error: Dialog failed (see error.log)',
                    is_error=True,
                    duration=6000,
                )
            except Exception:
                pass
