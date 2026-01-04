from PyQt5.QtWidgets import QLabel

def set_status_label(label: QLabel, message: str, ok: bool) -> bool:
    """Sets status message and triggers QSS property change."""
    if label is None:
        return False

    label.setText(message or "")
    
    # Apply the property defined in menu.qss
    status_val = "success" if ok else "error"
    label.setProperty("status", status_val)

    # Re-polish tells Qt to re-read the CSS for this specific widget
    label.style().unpolish(label)
    label.style().polish(label)
    
    return ok

def clear_status_label(label: QLabel) -> bool:
    """Clears text and resets the QSS property."""
    if label is None:
        return False
    label.setText("")
    label.setProperty("status", "none")
    label.style().unpolish(label)
    label.style().polish(label)
    return True