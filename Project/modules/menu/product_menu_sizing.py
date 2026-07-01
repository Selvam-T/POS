from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QGuiApplication

from config import PRODUCT_MENU_TAB_RATIOS


class ProductMenuSizingController:
    _TAB_RATIO_KEYS = {
        0: 'add',
        1: 'remove',
        2: 'update',
        3: 'category',
    }

    def __init__(self, dlg, main_window, widgets: dict):
        self.dlg = dlg
        self.main_window = main_window
        self.widgets = widgets

    def wire(self) -> None:
        try:
            self.widgets['tabs'].currentChanged.connect(self.schedule_resize_to_tab)
            QTimer.singleShot(0, self.schedule_resize_to_tab)
        except Exception:
            pass

    def center_on_main(self) -> None:
        try:
            host_geom = self.main_window.frameGeometry()
            x = host_geom.x() + (host_geom.width() - self.dlg.width()) // 2
            y = host_geom.y() + (host_geom.height() - self.dlg.height()) // 2
            self.dlg.move(x, y)
        except Exception:
            pass

    def ratio_for_tab(self, index: int):
        ratio_key = self._TAB_RATIO_KEYS.get(int(index), 'add')
        ratio = PRODUCT_MENU_TAB_RATIOS.get(ratio_key)
        if ratio is not None:
            return ratio
        ratio = PRODUCT_MENU_TAB_RATIOS.get('add')
        if ratio is not None:
            return ratio
        try:
            return next(iter(PRODUCT_MENU_TAB_RATIOS.values()))
        except Exception:
            return None

    def resize_to_tab(self, index: int | None = None) -> None:
        tabs = self.widgets.get('tabs')
        if tabs is None:
            return
        if index is None:
            try:
                index = tabs.currentIndex()
            except Exception:
                index = None
        if index is None or index < 0:
            return

        try:
            active_tab = tabs.widget(index)
            if active_tab is not None and active_tab.layout() is not None:
                active_tab.layout().activate()
            tabs.updateGeometry()
            if self.dlg.layout() is not None:
                self.dlg.layout().activate()
        except Exception:
            pass

        try:
            host_geom = self.main_window.frameGeometry()
            ratio = self.ratio_for_tab(index)
            if ratio is None:
                desired_w = self.dlg.width()
                desired_h = self.dlg.height()
            else:
                width_ratio, height_ratio = ratio
                desired_w = max(int(host_geom.width() * float(width_ratio)), self.dlg.minimumWidth())
                desired_h = max(int(host_geom.height() * float(height_ratio)), 300)
            max_h = None
            try:
                screen = None
                if self.dlg.windowHandle() is not None:
                    screen = self.dlg.windowHandle().screen()
                if screen is None:
                    screen = QGuiApplication.primaryScreen()
                if screen is not None:
                    geom = screen.availableGeometry()
                    max_h = int(geom.height())
            except Exception:
                max_h = None

            if max_h is not None:
                desired_h = min(desired_h, max_h)

            # Clear the old fixed-height constraint before resizing. This
            # avoids asking Qt/Windows to shrink below the previous minimum.
            self.dlg.setMinimumHeight(0)
            self.dlg.setMaximumHeight(16777215)
            self.dlg.resize(desired_w, desired_h)
            self.dlg.setMinimumHeight(desired_h)
            self.dlg.setMaximumHeight(desired_h)
            try:
                actual_w = int(self.dlg.width())
                actual_h = int(self.dlg.height())
                if abs(actual_h - int(desired_h)) > 2 or abs(actual_w - int(desired_w)) > 2:
                    from modules.ui_utils.error_logger import log_error_message
                    log_error_message(
                        "WARNING: ProductMenu resize mismatch: "
                        f"desired={int(desired_w)}x{int(desired_h)} "
                        f"actual={actual_w}x{actual_h}"
                    )
            except Exception:
                pass
        except Exception:
            pass

        self.center_on_main()
        try:
            self.dlg.updateGeometry()
            self.dlg.update()
            QTimer.singleShot(0, self.dlg.repaint)
        except Exception:
            pass

    def schedule_resize_to_tab(self, index: int | None = None) -> None:
        try:
            idx = self.widgets['tabs'].currentIndex() if index is None else int(index)
        except Exception:
            idx = None
        QTimer.singleShot(0, lambda idx=idx: self.resize_to_tab(idx))
