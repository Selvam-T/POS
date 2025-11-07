from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

from PyQt5 import uic
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QDialog, QWidget, QVBoxLayout, QLabel, QPushButton


class BaseMenuDialog(QDialog):
    """Reusable frameless dialog with a custom title bar and a content placeholder.
    Load ui/base_menu_dialog.ui and provide helpers to set title and embed content widgets.
    """

    def __init__(self, parent: Optional[QWidget] = None, title: str = "Dialog") -> None:
        super().__init__(parent)
        base_dir = Path(__file__).resolve().parents[2]  # .../POS/Project
        ui_path = base_dir / 'ui' / 'base_menu_dialog.ui'
        uic.loadUi(str(ui_path), self)

        # Window flags: frameless, dialog
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self._drag_pos: Optional[QPoint] = None

        # Cache references
        self._title_label: Optional[QLabel] = getattr(self, 'customTitle', None)
        self._close_btn: Optional[QPushButton] = getattr(self, 'customCloseBtn', None)
        self._content_container: Optional[QWidget] = getattr(self, 'contentContainer', None)
        self._content_layout: Optional[QVBoxLayout] = None
        if isinstance(self._content_container, QWidget):
            self._content_layout = self._content_container.layout()  # type: ignore[assignment]
            if not isinstance(self._content_layout, QVBoxLayout):
                # Ensure vertical layout exists
                lay = QVBoxLayout(self._content_container)
                lay.setContentsMargins(0, 0, 0, 0)
                self._content_container.setLayout(lay)
                self._content_layout = lay

        # Title and close button
        self.set_title(title)
        if isinstance(self._close_btn, QPushButton):
            self._close_btn.clicked.connect(self.reject)

        # Allow dragging the window by the custom title bar
        try:
            self._title_bar: Optional[QWidget] = getattr(self, 'customTitleBar', None)
            if isinstance(self._title_bar, QWidget):
                self._title_bar.installEventFilter(self)
        except Exception:
            self._title_bar = None

    def set_title(self, text: str) -> None:
        if isinstance(self._title_label, QLabel):
            self._title_label.setText(text)

    def set_content(self, widget: QWidget) -> None:
        """Insert a child widget into the content area, removing any placeholder items."""
        if not isinstance(self._content_layout, QVBoxLayout):
            return
        # Clear existing items
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        self._content_layout.addWidget(widget)

    # Optional: event filter to implement drag move when clicking the custom title bar
    def eventFilter(self, obj, event):
        try:
            if obj is getattr(self, 'customTitleBar', None):
                et = event.type()
                if et == event.MouseButtonPress:
                    if event.button() == Qt.LeftButton:
                        self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                        event.accept()
                        return True
                elif et == event.MouseMove:
                    if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
                        self.move(event.globalPos() - self._drag_pos)
                        event.accept()
                        return True
                elif et == event.MouseButtonRelease:
                    if event.button() == Qt.LeftButton:
                        self._drag_pos = None
                        event.accept()
                        return True
        except Exception:
            pass
        return super().eventFilter(obj, event)
