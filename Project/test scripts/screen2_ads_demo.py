#!/usr/bin/env python3
"""Standalone demo for Screen 2 Ads tab (admin_menu.ui).

Features:
- Loads admin_menu.ui and focuses Screen 2 Ads tab.
- Uses a local assets/ads/ folder as the source of truth.
- Supports add/remove/reorder with file-based persistence.
- Generates thumbnails in-memory via QPixmap.scaled().
"""
import os
import re
import shutil
from typing import List, Tuple

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QListWidgetItem,
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UI_PATH = os.path.join(BASE_DIR, "ui", "admin_menu.ui")
ADS_DIR = os.path.join(BASE_DIR, "assets", "ads")

MAX_ADS = 6
ALLOWED_EXTS = {".jpg", ".jpeg", ".png"}
REQ_WIDTH = 1280
REQ_HEIGHT = 800
REQ_RATIO = REQ_WIDTH / REQ_HEIGHT


class Screen2AdsDemo(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi(UI_PATH, self)
        self._ensure_ads_dir()
        self._wire()
        self._refresh_list(select_index=0)
        self._focus_screen2_tab()

    def _ensure_ads_dir(self) -> None:
        os.makedirs(ADS_DIR, exist_ok=True)

    def _wire(self) -> None:
        self.screen2ListWidget.itemSelectionChanged.connect(self._on_selection_changed)
        self.addScreen2Btn.clicked.connect(self._add_images)
        self.removeScreen2Btn.clicked.connect(self._remove_selected)
        self.upScreen2Btn.clicked.connect(self._move_selected_up)
        self.downScreen2Btn.clicked.connect(self._move_selected_down)
        self.btnScreen2Ok.clicked.connect(self._refresh_list)
        self.btnScreen2Cancel.clicked.connect(self.close)
        self.customCloseBtn.clicked.connect(self.close)

    def _focus_screen2_tab(self) -> None:
        # Find the Screen 2 Ads tab index by object name if possible.
        tab_widget = getattr(self, "tabWidget", None)
        if tab_widget is None:
            return
        idx = tab_widget.indexOf(self.tabScreen2)
        if idx >= 0:
            tab_widget.setCurrentIndex(idx)

    def _status(self, message: str) -> None:
        try:
            self.screen2StatusLabel.setText(message)
        except Exception:
            pass

    def _count_label(self, count: int) -> None:
        try:
            self.screen2CountLabel.setText(f"{count} / {MAX_ADS} images")
        except Exception:
            pass

    def _list_ad_files(self) -> List[str]:
        files = []
        try:
            for name in os.listdir(ADS_DIR):
                _, ext = os.path.splitext(name)
                if ext.lower() in ALLOWED_EXTS:
                    files.append(name)
        except FileNotFoundError:
            return []
        files.sort(key=self._sort_key)
        return [os.path.join(ADS_DIR, name) for name in files]

    def _sort_key(self, filename: str) -> Tuple[int, str]:
        # Sort by numeric prefix if present, else keep alphabetical.
        base = os.path.basename(filename)
        match = re.match(r"^(\d+)_", base)
        if match:
            return int(match.group(1)), base.lower()
        return 9999, base.lower()

    def _strip_prefix(self, filename: str) -> str:
        base = os.path.basename(filename)
        return re.sub(r"^\d+_", "", base)

    def _refresh_list(self, select_index: int = -1) -> None:
        self.screen2ListWidget.clear()
        files = self._list_ad_files()
        for path in files:
            item = self._make_item(path)
            self.screen2ListWidget.addItem(item)

        count = len(files)
        self._count_label(count)
        if count == 0:
            self._set_preview(None)
        if select_index >= 0 and count > 0:
            select_index = min(select_index, count - 1)
            self.screen2ListWidget.setCurrentRow(select_index)
        self._status("")

    def _make_item(self, path: str) -> QListWidgetItem:
        name = os.path.basename(path)
        item = QListWidgetItem(name)
        item.setData(Qt.UserRole, path)

        pix = QPixmap(path)
        if not pix.isNull():
            icon_pix = pix.scaled(160, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item.setIcon(QIcon(icon_pix))
        return item

    def _on_selection_changed(self) -> None:
        item = self.screen2ListWidget.currentItem()
        if item is None:
            self._set_preview(None)
            return
        path = item.data(Qt.UserRole)
        self._set_preview(path)

    def _set_preview(self, path: str | None) -> None:
        if not path:
            self.screen2PreviewLabel.setText("No image selected")
            self.screen2PreviewLabel.setPixmap(QPixmap())
            return

        pix = QPixmap(path)
        if pix.isNull():
            self.screen2PreviewLabel.setText("Failed to load image")
            self.screen2PreviewLabel.setPixmap(QPixmap())
            return

        label_size = self.screen2PreviewLabel.size()
        scaled = pix.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.screen2PreviewLabel.setPixmap(scaled)
        self.screen2PreviewLabel.setText("")

    def _add_images(self) -> None:
        current = self._list_ad_files()
        if len(current) >= MAX_ADS:
            self._status(f"Max {MAX_ADS} images reached.")
            return

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select ad images",
            "",
            "Images (*.jpg *.jpeg *.png)",
        )
        if not files:
            return

        remaining = MAX_ADS - len(current)
        accepted = []
        rejected = []
        for path in files:
            ok, reason = self._validate_image(path)
            if ok:
                accepted.append(path)
            else:
                rejected.append((path, reason))

        to_add = accepted[:remaining]

        next_index = len(current) + 1
        for src in to_add:
            base = os.path.basename(src)
            base = self._strip_prefix(base)
            dest_name = f"{next_index}_{base}"
            dest_path = os.path.join(ADS_DIR, dest_name)

            # Ensure no overwrite if user selects same file name multiple times.
            if os.path.exists(dest_path):
                dest_name = f"{next_index}_{self._unique_base(base)}"
                dest_path = os.path.join(ADS_DIR, dest_name)

            shutil.copy2(src, dest_path)
            next_index += 1

        self._refresh_list(select_index=len(current))
        self._status(self._build_add_status(to_add, rejected, remaining))

    def _validate_image(self, path: str) -> tuple[bool, str]:
        _, ext = os.path.splitext(path)
        if ext.lower() not in ALLOWED_EXTS:
            return False, "Invalid format"

        image = QImage(path)
        if image.isNull():
            return False, "Unreadable image"

        width = image.width()
        height = image.height()
        if width != REQ_WIDTH or height != REQ_HEIGHT:
            return False, "Wrong resolution"

        ratio = width / height if height else 0
        if abs(ratio - REQ_RATIO) > 0.001:
            return False, "Wrong aspect ratio"

        return True, ""

    def _build_add_status(
        self,
        added: List[str],
        rejected: List[tuple[str, str]],
        remaining: int,
    ) -> str:
        if rejected:
            reason = rejected[0][1]
            if added:
                return f"Added {len(added)}. File rejected - {reason}."
            return f"File rejected - {reason}."

        if added:
            message = f"Added {len(added)}."
            if remaining < len(added):
                message = f"{message} Limit reached."
            return message

        return "No images added."

    def _unique_base(self, base: str) -> str:
        name, ext = os.path.splitext(base)
        i = 1
        while True:
            candidate = f"{name}_{i}{ext}"
            if not os.path.exists(os.path.join(ADS_DIR, candidate)):
                return candidate
            i += 1

    def _remove_selected(self) -> None:
        item = self.screen2ListWidget.currentItem()
        if item is None:
            self._status("Select an image to remove.")
            return
        path = item.data(Qt.UserRole)
        try:
            os.remove(path)
        except Exception:
            self._status("Failed to remove image.")
            return

        self._renumber_files()
        self._refresh_list()
        self._status("Image removed.")

    def _move_selected_up(self) -> None:
        row = self.screen2ListWidget.currentRow()
        if row <= 0:
            return
        self._swap_rows(row, row - 1)

    def _move_selected_down(self) -> None:
        row = self.screen2ListWidget.currentRow()
        if row < 0 or row >= self.screen2ListWidget.count() - 1:
            return
        self._swap_rows(row, row + 1)

    def _swap_rows(self, row_a: int, row_b: int) -> None:
        item_a = self.screen2ListWidget.takeItem(row_a)
        item_b = self.screen2ListWidget.takeItem(row_b - 1 if row_b > row_a else row_b)

        if row_b > row_a:
            self.screen2ListWidget.insertItem(row_a, item_b)
            self.screen2ListWidget.insertItem(row_b, item_a)
        else:
            self.screen2ListWidget.insertItem(row_b, item_a)
            self.screen2ListWidget.insertItem(row_a, item_b)

        self._persist_order_from_list()
        self.screen2ListWidget.setCurrentRow(row_b)

    def _persist_order_from_list(self) -> None:
        ordered_paths = []
        for i in range(self.screen2ListWidget.count()):
            item = self.screen2ListWidget.item(i)
            ordered_paths.append(item.data(Qt.UserRole))

        self._renumber_files(ordered_paths)
        self._refresh_list(select_index=0)

    def _renumber_files(self, ordered_paths: List[str] | None = None) -> None:
        if ordered_paths is None:
            ordered_paths = self._list_ad_files()

        # First, move all files to temporary names to avoid collisions.
        temp_paths = []
        for idx, path in enumerate(ordered_paths, start=1):
            base = os.path.basename(path)
            temp_name = f"__tmp__{idx}__{base}"
            temp_path = os.path.join(ADS_DIR, temp_name)
            try:
                os.rename(path, temp_path)
                temp_paths.append(temp_path)
            except Exception:
                continue

        # Then rename to final numbered names.
        for idx, temp_path in enumerate(temp_paths, start=1):
            base = self._strip_prefix(temp_path)
            final_name = f"{idx}_{base}"
            final_path = os.path.join(ADS_DIR, final_name)
            try:
                os.rename(temp_path, final_path)
            except Exception:
                continue


def main() -> None:
    app = QApplication([])
    dlg = Screen2AdsDemo()
    dlg.show()
    app.exec_()


if __name__ == "__main__":
    main()
