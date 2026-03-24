import os
import re
import shutil
from typing import List, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QIcon
from PyQt5.QtWidgets import QFileDialog, QListWidget, QListWidgetItem, QLabel, QPushButton

from modules.ui_utils import ui_feedback
from config import MAX_ADS, ALLOWED_EXTS, REQ_WIDTH, REQ_HEIGHT, REQ_RATIO

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(THIS_DIR))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ADS_DIR = os.path.join(ASSETS_DIR, 'ads')


class Screen2AdsController:
    def __init__(
        self,
        *,
        list_widget: QListWidget,
        preview_label: QLabel,
        count_label: QLabel,
        status_label: QLabel,
        add_btn: QPushButton,
        remove_btn: QPushButton,
        up_btn: QPushButton,
        down_btn: QPushButton,
    ) -> None:
        self._list = list_widget
        self._preview = preview_label
        self._count = count_label
        self._status = status_label
        self._add_btn = add_btn
        self._remove_btn = remove_btn
        self._up_btn = up_btn
        self._down_btn = down_btn

        self._ensure_ads_dir()

    # Wire widget signals to handlers.
    def wire(self) -> None:
        try:
            self._list.itemSelectionChanged.connect(self._on_selection_changed)
        except Exception:
            pass
        try:
            self._add_btn.clicked.connect(self._add_images)
            self._remove_btn.clicked.connect(self._remove_selected)
            self._up_btn.clicked.connect(self._move_selected_up)
            self._down_btn.clicked.connect(self._move_selected_down)
        except Exception:
            pass

    # Refresh the list and preview based on current files.
    def refresh(self, *, select_index: int = -1) -> None:
        self._list.clear()
        files = self._list_ad_files()
        for path in files:
            self._list.addItem(self._make_item(path))

        self._update_count(len(files))
        if len(files) == 0:
            self._set_preview(None)
        if select_index >= 0 and files:
            select_index = min(select_index, len(files) - 1)
            self._list.setCurrentRow(select_index)
        self._set_status('')
        self._update_gates()

    # Create the ads folder if missing.
    def _ensure_ads_dir(self) -> None:
        try:
            os.makedirs(ADS_DIR, exist_ok=True)
        except Exception:
            pass

    # Show an error/success message in screen2StatusLabel.
    def _set_status(self, message: str, *, ok: bool | None = None, duration: int = 2000) -> None:
        if not message:
            ui_feedback.clear_status_label(self._status)
            return
        if ok is None:
            ok = False
        ui_feedback.set_status_label(self._status, message, ok=ok, duration=duration)

    # Update count label with current total.
    def _update_count(self, count: int) -> None:
        try:
            self._count.setText(f"{count} / {MAX_ADS} images")
        except Exception:
            pass

    # List files in ads directory sorted by prefix.
    def _list_ad_files(self) -> List[str]:
        files: List[str] = []
        try:
            for name in os.listdir(ADS_DIR):
                _, ext = os.path.splitext(name)
                if ext.lower() in ALLOWED_EXTS:
                    files.append(name)
        except FileNotFoundError:
            return []
        files.sort(key=self._sort_key)
        return [os.path.join(ADS_DIR, name) for name in files]

    # Sort by numeric prefix, then name.
    def _sort_key(self, filename: str) -> Tuple[int, str]:
        base = os.path.basename(filename)
        match = re.match(r'^(\d+)_', base)
        if match:
            return int(match.group(1)), base.lower()
        return 9999, base.lower()

    # Remove numeric prefix from a filename.
    def _strip_prefix(self, filename: str) -> str:
        base = os.path.basename(filename)
        return re.sub(r'^\d+_', '', base)

    # Build list widget item with thumbnail icon.
    def _make_item(self, path: str) -> QListWidgetItem:
        name = os.path.basename(path)
        item = QListWidgetItem(name)
        item.setData(Qt.UserRole, path)

        pix = QPixmap(path)
        if not pix.isNull():
            icon_pix = pix.scaled(160, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item.setIcon(QIcon(icon_pix))
        return item

    # Update preview when selection changes.
    def _on_selection_changed(self) -> None:
        item = self._list.currentItem()
        if item is None:
            self._set_preview(None)
            self._update_gates()
            return
        path = item.data(Qt.UserRole)
        self._set_preview(path)
        self._update_gates()

    # Set preview label pixmap/text.
    def _set_preview(self, path: str | None) -> None:
        if not path:
            self._preview.setText('No image selected')
            self._preview.setPixmap(QPixmap())
            return

        pix = QPixmap(path)
        if pix.isNull():
            self._preview.setText('Failed to load image')
            self._preview.setPixmap(QPixmap())
            return

        label_size = self._preview.size()
        scaled = pix.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._preview.setPixmap(scaled)
        self._preview.setText('')

    # Open file dialog and add selected images.
    def _add_images(self) -> None:
        current = self._list_ad_files()
        if len(current) >= MAX_ADS:
            self._set_status(f"Max {MAX_ADS} images reached.", ok=False)
            return

        files, _ = QFileDialog.getOpenFileNames(
            self._list.window(),
            'Select ad images',
            '',
            'Images (*.jpg *.jpeg *.png)',
        )
        if not files:
            return

        remaining = MAX_ADS - len(current)
        accepted: List[str] = []
        rejected: List[tuple[str, str]] = []
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

            if os.path.exists(dest_path):
                dest_name = f"{next_index}_{self._unique_base(base)}"
                dest_path = os.path.join(ADS_DIR, dest_name)

            shutil.copy2(src, dest_path)
            next_index += 1

        self.refresh(select_index=len(current))
        self._set_status(self._build_add_status(to_add, rejected, remaining), ok=bool(to_add))

    # Validate format, size, and ratio.
    def _validate_image(self, path: str) -> tuple[bool, str]:
        _, ext = os.path.splitext(path)
        if ext.lower() not in ALLOWED_EXTS:
            return False, 'Invalid format'

        image = QImage(path)
        if image.isNull():
            return False, 'Unreadable image'

        width = image.width()
        height = image.height()
        if width != REQ_WIDTH or height != REQ_HEIGHT:
            return False, 'Wrong resolution'

        ratio = width / height if height else 0
        if abs(ratio - REQ_RATIO) > 0.001:
            return False, 'Wrong aspect ratio'

        return True, ''

    # Build a concise status message after add.
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

        return 'No images added.'

    # Ensure unique base filename when conflicts occur.
    def _unique_base(self, base: str) -> str:
        name, ext = os.path.splitext(base)
        i = 1
        while True:
            candidate = f"{name}_{i}{ext}"
            if not os.path.exists(os.path.join(ADS_DIR, candidate)):
                return candidate
            i += 1

    # Remove the selected image.
    def _remove_selected(self) -> None:
        item = self._list.currentItem()
        if item is None:
            self._set_status('Select an image to remove.', ok=False)
            return
        path = item.data(Qt.UserRole)
        try:
            os.remove(path)
        except Exception:
            self._set_status('Failed to remove image.', ok=False)
            return

        self._renumber_files()
        self.refresh()
        self._set_status('Image removed.', ok=True)

    # Move selected row up.
    def _move_selected_up(self) -> None:
        row = self._list.currentRow()
        if row <= 0:
            return
        self._swap_rows(row, row - 1)

    # Move selected row down.
    def _move_selected_down(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= self._list.count() - 1:
            return
        self._swap_rows(row, row + 1)

    # Swap two list rows and persist order.
    def _swap_rows(self, row_a: int, row_b: int) -> None:
        item_a = self._list.takeItem(row_a)
        item_b = self._list.takeItem(row_b - 1 if row_b > row_a else row_b)

        if row_b > row_a:
            self._list.insertItem(row_a, item_b)
            self._list.insertItem(row_b, item_a)
        else:
            self._list.insertItem(row_b, item_a)
            self._list.insertItem(row_a, item_b)

        self._persist_order_from_list()
        self._list.setCurrentRow(row_b)

    # Persist list order by renumbering files.
    def _persist_order_from_list(self) -> None:
        ordered_paths: List[str] = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            ordered_paths.append(item.data(Qt.UserRole))

        self._renumber_files(ordered_paths)
        self.refresh(select_index=0)

    # Rename files to numeric prefix order.
    def _renumber_files(self, ordered_paths: List[str] | None = None) -> None:
        if ordered_paths is None:
            ordered_paths = self._list_ad_files()

        temp_paths: List[str] = []
        for idx, path in enumerate(ordered_paths, start=1):
            base = os.path.basename(path)
            temp_name = f"__tmp__{idx}__{base}"
            temp_path = os.path.join(ADS_DIR, temp_name)
            try:
                os.rename(path, temp_path)
                temp_paths.append(temp_path)
            except Exception:
                continue

        for idx, temp_path in enumerate(temp_paths, start=1):
            base = self._strip_prefix(temp_path)
            final_name = f"{idx}_{base}"
            final_path = os.path.join(ADS_DIR, final_name)
            try:
                os.rename(temp_path, final_path)
            except Exception:
                continue

    # Enable/disable buttons based on selection and count.
    def _update_gates(self) -> None:
        count = self._list.count()
        row = self._list.currentRow()
        has_sel = row >= 0

        try:
            self._add_btn.setEnabled(count < MAX_ADS)
            self._remove_btn.setEnabled(has_sel)
            self._up_btn.setEnabled(has_sel and row > 0)
            self._down_btn.setEnabled(has_sel and row < count - 1)
        except Exception:
            pass
