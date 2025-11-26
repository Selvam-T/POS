"""
Shared dialog utilities for menu dialogs.
"""
from PyQt5.QtWidgets import QDialog

def center_dialog_relative_to(dlg: QDialog, host) -> None:
    """Center dlg relative to host window."""
    try:
        mw = host.frameGeometry().width(); mh = host.frameGeometry().height()
        mx = host.frameGeometry().x();     my = host.frameGeometry().y()
        dw = dlg.width();                  dh = dlg.height()
        dlg.move(mx + (mw - dw)//2, my + (mh - dh)//2)
    except Exception:
        pass
