"""Minimal programmatic fallback UI for Screen 2.

Builds a single-panel view that exposes the same object names used by
the real `pageSplit` so the rest of the app can use the same API.
"""
from __future__ import annotations

from datetime import datetime
import traceback

from PyQt5.QtWidgets import (
	QApplication,
	QWidget,
	QLabel,
	QVBoxLayout,
	QHBoxLayout,
	QTableWidget,
	QFrame,
	QHeaderView,
	QStackedWidget,
	QSizePolicy,
	QSpacerItem,
)
from PyQt5.QtCore import Qt, QObject, QEvent, QTimer

import config
from config import (
	COMPANY_NAME,
	CUSTOMER_DISPLAY_DATE_FMT,
	CUSTOMER_DISPLAY_TIME_FMT,
	CUSTOMER_DISPLAY_FULLSCREEN,
)
from modules.date_time.formatters import format_date, format_time
from modules.ui_utils.error_logger import log_error_message


class LenientStack(QStackedWidget):
	"""QStackedWidget that clamps out-of-range indices to zero."""

	def setCurrentIndex(self, index: int) -> None:  # type: ignore[override]
		if self.count() == 0:
			return
		if index < 0 or index >= self.count():
			index = 0
		super().setCurrentIndex(index)


def _get_greeting_text() -> str:
	text = getattr(config, 'GREETING_SELECTED', '') or 'Thanks for shopping with us!'
	return str(text)


def _make_main_page(parent: QWidget) -> QWidget:
	frame = QFrame(parent)
	frame.setObjectName('screen2LeftFrame')
	frame.setStyleSheet('background-color: #f3efe9; color: #1f1f1f;')
	frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
	frame.setMinimumSize(500, 500)

	layout = QVBoxLayout(frame)
	layout.setContentsMargins(100, 20, 100, 20)
	layout.setSpacing(15)

	company = QLabel(COMPANY_NAME, frame)
	company.setObjectName('screen2CompanyLabel')
	company.setAlignment(Qt.AlignCenter)
	company.setStyleSheet('font-size: 35px; font-weight: 500;')
	layout.addWidget(company)

	date_lbl = QLabel(format_date(datetime.now(), CUSTOMER_DISPLAY_DATE_FMT), frame)
	date_lbl.setObjectName('screen2DateLabel')
	date_lbl.setAlignment(Qt.AlignCenter)
	date_lbl.setStyleSheet('font-size: 25px;')
	layout.addWidget(date_lbl)

	time_lbl = QLabel(format_time(datetime.now(), CUSTOMER_DISPLAY_TIME_FMT), frame)
	time_lbl.setObjectName('screen2TimeLabel')
	time_lbl.setAlignment(Qt.AlignCenter)
	time_lbl.setStyleSheet('font-size: 25px;')
	layout.addWidget(time_lbl)

	table = QTableWidget(frame)
	table.setObjectName('screen2SalesTable')
	table.setColumnCount(3)
	table.setHorizontalHeaderLabels(['Quantity', 'Description', 'Amount'])
	table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
	# Basic inline styling; a stricter re-apply happens after UI construction
	table.setStyleSheet('QTableWidget { background-color: #ffffff; color: #1f1f1f; }')
	hdr = table.horizontalHeader()
	try:
		hdr.setSectionResizeMode(0, QHeaderView.Stretch)
		hdr.setSectionResizeMode(1, QHeaderView.Stretch)
		hdr.setSectionResizeMode(2, QHeaderView.Stretch)
	except Exception:
		pass
	table.setColumnWidth(0, 320)   # Qty
	table.setColumnWidth(2, 360)   # Amount
	table.verticalHeader().setDefaultSectionSize(36)
	layout.addWidget(table, 1)

	spacer_top = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)
	layout.addItem(spacer_top)

	count_frame = QFrame(frame)
	count_frame.setObjectName('screen2CountFrame')
	count_layout = QHBoxLayout(count_frame)
	count_layout.setContentsMargins(0, 0, 0, 0)
	items_label = QLabel('Number of Items:', count_frame)
	items_label.setObjectName('screen2ItemsLabel')
	items_label.setStyleSheet('font-size: 25px;font-weight: 500;')
	count_layout.addWidget(items_label)
	count_layout.addStretch()
	num_label = QLabel('0', count_frame)
	num_label.setObjectName('screen2NumLabel')
	num_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
	num_label.setStyleSheet('font-size: 35px; font-weight: 500;')
	count_layout.addWidget(num_label)
	layout.addWidget(count_frame)

	total_frame = QFrame(frame)
	total_frame.setObjectName('screen2TotalFrame')
	total_layout = QHBoxLayout(total_frame)
	total_layout.setContentsMargins(0, 0, 0, 0)
	total_label = QLabel('Total Payable:', total_frame)
	total_label.setObjectName('screen2TotalLabel')
	total_label.setStyleSheet('font-size: 25px; font-weight: 500;')
	total_layout.addWidget(total_label)
	total_layout.addStretch()
	value_label = QLabel('$ 0.00', total_frame)
	value_label.setObjectName('screen2ValueLabel')
	value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
	value_label.setStyleSheet('font-size: 40px; font-weight: 500;')
	total_layout.addWidget(value_label)
	layout.addWidget(total_frame)

	layout.addStretch()

	footer = QLabel('Selvam POS', frame)
	footer.setObjectName('screen2FooterLabel')
	footer.setAlignment(Qt.AlignCenter)
	footer.setStyleSheet('font-size: 15px; color: #333333;')
	layout.addWidget(footer)

	"""qr_label = QLabel('QR CODE', frame)
	qr_label.setObjectName('screen2QrLabel')
	qr_label.setVisible(False)"""

	return frame


