"""Reusable date gating helpers for dialog controllers.

Provides a commit-based date-range gate that can be shared by multiple dialogs.
"""
from __future__ import annotations

from PyQt5.QtCore import QObject, QEvent, Qt, QDate
from PyQt5.QtWidgets import QDateEdit


def refresh_style(widget) -> None:
    if widget is None:
        return
    try:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
    except Exception:
        pass


def set_locked_property(widget, locked: bool) -> None:
    if widget is None:
        return
    try:
        widget.setProperty('locked', bool(locked))
    except Exception:
        pass
    refresh_style(widget)


def set_dateedit_locked(date_edit: QDateEdit, locked: bool, *, fmt_property: str = '_gate_display_format') -> None:
    if date_edit is None:
        return

    try:
        if date_edit.property(fmt_property) is None:
            date_edit.setProperty(fmt_property, date_edit.displayFormat() or 'dd/MM/yyyy')
    except Exception:
        pass

    fmt = 'dd/MM/yyyy'
    try:
        saved_fmt = date_edit.property(fmt_property)
        if isinstance(saved_fmt, str) and saved_fmt.strip():
            fmt = saved_fmt
    except Exception:
        pass

    try:
        if locked:
            date_edit.setEnabled(False)
            # Use a quoted literal blank so Qt renders no date text reliably.
            date_edit.setDisplayFormat("' '")
            try:
                le = date_edit.lineEdit()
                if le is not None:
                    le.setReadOnly(True)
                    le.clear()
            except Exception:
                pass
        else:
            date_edit.setEnabled(True)
            date_edit.setDisplayFormat(fmt)
            try:
                le = date_edit.lineEdit()
                if le is not None:
                    le.setReadOnly(False)
            except Exception:
                pass
    except Exception:
        pass

    set_locked_property(date_edit, locked)


def set_buttons_locked(buttons, locked: bool) -> None:
    for btn in list(buttons or []):
        if btn is None:
            continue
        try:
            btn.setEnabled(not bool(locked))
        except Exception:
            pass
        set_locked_property(btn, locked)


class _DateEnterFilter(QObject):
    def __init__(self, parent, *, from_edit: QDateEdit, to_edit: QDateEdit, on_from_enter, on_to_enter):
        super().__init__(parent)
        self._from_edit = from_edit
        self._to_edit = to_edit
        self._on_from_enter = on_from_enter
        self._on_to_enter = on_to_enter

    def eventFilter(self, obj, event):
        try:
            if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if obj is self._from_edit and callable(self._on_from_enter):
                    self._on_from_enter()
                    return True
                if obj is self._to_edit and callable(self._on_to_enter):
                    self._on_to_enter()
                    return True
        except Exception:
            pass
        return False


class DateRangeGateController(QObject):
    """Shared commit-based gate for (today/date-range) dialogs."""

    def __init__(
        self,
        parent,
        *,
        today_radio,
        date_range_radio,
        from_date_edit: QDateEdit,
        to_date_edit: QDateEdit,
        action_buttons,
        field_labels=None,
        on_actions_unlocked=None,
    ):
        super().__init__(parent)
        self.today_radio = today_radio
        self.date_range_radio = date_range_radio
        self.from_date_edit = from_date_edit
        self.to_date_edit = to_date_edit
        self.action_buttons = list(action_buttons or [])
        self.field_labels = list(field_labels or [])
        self.on_actions_unlocked = on_actions_unlocked
        self.from_committed = False
        self.to_committed = False

        self._enter_filter = _DateEnterFilter(
            parent,
            from_edit=self.from_date_edit,
            to_edit=self.to_date_edit,
            on_from_enter=self._on_from_enter,
            on_to_enter=self._on_to_enter,
        )

        self._wire_signals()

    def _wire_signals(self) -> None:
        try:
            self.today_radio.toggled.connect(lambda _checked=None: self.apply_state())
        except Exception:
            pass
        try:
            self.date_range_radio.toggled.connect(self._on_date_range_toggled)
        except Exception:
            pass
        try:
            self.from_date_edit.dateChanged.connect(self._on_from_changed)
        except Exception:
            pass
        try:
            self.to_date_edit.dateChanged.connect(self._on_to_changed)
        except Exception:
            pass
        try:
            self.from_date_edit.installEventFilter(self._enter_filter)
            self.to_date_edit.installEventFilter(self._enter_filter)
        except Exception:
            pass

    def _on_date_range_toggled(self, checked: bool) -> None:
        self.apply_state()
        if not checked:
            return
        try:
            if self.from_date_edit.isEnabled():
                self.from_date_edit.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass

    def init_date_bounds(self, *, today: QDate | None = None) -> None:
        day = today or QDate.currentDate()
        try:
            self.from_date_edit.setDate(day)
            self.from_date_edit.setMaximumDate(day)
        except Exception:
            pass
        try:
            self.to_date_edit.setDate(day)
            self.to_date_edit.setMaximumDate(day)
        except Exception:
            pass

    def _clamp_to_min(self) -> None:
        try:
            self.to_date_edit.setMinimumDate(self.from_date_edit.date())
            if self.to_date_edit.date() < self.from_date_edit.date():
                self.to_date_edit.setDate(self.from_date_edit.date())
        except Exception:
            pass

    def _on_from_changed(self, _date: QDate) -> None:
        if not self.date_range_radio.isChecked():
            return
        self.from_committed = False
        self.to_committed = False
        self._clamp_to_min()
        self.apply_state()

    def _on_to_changed(self, _date: QDate) -> None:
        if not self.date_range_radio.isChecked():
            return
        self.to_committed = False
        self._clamp_to_min()
        self.apply_state()

    def _on_from_enter(self) -> None:
        if not self.date_range_radio.isChecked():
            return
        self.from_committed = True
        self.to_committed = False
        self._clamp_to_min()
        self.apply_state()
        try:
            self.to_date_edit.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass

    def _on_to_enter(self) -> None:
        if not self.date_range_radio.isChecked() or not self.from_committed:
            return
        self._clamp_to_min()
        self.to_committed = True
        self.apply_state()
        try:
            if callable(self.on_actions_unlocked):
                self.on_actions_unlocked()
        except Exception:
            pass

    def apply_state(self) -> None:
        # Labels are gray in default/unselected date-range state.
        labels_locked = (not bool(self.date_range_radio.isEnabled())) or (not bool(self.date_range_radio.isChecked()))
        for lbl in self.field_labels:
            set_locked_property(lbl, labels_locked)

        if self.today_radio.isChecked():
            self.from_committed = False
            self.to_committed = False
            set_dateedit_locked(self.from_date_edit, True)
            set_dateedit_locked(self.to_date_edit, True)
            # Today mode keeps actions available by design.
            set_buttons_locked(self.action_buttons, False)
            return

        set_dateedit_locked(self.from_date_edit, False)
        set_dateedit_locked(self.to_date_edit, not self.from_committed)
        set_buttons_locked(self.action_buttons, not self.to_committed)
