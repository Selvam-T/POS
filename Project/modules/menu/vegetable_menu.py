"""VegetableMenuDialog: manages vegetable label editing dialog with toggles and state."""
import os
from pathlib import Path
from typing import List

from PyQt5 import QtWidgets, QtCore, uic, QtGui

from modules.wrappers import settings as app_settings


class VegetableMenuDialog(QtWidgets.QDialog):
    """Dialog to edit 16 vegetable labels with toggle sliders and NOT USED indicator."""

    configChanged = QtCore.pyqtSignal(dict)  # emits the final mapping dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint | QtCore.Qt.CustomizeWindowHint)
        # Load .ui as a child widget, not as the dialog itself
        self._base_dir = Path(__file__).resolve().parents[2]  # .../POS/Project
        ui_path = self._base_dir / 'ui' / 'vegetable_menu.ui'
        uic.loadUi(str(ui_path), self) # Pass 'self' as the second argument
        # Wire custom window titlebar X button to close dialog
        custom_close_btn = self.findChild(QtWidgets.QPushButton, 'customCloseBtn')
        if custom_close_btn is not None:
            custom_close_btn.clicked.connect(self.reject)
        # Find all required widgets from content
        self._rows = []  # list of tuples (lineEdit, slider, not_used_label)
        for i in range(1, app_settings.veg_slots() + 1):
            le = self.findChild(QtWidgets.QLineEdit, f"lineEdit_value_{i}")
            sl = self.findChild(QtWidgets.QSlider, f"slider_toggle_{i}")
            nu = self.findChild(QtWidgets.QLabel, f"label_not_used_{i}")
            if not (isinstance(le, QtWidgets.QLineEdit) and isinstance(sl, QtWidgets.QSlider) and isinstance(nu, QtWidgets.QLabel)):
                continue
            self._rows.append((le, sl, nu))
            # Ensure placeholder text looks inactive/muted consistently
            try:
                pal = le.palette()
                pal.setColor(QtGui.QPalette.PlaceholderText, QtGui.QColor('#888888'))
                le.setPalette(pal)
            except Exception:
                pass
            # Mark the right-side label so QSS rules can target it without affecting other labels
            try:
                nu.setProperty('rightIndicator', True)
                nu.style().unpolish(nu)
                nu.style().polish(nu)
                nu.update()
            except Exception:
                pass
            sl.setRange(0, 1)
            sl.setSingleStep(1)
            sl.setPageStep(1)
            # Make the slider compact to look like a switch
            try:
                sl.setFixedWidth(52)
                sl.setFixedHeight(20)
            except Exception:
                pass
            sl.valueChanged.connect(lambda v, idx=i: self._on_toggle_changed(idx, v))
            # Right-side label styling handled via QSS
            # Clear messages on any user edits
            try:
                le.textChanged.connect(self._clear_message)
            except Exception:
                pass
        # Wire buttons
        pushButton_ok = self.findChild(QtWidgets.QPushButton, 'pushButton_ok')
        if pushButton_ok is not None:
            pushButton_ok.clicked.connect(self._on_ok)
        pushButton_cancel = self.findChild(QtWidgets.QPushButton, 'pushButton_cancel')
        if pushButton_cancel is not None:
            pushButton_cancel.clicked.connect(self.reject)
        # Load existing mapping and populate
        self._load_and_populate()

    # ---------------------------- UI helpers ----------------------------
    def _on_toggle_changed(self, idx: int, value: int) -> None:
        # New semantics:
        # value 0 (left) -> left side selected: QLineEdit editable; right text grayed
        # value 1 (right) -> left side not editable (read-only); right text remains grayed
        le, sl, nu = self._rows[idx - 1]
        if value == 0:
            le.setReadOnly(False)
            le.setEnabled(True)
            # Visuals handled via QSS
            # Mark slider active for QSS (green background)
            sl.setProperty('active', True)
            # Mark input active for QSS (blue border)
            le.setProperty('active', True)
            # Right label becomes inactive color when left side is active
            nu.setProperty('active', False)
        else:
            # Right selected: make left non-editable but not visually grayed
            le.setReadOnly(True)
            le.setEnabled(True)
            # Visuals handled via QSS
            # Mark slider inactive for QSS (gray background)
            sl.setProperty('active', False)
            # Mark input inactive for QSS
            le.setProperty('active', False)
            # Right label becomes active color when right side is active
            nu.setProperty('active', True)

        # Refresh style to apply dynamic property changes
        try:
            sl.style().unpolish(sl)
            sl.style().polish(sl)
            sl.update()
        except Exception:
            pass
        try:
            le.style().unpolish(le)
            le.style().polish(le)
            le.update()
        except Exception:
            pass
        try:
            nu.style().unpolish(nu)
            nu.style().polish(nu)
            nu.update()
        except Exception:
            pass
        # Clear any message when toggling choices
        self._clear_message()

    def _load_and_populate(self) -> None:
        mapping = app_settings.load_vegetables()
        n = min(app_settings.veg_slots(), len(self._rows))
        for i in range(1, n + 1):
            le, sl, nu = self._rows[i - 1]
            entry = mapping.get(f"veg{i}", {"state": "unused", "label": "unused"})
            if entry.get("state") == "custom":
                # Left position (0) means editable
                sl.setValue(0)
                le.setReadOnly(False)
                le.setEnabled(True)
                le.setText(entry.get("label", ""))
                # Visuals handled via QSS
                sl.setProperty('active', True)
                le.setProperty('active', True)
                nu.setProperty('active', False)
            else:
                # Right position (1) means NOT USED
                sl.setValue(1)
                le.setReadOnly(True)
                le.setEnabled(True)
                le.clear()
                # Visuals handled via QSS
                sl.setProperty('active', False)
                le.setProperty('active', False)
                nu.setProperty('active', True)

            # Ensure QSS picks up the property
            try:
                sl.style().unpolish(sl)
                sl.style().polish(sl)
                sl.update()
            except Exception:
                pass
            try:
                le.style().unpolish(le)
                le.style().polish(le)
                le.update()
            except Exception:
                pass
            try:
                nu.style().unpolish(nu)
                nu.style().polish(nu)
                nu.update()
            except Exception:
                pass
        # Clear message on load
        self._clear_message()

        # Load dialog-specific stylesheet if available
        try:
            qss_path = self._base_dir / 'assets' / 'menu.qss'
            if qss_path.exists():
                with open(qss_path, 'r', encoding='utf-8') as f:
                    self.setStyleSheet(f.read())
        except Exception:
            pass

    # ---------------------------- Validation + Save ----------------------------
    def _collect_active_labels(self) -> List[str]:
        labels: List[str] = []
        for i, (le, sl, _nu) in enumerate(self._rows, start=1):
            if sl.value() == 0:  # left selected => custom/editable
                txt = le.text().strip()
                if not txt:
                    le.setFocus()
                    raise ValueError(f"Vegetable {i} cannot be empty.")
                labels.append(txt)
        # Duplicate check (case-insensitive)
        lowered = [s.casefold() for s in labels]
        seen = set()
        for i, l in enumerate(lowered):
            if l in seen:
                raise ValueError("Duplicate labels are not allowed.")
            seen.add(l)
        return labels

    def _sorted_assignment(self, labels: List[str]) -> dict:
        # Sort A→Z (case-insensitive) and assign left-to-right; remainder unused
        labels_sorted = sorted(labels, key=lambda s: s.casefold())
        n = app_settings.veg_slots()
        new_map = {f"veg{i}": {"state": "unused", "label": "unused"} for i in range(1, n + 1)}
        for idx, lbl in enumerate(labels_sorted, start=1):
            if idx > n:
                break
            new_map[f"veg{idx}"] = {"state": "custom", "label": lbl}
        return new_map

    def _on_ok(self) -> None:
        try:
            labels = self._collect_active_labels()
        except ValueError as e:
            self._set_message(str(e), kind='error')
            return
        mapping = self._sorted_assignment(labels)
        try:
            app_settings.save_vegetables(mapping)
        except Exception as e:
            self._set_message(f"Could not save labels: {e}", kind='error')
            return
        # notify and close
        self._clear_message()
        self.configChanged.emit(mapping)
        self.accept()

    # ---------------------------- Message helpers ----------------------------
    def _set_message(self, text: str, kind: str = 'info') -> None:
        lbl = getattr(self, 'messageLabel', None)
        if isinstance(lbl, QtWidgets.QLabel):
            try:
                lbl.setText(text)
                lbl.setProperty('kind', kind)
                lbl.style().unpolish(lbl)
                lbl.style().polish(lbl)
                lbl.update()
            except Exception:
                pass

    def _clear_message(self) -> None:
        lbl = getattr(self, 'messageLabel', None)
        if isinstance(lbl, QtWidgets.QLabel):
            try:
                lbl.clear()
                lbl.setProperty('kind', 'info')
                lbl.style().unpolish(lbl)
                lbl.style().polish(lbl)
                lbl.update()
            except Exception:
                pass

