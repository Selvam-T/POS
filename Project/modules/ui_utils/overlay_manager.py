from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt

class OverlayManager:
    def __init__(self, main_window):
        self.mw = main_window  # Reference to MainLoader
        self._dim_overlay = None

    def toggle_dim_overlay(self, show=True):
        if show:
            if not self._dim_overlay:
                self._dim_overlay = QWidget(self.mw)
                self._dim_overlay.setObjectName('dimOverlay')
                self._dim_overlay.setStyleSheet('#dimOverlay { background-color: rgba(0, 0, 0, 110); }')
                self._dim_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self._dim_overlay.setGeometry(self.mw.rect())
            self._dim_overlay.show()
            self._dim_overlay.raise_()
        else:
            if self._dim_overlay:
                self._dim_overlay.hide()
