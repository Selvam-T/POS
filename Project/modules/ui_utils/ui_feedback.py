"""
ui_feedback.py
Small UI helper utilities for consistent status label feedback across dialogs.

Usage:
    from modules.ui_utils import ui_feedback

    ui_feedback.set_status_label(lbl, "Saved", ok=True)
    ui_feedback.set_status_label(lbl, "Error: ...", ok=False)
    ui_feedback.clear_status_label(lbl)

All helpers return True/False so controllers can use the return value if desired.
"""

from PyQt5.QtWidgets import QLabel

def set_status_label(label: QLabel, message: str, ok: bool) -> bool:
    """Set status message and apply QSS styling via dynamic properties."""
    if label is None:
        return False

    label.setText(message or "")
    
    # Assign the property value defined in menu.qss
    status_value = "success" if ok else "error"
    label.setProperty("status", status_value)

    # RE-POLISH: This is required for Qt to re-apply QSS 
    # based on the new property value.
    label.style().unpolish(label)
    label.style().polish(label)
    
    return ok

def clear_status_label(label: QLabel) -> bool:
    """Clear message and reset status property."""
    if label is None:
        return False
        
    label.setText("")
    label.setProperty("status", "none")
    
    label.style().unpolish(label)
    label.style().polish(label)
    return True