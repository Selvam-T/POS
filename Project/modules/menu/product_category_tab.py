from PyQt5.QtCore import QObject, QEvent, Qt, QTimer
from PyQt5.QtWidgets import QLabel, QLineEdit

from modules.ui_utils import category_service, ui_feedback
from modules.ui_utils.canonicalization import canonicalize_title_text
from modules.ui_utils.focus_utils import FocusGate
from modules.ui_utils.dialog_utils import log_error_message_and_postclose_statusBar
from modules.ui_utils.input_validation import validate_category
from config import MAIN_STATUS_ERROR_DURATION_MS, STATUS_LABEL_DURATION_MS


class ProductCategoryTabController:
    def __init__(self, dlg, widgets: dict, coord):
        self.dlg = dlg
        self.widgets = widgets
        self.coord = coord
        self._replace_selection_valid = {'val': False}

        self.add_gate = FocusGate([widgets['cat_add_le']], lock_enabled=True)
        self.select_gate = FocusGate([widgets['cat_select_combo']], lock_enabled=True)
        self.update_gate = FocusGate([widgets['cat_update_le']], lock_enabled=True)
        self.ok_gate = FocusGate([widgets['cat_ok']], lock_enabled=True)

        try:
            self.add_gate.remember_placeholders([widgets['cat_add_le']])
            self.update_gate.remember_placeholders([widgets['cat_update_le']])
        except Exception:
            pass

        self.add_lbl = self._find_label('categoryAddFieldLbl')
        self.select_lbl = self._find_label('categorySelectFieldLbl')
        self.update_lbl = self._find_label('categoryUpdateFieldLbl')
        self._cat_filter = None

        self._register_validators()
        self._wire_connections()
        self.set_add_mode()

    def _find_label(self, name: str):
        try:
            return self.dlg.findChild(QLabel, name)
        except Exception:
            return None

    @staticmethod
    def category_placeholder(_items: list | None = None) -> str:
        return '--Select Category--'

    def refresh_combo(self) -> None:
        combo = self.widgets['cat_select_combo']
        if combo is None:
            return
        try:
            categories = category_service.list_categories() or []
            combo.blockSignals(True)
            combo.clear()
            placeholder = self.category_placeholder(categories)
            combo.addItem(placeholder)

            items = []
            for c in categories:
                s = (c or '').strip()
                if not s:
                    continue
                if s.strip().lower() == 'other':
                    continue
                if s.strip().lower() == placeholder.strip().lower():
                    continue
                if s not in items:
                    items.append(s)
            combo.addItems(items)
            combo.setCurrentIndex(0)
        except Exception:
            pass
        finally:
            try:
                combo.blockSignals(False)
            except Exception:
                pass

    def clear_combo(self) -> None:
        combo = self.widgets['cat_select_combo']
        if combo is None:
            return
        try:
            combo.blockSignals(True)
            combo.clear()
            combo.setCurrentIndex(-1)
        except Exception:
            pass
        finally:
            try:
                combo.blockSignals(False)
            except Exception:
                pass

    def _set_field_locked(self, lbl: QLabel, locked: bool) -> None:
        if lbl is None:
            return
        try:
            lbl.setProperty('locked', bool(locked))
            try:
                lbl.style().unpolish(lbl)
                lbl.style().polish(lbl)
            except Exception:
                pass
            try:
                lbl.update()
            except Exception:
                pass
        except Exception:
            pass

    def _set_placeholders(self, add_enabled: bool, update_enabled: bool) -> None:
        try:
            if add_enabled:
                self.add_gate.restore_placeholders([self.widgets['cat_add_le']])
            else:
                self.add_gate.hide_placeholders([self.widgets['cat_add_le']])
        except Exception:
            pass
        try:
            if update_enabled:
                self.update_gate.restore_placeholders([self.widgets['cat_update_le']])
            else:
                self.update_gate.hide_placeholders([self.widgets['cat_update_le']])
        except Exception:
            pass

    def set_mode(self, mode: str) -> None:
        add_mode = mode == 'add'
        rem_mode = mode == 'remove'
        rep_mode = mode == 'replace'

        try:
            self.add_gate.set_locked(not add_mode)
            self._set_field_locked(self.add_lbl, not add_mode)
            if add_mode:
                self.widgets['cat_add_le'].setFocus()
        except Exception:
            pass
        try:
            self.select_gate.set_locked(not (rem_mode or rep_mode))
            self._set_field_locked(self.select_lbl, not (rem_mode or rep_mode))
        except Exception:
            pass
        try:
            if rep_mode:
                self.update_gate.set_locked(True)
                self._set_field_locked(self.update_lbl, True)
            else:
                self.update_gate.set_locked(not rep_mode)
                self._set_field_locked(self.update_lbl, not rep_mode)
        except Exception:
            pass

        try:
            self.widgets['cat_select_combo'].setEnabled(rem_mode or rep_mode)
        except Exception:
            pass
        try:
            self.widgets['cat_update_le'].setEnabled(rep_mode)
        except Exception:
            pass
        try:
            self.ok_gate.set_locked(True)
        except Exception:
            pass
        try:
            self._replace_selection_valid['val'] = False
            if not rep_mode:
                self.update_gate.set_locked(True)
                self._set_field_locked(self.update_lbl, True)
        except Exception:
            pass

        self._set_placeholders(add_mode, rep_mode)

        if rem_mode or rep_mode:
            self.refresh_combo()
            try:
                self.widgets['cat_select_combo'].setFocus()
            except Exception:
                pass
        else:
            self.clear_combo()

        try:
            if not add_mode:
                self.widgets['cat_add_le'].clear()
        except Exception:
            pass
        try:
            if not rep_mode:
                self.widgets['cat_update_le'].clear()
        except Exception:
            pass

    def set_add_mode(self):
        self.set_mode('add')

    def set_remove_mode(self):
        self.set_mode('remove')

    def set_replace_mode(self):
        self.set_mode('replace')

    def clear_tab(self) -> None:
        try:
            self.widgets['cat_add_radio'].setChecked(True)
        except Exception:
            pass
        try:
            self.set_add_mode()
        except Exception:
            pass
        for k in ['cat_add_le', 'cat_update_le']:
            try:
                self.widgets[k].clear()
            except Exception:
                pass
        try:
            self._replace_selection_valid['val'] = False
        except Exception:
            pass
        try:
            self.ok_gate.set_locked(True)
        except Exception:
            pass
        try:
            ui_feedback.clear_status_label(self.widgets['cat_status'])
        except Exception:
            pass
        try:
            self.widgets['cat_add_le'].setFocus()
            self.widgets['cat_add_le'].selectAll()
        except Exception:
            pass

    def _set_prompt(self, message: str) -> None:
        ui_feedback.set_status_label(self.widgets['cat_status'], message, ok=True)

    @staticmethod
    def _normalize_line_edit(le: QLineEdit) -> str:
        raw = (le.text() or '').strip()
        normalized = canonicalize_title_text(raw)
        if normalized != raw:
            try:
                le.setText(normalized)
            except Exception:
                pass
        return normalized

    def _validate_text(self, text: str, focus_widget=None) -> bool:
        ok, err = validate_category(text)
        if not ok:
            try:
                self.coord.set_error(focus_widget, err, status_label=self.widgets['cat_status'])
            except Exception:
                try:
                    ui_feedback.set_status_label(self.widgets['cat_status'], err, ok=False)
                except Exception:
                    pass
            try:
                if focus_widget is not None:
                    focus_widget.setFocus()
                    try:
                        if hasattr(focus_widget, 'selectAll'):
                            focus_widget.selectAll()
                    except Exception:
                        pass
            except Exception:
                pass
        return bool(ok)

    def _on_add_enter(self) -> None:
        name = self._normalize_line_edit(self.widgets['cat_add_le'])
        if not self._validate_text(name, focus_widget=self.widgets['cat_add_le']):
            return
        self._set_prompt(f"Add new category {name} ?")
        try:
            self.ok_gate.set_locked(False)
        except Exception:
            pass
        try:
            self.widgets['cat_ok'].setFocus()
        except Exception:
            pass

    def _on_combo_activated(self, _idx=None) -> None:
        combo = self.widgets['cat_select_combo']
        if combo is None:
            return
        current_name = (combo.currentText() or '').strip()
        if combo.currentIndex() <= 0 or current_name == self.category_placeholder([]):
            ui_feedback.set_status_label(self.widgets['cat_status'], "Select a category", ok=False)
            try:
                combo.setFocus()
            except Exception:
                pass
            return
        name = current_name
        if self.widgets['cat_remove_radio'].isChecked():
            self._set_prompt(f"Remove category {name} ?")
            try:
                self.ok_gate.set_locked(False)
            except Exception:
                pass
            try:
                self.widgets['cat_ok'].setFocus()
            except Exception:
                pass
        elif self.widgets['cat_replace_radio'].isChecked():
            self._set_prompt(f"Replace category {name} ?")
            try:
                self._replace_selection_valid['val'] = True
            except Exception:
                pass
            try:
                self.update_gate.set_locked(False)
                self._set_field_locked(self.update_lbl, False)
            except Exception:
                pass
            try:
                try:
                    self.widgets['cat_update_le'].setEnabled(True)
                    self.widgets['cat_update_le'].setReadOnly(False)
                    self.widgets['cat_update_le'].setFocusPolicy(Qt.StrongFocus)
                except Exception:
                    pass
                self.widgets['cat_update_le'].setFocus()
            except Exception:
                pass

    def _on_update_enter(self) -> None:
        replacement = self._normalize_line_edit(self.widgets['cat_update_le'])
        if not self._validate_text(replacement, focus_widget=self.widgets['cat_update_le']):
            return
        try:
            self.widgets['cat_ok'].setFocus()
        except Exception:
            pass

    def _cat_add_validator(self):
        txt = (self.widgets['cat_add_le'].text() or '').strip()
        ok, err = validate_category(txt)
        if not ok or not txt:
            raise ValueError(err or "Category is required")
        try:
            self.ok_gate.set_locked(False)
        except Exception:
            pass
        return True

    def _cat_update_validator(self):
        txt = (self.widgets['cat_update_le'].text() or '').strip()
        ok, err = validate_category(txt)
        if not ok or not txt:
            raise ValueError(err or "Category is required")
        try:
            if self._replace_selection_valid.get('val'):
                self.ok_gate.set_locked(False)
        except Exception:
            pass
        return True

    def _register_validators(self) -> None:
        try:
            self.coord.register_validator(
                self.widgets['cat_add_le'],
                self._cat_add_validator,
                status_label=self.widgets['cat_status'],
            )
        except Exception:
            pass
        try:
            self.coord.register_validator(
                self.widgets['cat_update_le'],
                self._cat_update_validator,
                status_label=self.widgets['cat_status'],
            )
        except Exception:
            pass

    def _on_add_text_changed(self, _txt=None):
        try:
            text = (self.widgets['cat_add_le'].text() or '').strip()
        except Exception:
            text = ''
        if not text:
            try:
                self.coord.clear_status(self.widgets['cat_status'])
            except Exception:
                pass
            try:
                self.ok_gate.set_locked(True)
            except Exception:
                pass
            return
        try:
            self._cat_add_validator()
        except Exception:
            try:
                self.ok_gate.set_locked(True)
            except Exception:
                pass
            return
        try:
            self.coord.clear_status(self.widgets['cat_status'])
            try:
                self.ok_gate.set_locked(False)
            except Exception:
                pass
        except Exception:
            pass

    def _on_update_text_changed(self, _txt=None):
        try:
            text = (self.widgets['cat_update_le'].text() or '').strip()
        except Exception:
            text = ''
        if not text:
            try:
                self.coord.clear_status(self.widgets['cat_status'])
            except Exception:
                pass
            try:
                self.ok_gate.set_locked(True)
            except Exception:
                pass
            return
        try:
            self._cat_update_validator()
        except Exception:
            try:
                self.ok_gate.set_locked(True)
            except Exception:
                pass
            return
        try:
            self.coord.clear_status(self.widgets['cat_status'])
        except Exception:
            pass

    def do_ok(self) -> None:
        def _finalize_category(message: str, *, show_label: bool = True) -> None:
            def _finish_success() -> None:
                self.clear_tab()
                self.widgets['cat_close'].setFocus()
                if show_label:
                    QTimer.singleShot(
                        0,
                        lambda: ui_feedback.set_status_label(
                            self.widgets['cat_status'],
                            message,
                            ok=True,
                            duration=STATUS_LABEL_DURATION_MS,
                        ),
                    )
            QTimer.singleShot(0, _finish_success)

        def _selected_category() -> str | None:
            combo = self.widgets['cat_select_combo']
            if combo is None:
                return None
            name = (combo.currentText() or '').strip()
            if combo.currentIndex() <= 0 or name == self.category_placeholder([]):
                ui_feedback.set_status_label(self.widgets['cat_status'], "Select a category", ok=False)
                return None
            return name

        def _run_category_op(op_fn, success_msg: str, error_tag: str) -> None:
            try:
                op_fn()
                _finalize_category(success_msg)
            except ValueError as e:
                ui_feedback.set_status_label(
                    self.widgets['cat_status'],
                    str(e),
                    ok=False,
                    duration=STATUS_LABEL_DURATION_MS,
                )
            except Exception as e:
                try:
                    ui_feedback.set_status_label(
                        self.widgets['cat_status'],
                        str(e),
                        ok=False,
                        duration=STATUS_LABEL_DURATION_MS,
                    )
                except Exception:
                    pass
                try:
                    log_error_message_and_postclose_statusBar(
                        self.dlg,
                        f"{error_tag}",
                        str(e),
                        user_message=f"Error: {e}",
                        level='error',
                        duration=MAIN_STATUS_ERROR_DURATION_MS,
                    )
                except Exception:
                    pass
                QTimer.singleShot(500, self.dlg.reject)

        if self.widgets['cat_add_radio'].isChecked():
            name = self._normalize_line_edit(self.widgets['cat_add_le'])
            if not self._validate_text(name, focus_widget=self.widgets['cat_add_le']):
                return
            _run_category_op(
                lambda: category_service.add_category(name),
                f"Category '{name.strip()}' added",
                "Category ADD failed",
            )
            return

        if self.widgets['cat_remove_radio'].isChecked():
            target = _selected_category()
            if not target:
                return
            _run_category_op(
                lambda: category_service.delete_category(target),
                f"Category '{target}' removed",
                "Category REMOVE failed",
            )
            return

        if self.widgets['cat_replace_radio'].isChecked():
            target = _selected_category()
            if not target:
                return
            replacement = self.widgets['cat_update_le'].text() or ''
            if not self._validate_text(replacement, focus_widget=self.widgets['cat_update_le']):
                return
            _run_category_op(
                lambda: category_service.update_category(target, replacement),
                f"Category '{target}' replaced with '{replacement}'",
                "Category REPLACE failed",
            )
            return

    def _wire_connections(self) -> None:
        try:
            self.widgets['cat_add_le'].textChanged.connect(self._on_add_text_changed)
        except Exception:
            pass
        try:
            self.widgets['cat_update_le'].textChanged.connect(self._on_update_text_changed)
        except Exception:
            pass
        try:
            self.widgets['cat_ok'].clicked.connect(self.do_ok)
        except Exception:
            pass
        try:
            self.widgets['cat_select_combo'].activated.connect(self._on_combo_activated)
        except Exception:
            pass
        try:
            self.widgets['cat_clear'].clicked.connect(self.clear_tab)
        except Exception:
            pass
        try:
            self.widgets['cat_add_radio'].toggled.connect(lambda checked: checked and self.set_add_mode())
            self.widgets['cat_remove_radio'].toggled.connect(lambda checked: checked and self.set_remove_mode())
            self.widgets['cat_replace_radio'].toggled.connect(lambda checked: checked and self.set_replace_mode())
        except Exception:
            pass

        class _CategoryEnterFilter(QObject):
            def eventFilter(filter_self, obj, event):
                if event.type() == QEvent.KeyPress:
                    key = event.key()
                    if key in (Qt.Key_Return, Qt.Key_Enter):
                        if obj is self.widgets.get('cat_add_le'):
                            self._on_add_enter()
                            return True
                        if obj is self.widgets.get('cat_update_le'):
                            self._on_update_enter()
                            return True
                        if obj is self.widgets.get('cat_select_combo'):
                            try:
                                if obj.view().isVisible():
                                    return False
                            except Exception:
                                pass
                            self._on_combo_activated(obj.currentIndex())
                            return True
                        if obj is self.widgets.get('cat_ok'):
                            self.do_ok()
                            return True
                return False

        try:
            self._cat_filter = _CategoryEnterFilter(self.dlg)
            self.widgets['cat_add_le'].installEventFilter(self._cat_filter)
            self.widgets['cat_select_combo'].installEventFilter(self._cat_filter)
            self.widgets['cat_update_le'].installEventFilter(self._cat_filter)
            self.widgets['cat_ok'].installEventFilter(self._cat_filter)
        except Exception:
            pass
