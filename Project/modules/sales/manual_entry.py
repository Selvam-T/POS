
# Manual Product Entry Dialog Controller
# Implements dialog logic for manual product entry in POS system
import os
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QLineEdit, QPushButton, QLabel, QCompleter
from PyQt5.QtCore import Qt
from modules.ui_utils import input_handler, ui_feedback
from modules.db_operation.database import PRODUCT_CACHE

def open_manual_entry_dialog(parent):
	"""
	Open the Manual Product Entry dialog and return QDialog for DialogWrapper execution.
	DialogWrapper handles: overlay, sizing, centering, scanner blocking, cleanup, and focus restoration.
	This function only creates and returns the QDialog.
	Args:
		parent: Main window instance
	Returns:
		QDialog instance ready for DialogWrapper.open_dialog_scanner_blocked() to execute
	"""
	BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	UI_DIR = os.path.join(BASE_DIR, 'ui')
	manual_ui = os.path.join(UI_DIR, 'manual_entry.ui')
	if not os.path.exists(manual_ui):
		print('manual_entry.ui not found at', manual_ui)
		return None
	try:
		dlg = uic.loadUi(manual_ui)
	except Exception as e:
		print('Failed to load manual_entry.ui:', e)
		return None

	# Set dialog properties (frameless, no OS title bar)
	dlg.setParent(parent)
	dlg.setModal(True)
	dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)

	# Styling temporarily disabled for debugging input/display issues
	# try:
	#     assets_dir = os.path.join(BASE_DIR, 'assets')
	#     sales_qss = os.path.join(assets_dir, 'sales.qss')
	#     if os.path.exists(sales_qss):
	#         with open(sales_qss, 'r', encoding='utf-8') as f:
	#             dlg.setStyleSheet(f.read())
	# except Exception as e:
	#     print('Failed to load sales.qss:', e)

	# Get widgets
	product_name_line = dlg.findChild(QLineEdit, 'manualNameSearchLineEdit')
	product_code_line = dlg.findChild(QLineEdit, 'manualProductCodeLineEdit')
	quantity_input = dlg.findChild(QLineEdit, 'manualQuantityLineEdit')
	unit_line = dlg.findChild(QLineEdit, 'manualUnitLineEdit')
	# Set initial placeholder for quantity
	if quantity_input is not None:
		quantity_input.setPlaceholderText('Enter Quantity')
	# Helper to update placeholder based on unit
	def update_quantity_placeholder():
		if quantity_input is None or unit_line is None:
			return
		unit_val = unit_line.text().strip().lower()
		if not unit_val or unit_val == 'each':
			quantity_input.setPlaceholderText('Enter Quantity')
		elif unit_val == 'kg':
			quantity_input.setPlaceholderText('Enter 500 grams as 0.5 or 1 Kg as 1')
		else:
			quantity_input.setPlaceholderText('Enter Quantity')
	# Update placeholder when unit changes
	if unit_line is not None:
		unit_line.textChanged.connect(update_quantity_placeholder)
	# Also call after product selection (code/name)
	error_label = dlg.findChild(QLabel, 'manualStatusLabel')
	btn_ok = dlg.findChild(QPushButton, 'btnManualOk')
	btn_cancel = dlg.findChild(QPushButton, 'btnManualCancel')
	custom_close_btn = dlg.findChild(QPushButton, 'customCloseBtn')

	# --- QLineEdit for product name search with shared input handler ---
	product_name_line.setPlaceholderText("Search Product Name")
	print("manualNameSearchLineEdit readOnly:", product_name_line.isReadOnly(), "enabled:", product_name_line.isEnabled())
	product_names = [rec[0] for rec in PRODUCT_CACHE.values() if rec and rec[0]]
	from modules.ui_utils.input_handler import setup_name_search_lineedit
	completer = setup_name_search_lineedit(product_name_line, product_names, error_label)
	from modules.ui_utils.input_handler import handle_product_name_edit, handle_product_code_edit
	# Connect dual-source handlers for product name
	def on_product_name_edit(name_override=None):
		# If name_override is provided (from completer), set it in the line edit first
		if name_override is not None:
			product_name_line.setText(name_override)
		handle_product_name_edit(
			product_name_line,
			product_code_line,
			unit_line,
			PRODUCT_CACHE,
			error_label,
			'cache',
			name_override=name_override
		)
		update_quantity_placeholder()
	product_name_line.editingFinished.connect(lambda: on_product_name_edit())
	product_name_line.returnPressed.connect(lambda: on_product_name_edit())
	if completer is not None:
		completer.activated.connect(lambda name: on_product_name_edit(name))
	# Connect dual-source handlers for product code
	def on_product_code_edit():
		handle_product_code_edit(product_code_line, product_name_line, unit_line, PRODUCT_CACHE, error_label, source_type='cache')
		update_quantity_placeholder()
	product_code_line.editingFinished.connect(on_product_code_edit)
	product_code_line.returnPressed.connect(on_product_code_edit)

	# Prevent Enter in QLineEdit from triggering dialog accept
	def block_enter_accept(event):
		if event.type() == event.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
			return True
		return False
	for line_edit in (product_code_line, product_name_line, quantity_input):
		if line_edit is not None:
			line_edit.installEventFilter(dlg)
	orig_eventFilter = dlg.eventFilter
	def custom_eventFilter(obj, event):
		if isinstance(obj, QLineEdit) and event.type() == event.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
			# Block Enter/Return in QLineEdit
			return True
		return orig_eventFilter(obj, event)
	dlg.eventFilter = custom_eventFilter

	# Real-time feedback: update product name and status as product code changes
	if product_code_line is not None:
		def update_product_name_realtime():
			code = product_code_line.text().strip()
			from modules.ui_utils.input_handler import map_product_fields_from_cache
			result = map_product_fields_from_cache(product_code=code, product_cache=PRODUCT_CACHE)
			if result:
				name = result['product_name']
				unit = result['record'][2] if len(result['record']) > 2 else 'Each'
				if product_name_line is not None:
					product_name_line.setText(name)
				if unit_line is not None:
					unit_line.setText(unit)
				ui_feedback.set_status_label(error_label, "", ok=True)
			else:
				if product_name_line is not None:
					product_name_line.setText("")
				if unit_line is not None:
					unit_line.setText("")
				if code:
					ui_feedback.set_status_label(error_label, "Product code not found.", ok=False)
				else:
					ui_feedback.set_status_label(error_label, "", ok=True)
		product_code_line.textChanged.connect(update_product_name_realtime)

	# OK button handler
	def handle_ok():
		try:
			# Tab order: product code, product name, quantity
			if product_code_line is None or not product_code_line.text().strip():
				ui_feedback.set_status_label(error_label, "Product code missing.", ok=False)
				if product_code_line is not None:
					product_code_line.setFocus()
				return
			code = product_code_line.text().strip()
			from modules.ui_utils.input_handler import map_product_fields_from_cache
			result = map_product_fields_from_cache(product_code=code, product_cache=PRODUCT_CACHE)
			if not result:
				ui_feedback.set_status_label(error_label, "Product code not found.", ok=False)
				if product_code_line is not None:
					product_code_line.setFocus()
				return
			if product_name_line is None or not product_name_line.text().strip():
				ui_feedback.set_status_label(error_label, "Product name must be selected.", ok=False)
				if product_name_line is not None:
					product_name_line.setFocus()
				return
			if quantity_input is None or not quantity_input.text().strip():
				ui_feedback.set_status_label(error_label, "Quantity is required.", ok=False)
				if quantity_input is not None:
					quantity_input.setFocus()
				return
			unit_price = result['record'][1]
			unit = result['record'][2] if len(result['record']) > 2 else 'Each'
			# Validate quantity based on unit
			text = quantity_input.text().strip()
			if unit.lower() == 'kg':
				ok, err = input_handler.input_validation.validate_quantity(text, unit_type='kg')
			else:
				ok, err = input_handler.input_validation.validate_quantity(text, unit_type='unit')
			if not ok:
				ui_feedback.set_status_label(error_label, err, ok=False)
				quantity_input.setFocus()
				return
			quantity = float(text) if unit.lower() == 'kg' else int(float(text))
			# All good
			ui_feedback.set_status_label(error_label, "✓ Adding to sale...", ok=True)
			dlg.manual_entry_result = {
				'product_code': result['product_code'],
				'product_name': result['product_name'],
				'quantity': quantity,
				'unit': unit,
				'unit_price': unit_price
			}
			dlg.accept()
		except Exception as e:
			msg = str(e)
			ui_feedback.set_status_label(error_label, msg, ok=False)

	def handle_cancel():
		dlg.reject()

	# Connect buttons
	if btn_ok:
		btn_ok.clicked.connect(handle_ok)
	if btn_cancel:
		btn_cancel.clicked.connect(handle_cancel)
	if custom_close_btn:
		custom_close_btn.clicked.connect(handle_cancel)

	# Return QDialog for DialogWrapper to execute (scanner will be blocked by wrapper)
	return dlg
