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
    """Set status message and apply simple red/green coloring."""
    if label is None:
        return False

    label.setText(message or "")

    # Keep styling simple and local (no global QSS required).
    # If you later switch to QSS/property-based styling, you can update this in one place.
    if ok:
        label.setStyleSheet("color: green;")
        return True

    label.setStyleSheet("color: red;")
    return False


def clear_status_label(label: QLabel) -> bool:
    """Clear message and remove inline color styling."""
    if label is None:
        return False
    label.setText("")
    label.setStyleSheet("")
    return True
