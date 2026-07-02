import os

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QPushButton

from config import (
    ICON_ADMIN,
    ICON_REPORTS,
    ICON_VEGETABLE,
    ICON_PRODUCT,
    ICON_GREETING,
    ICON_RECEIPT,
    ICON_LOGOUT,
)


class MainMenuController:
    BUTTON_TITLES = {
        'adminBtn': 'Admin',
        'reportsBtn': 'Reports',
        'vegetableBtn': 'Vegetable',
        'productBtn': 'Product',
        'greetingBtn': 'Greeting',
        'receiptBtn': 'Receipt',
        'logoutBtn': 'Logout',
    }

    BUTTON_ICONS = {
        'adminBtn': ICON_ADMIN,
        'reportsBtn': ICON_REPORTS,
        'vegetableBtn': ICON_VEGETABLE,
        'productBtn': ICON_PRODUCT,
        'greetingBtn': ICON_GREETING,
        'receiptBtn': ICON_RECEIPT,
        'logoutBtn': ICON_LOGOUT,
    }

    def __init__(self, main_window):
        self.main_window = main_window

    def setup(self) -> None:
        try:
            for obj_name, title in self.BUTTON_TITLES.items():
                btn = self.main_window.findChild(QPushButton, obj_name)
                if btn is None:
                    continue
                self._apply_button_presentation(btn, obj_name, title)
                self._wire_button(btn, obj_name, title)
        except Exception as e:
            try:
                from modules.ui_utils.error_logger import log_error_message
                log_error_message(f"Failed to wire menu buttons: {e}")
            except Exception:
                pass

    @staticmethod
    def _set_btn_icon_path(btn: QPushButton, icon_path: str, size: int = 60) -> bool:
        try:
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(QSize(size, size))
                return True
            return False
        except Exception:
            return False

    def _apply_button_presentation(self, btn: QPushButton, obj_name: str, title: str) -> None:
        icon_rel = self.BUTTON_ICONS.get(obj_name)
        success = False
        if icon_rel:
            success = self._set_btn_icon_path(btn, icon_rel)

        try:
            if success:
                btn.setProperty('iconFallback', False)
                btn.setText('')
            else:
                btn.setProperty('iconFallback', True)
                btn.setText(title)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.setToolTip(title)
        except Exception:
            pass

    def _wire_button(self, btn: QPushButton, obj_name: str, title: str) -> None:
        handler_map = {
            'productBtn': self.main_window.open_product_menu_dialog,
            'logoutBtn': self.main_window.open_logout_menu_dialog,
            'vegetableBtn': self.main_window.launch_vegetable_menu_dialog,
            'greetingBtn': self.main_window.open_greeting_menu_dialog,
            'adminBtn': self.main_window.open_admin_menu_dialog,
            'reportsBtn': self.main_window.open_report_menu_dialog,
            'receiptBtn': self.main_window.open_receipt_menu_dialog,
        }
        handler = handler_map.get(obj_name)
        if handler is not None:
            btn.clicked.connect(handler)
            return

        try:
            btn.setEnabled(False)
            btn.setToolTip(title)
        except Exception:
            pass