def create_fallback_ui(dialog: QWidget) -> None:
	"""Attach a minimal fallback UI to `dialog`."""
	try:
		mode_stack = LenientStack(dialog)
		mode_stack.setObjectName('screen2ModeStack')
		mode_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

		mode_page = QFrame(mode_stack)
		mode_layout = QVBoxLayout(mode_page)
		mode_layout.setContentsMargins(0, 0, 0, 0)

		ad_stack = LenientStack(mode_page)
		ad_stack.setObjectName('screen2AdDisplayStack')
		ad_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
		main_page = _make_main_page(ad_stack)
		ad_stack.addWidget(main_page)
		ad_stack.setCurrentIndex(0)
		mode_layout.addWidget(ad_stack)

		mode_stack.addWidget(mode_page)
		mode_stack.setCurrentIndex(0)

		parent_layout = dialog.layout()
		if parent_layout is None:
			parent_layout = QVBoxLayout(dialog)
			parent_layout.setContentsMargins(0, 0, 0, 0)
		parent_layout.addWidget(mode_stack, 1)
		mode_stack.show()

		# Completed overlay (hidden by default)
		overlay = QFrame(dialog)
		overlay.setObjectName('_completed_overlay')
		overlay.setStyleSheet('background-color: rgba(0,0,0,0.78); color: #ffffff;')
		overlay_layout = QVBoxLayout(overlay)
		overlay_layout.setContentsMargins(30, 30, 30, 30)
		title_label = QLabel('Thank you for payment', overlay)
		title_label.setAlignment(Qt.AlignCenter)
		title_label.setStyleSheet('font-size: 28px; font-weight: 700;')
		greeting_label = QLabel(_get_greeting_text(), overlay)
		greeting_label.setAlignment(Qt.AlignCenter)
		greeting_label.setStyleSheet('font-size: 18px;')
		overlay_layout.addStretch()
		overlay_layout.addWidget(title_label)
		overlay_layout.addSpacing(10)
		overlay_layout.addWidget(greeting_label)
		overlay_layout.addStretch()
		overlay.setVisible(False)
		overlay.setGeometry(0, 0, dialog.width() or 900, dialog.height() or 700)
		overlay.raise_()

		# Reapply table/header styles once the dialog is shown and any app QSS
		# has been applied. This helps the fallback win over global styles.
		def _reapply_table_styles() -> None:
			tbl = dialog.findChild(QTableWidget, 'screen2SalesTable')
			if tbl is None:
				return
			try:
				tbl.setStyleSheet(
					"QTableWidget#screen2SalesTable { background-color: #ffffff; color: #1f1f1f; gridline-color: #dcdcdc; }"
					"QTableWidget#screen2SalesTable QTableCornerButton::section { background-color: #a3a7a0; }"
					"QTableWidget#screen2SalesTable QTableView::item { padding: 6px 8px; }"
				)
				hdr = tbl.horizontalHeader()
				if hdr is not None:
					hdr.setStyleSheet("QHeaderView::section { background-color: #a3a7a0; color: #1f1f1f; font-size: 20px; font-weight: 500; }")
					hdr.setDefaultAlignment(Qt.AlignCenter | Qt.AlignVCenter)
					# Column sizing: fixed Qty and Amount, stretch Description
					try:
						hdr.setSectionResizeMode(0, QHeaderView.Stretch)
						hdr.setSectionResizeMode(1, QHeaderView.Stretch)
						hdr.setSectionResizeMode(2, QHeaderView.Stretch)
					except Exception:
						pass
					tbl.setColumnWidth(0, 120)
					tbl.setColumnWidth(2, 160)
					tbl.verticalHeader().setDefaultSectionSize(36)
				tbl.viewport().setStyleSheet('background-color: #ffffff;')
				tbl.setAlternatingRowColors(True)
			except Exception:
				pass

		QTimer.singleShot(250, _reapply_table_styles)

		class _ResizeWatcher(QObject):
			def __init__(self, dlg, ovl):
				super().__init__(dlg)
				self._dlg = dlg
				self._ovl = ovl

			def eventFilter(self, watched, event):
				if watched is self._dlg and event.type() in (QEvent.Resize, QEvent.Show):
					try:
						self._ovl.setGeometry(0, 0, self._dlg.width() or 900, self._dlg.height() or 700)
						self._ovl.raise_()
					except Exception:
						pass
				return False

		watcher = _ResizeWatcher(dialog, overlay)
		dialog.installEventFilter(watcher)
		setattr(dialog, '_fallback_resize_watcher', watcher)

		def _center_dialog() -> None:
			if getattr(dialog, 'isFullScreen', lambda: False)():
				return
			if CUSTOMER_DISPLAY_FULLSCREEN:
				return
			screen = dialog.screen() or QApplication.primaryScreen()
			if screen is None:
				return
			rect = screen.availableGeometry()
			w = dialog.width() or 900
			h = dialog.height() or 700
			dialog.resize(w, h)
			x = rect.x() + (rect.width() - w) // 2
			y = rect.y() + (rect.height() - h) // 2
			dialog.move(x, y)

		QTimer.singleShot(250, _center_dialog)

		setattr(dialog, '_using_fallback_ui', True)
		setattr(dialog, '_completed_overlay', overlay)
		setattr(dialog, '_completed_title_label', title_label)
		setattr(dialog, '_completed_greeting_label', greeting_label)

	except Exception:
		try:
			log_error_message(f"Fallback UI creation failed:\n{traceback.format_exc()}")
		except Exception:
			pass
		raise
