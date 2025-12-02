import os
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QWidget, QTextEdit, QPlainTextEdit
from PyQt5.QtCore import Qt

def open_manual_entry_dialog(parent, message="Manual Product Entry"):
    """Open the Manual Product Entry panel as a modal dialog (controller logic)."""
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    UI_DIR = os.path.join(BASE_DIR, 'ui')
    manual_ui = os.path.join(UI_DIR, 'manual_entry.ui')
    if not os.path.exists(manual_ui):
        print('manual_entry.ui not found at', manual_ui)
        return

    # Create dimming overlay over the main window
    parent.overlay_manager.toggle_dim_overlay(True)

    # Build a modal dialog and embed the loaded UI inside
    try:
        content = uic.loadUi(manual_ui)
    except Exception as e:
        print('Failed to load manual_entry.ui:', e)
        parent.overlay_manager.toggle_dim_overlay(False)
        return

    dlg = QDialog(parent)
    dlg.setModal(True)
    dlg.setWindowTitle('Manual Entry of Product')
    # Window flags: remove min/max, keep title + close
    dlg.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
    # Fixed size at 60% of main window, centered
    try:
        mw = parent.frameGeometry().width()
        mh = parent.frameGeometry().height()
        dw = max(400, int(mw * 0.6))
        dh = max(300, int(mh * 0.6))
        dlg.setFixedSize(dw, dh)
        # Center relative to main window
        mx = parent.frameGeometry().x()
        my = parent.frameGeometry().y()
        dlg.move(mx + (mw - dw) // 2, my + (mh - dh) // 2)
    except Exception:
        pass

    # Install content into dialog
    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(content)

    # Set the message in the QTextEdit or QPlainTextEdit widget
    try:
        text_edit = content.findChild(QWidget, 'manualText')
        if isinstance(text_edit, (QTextEdit, QPlainTextEdit)):
            text_edit.setPlainText(str(message))
            try:
                text_edit.setReadOnly(True)
            except Exception:
                pass
    except Exception as e:
        print('Failed to set manual text:', e)

    # Mark that a generic modal is open to block scanner routing
    try:
        if hasattr(parent, 'barcode_manager'):
            parent.barcode_manager._start_scanner_modal_block()
    except Exception:
        pass

    # Ensure overlay hides and focus returns when dialog closes
    def _cleanup_overlay(_code):
        parent.overlay_manager.toggle_dim_overlay(False)
        # Bring main window back to front
        try:
            parent.raise_()
            parent.activateWindow()
        except Exception:
            pass
        # Unblock scanner and restore focus to sales table
        try:
            if hasattr(parent, 'barcode_manager'):
                parent.barcode_manager._end_scanner_modal_block()
        except Exception:
            pass
        try:
            parent._refocus_sales_table()
        except Exception:
            pass

    dlg.finished.connect(_cleanup_overlay)

    # Execute modally
    dlg.exec_()