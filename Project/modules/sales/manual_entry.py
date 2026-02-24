import os
from PyQt5.QtWidgets import QLineEdit, QPushButton, QLabel
from PyQt5.QtCore import Qt

from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui, 
    require_widgets, 
    set_dialog_info
)
from modules.ui_utils.focus_utils import FieldCoordinator, FocusGate, enforce_exclusive_lineedits
from modules.ui_utils import input_handler, ui_feedback
import modules.db_operation as dbop

# Paths
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))
UI_PATH = os.path.join(_PROJECT_DIR, 'ui', 'manual_entry.ui')
QSS_PATH = os.path.join(_PROJECT_DIR, 'assets', 'dialog.qss')

def launch_manual_entry_dialog(parent):
    # 1. Guards
    from config import MAX_TABLE_ROWS
    main_sales_table = getattr(parent, 'sales_table', None)
    if main_sales_table is None or main_sales_table.rowCount() >= MAX_TABLE_ROWS:
        from modules.ui_utils.max_rows_dialog import open_max_rows_dialog
        msg = "Table full" if main_sales_table else "Internal Error"
        open_max_rows_dialog(parent, msg).exec_()
        return None

    # 2. Build Dialog
    dlg = build_dialog_from_ui(UI_PATH, host_window=parent, dialog_name='Manual Entry', qss_path=QSS_PATH)

    if dlg:
        # PATH A: Extract widgets from loaded .ui
        widgets = require_widgets(dlg, {
            'code': (QLineEdit, 'manualProductCodeLineEdit'),
            'name_srch': (QLineEdit, 'manualNameSearchLineEdit'),
            'qty': (QLineEdit, 'manualQuantityLineEdit'),
            'unit': (QLineEdit, 'manualUnitLineEdit'),
            'status': (QLabel, 'manualStatusLabel'),
            'ok_btn': (QPushButton, 'btnManualOk'),
            'cancel_btn': (QPushButton, 'btnManualCancel'),
            'close_btn': (QPushButton, 'customCloseBtn'),
        })
    else:
        # PATH B: Build programmatic fallback
        dlg, widgets = _create_manual_entry_fallback_ui(parent)
        # Notify user/admin
        from modules.ui_utils.dialog_utils import set_dialog_error
        set_dialog_error(dlg, "Error: Manual Entry UI missing. Using fallback.")

    # --- SECTION 1: GATING & UI STATE ---
    
    # Unit is always read-only (display only)
    widgets['unit'].setReadOnly(True)
    widgets['unit'].setFocusPolicy(Qt.NoFocus)

    # Gate logic: Lock Qty and OK button until product is identified
    gate = FocusGate([widgets['qty'], widgets['ok_btn']], lock_enabled=True)
    
    def _set_gate_state(enabled: bool, result: dict = None):
        gate.set_locked(not enabled)
        if enabled and result:
            # Setup Quantity Placeholder based on unit
            is_kg = (result.get('unit', '').lower() == 'kg')
            widgets['qty'].setPlaceholderText('Enter weight (e.g. 0.5)' if is_kg else 'Enter Quantity')
            # Store price for the OK handler
            widgets['qty'].setProperty('unit_price', result.get('price', 0))
        else:
            widgets['qty'].clear()
            widgets['qty'].setPlaceholderText('')

    _set_gate_state(False) # Initial state

    # --- SECTION 2: COORDINATOR (Cross-Mapping) ---

    coord = FieldCoordinator(dlg)

    def _on_sync(result):
        _set_gate_state(bool(result), result)

    # Link Code -> Name/Unit
    coord.add_link(
        source=widgets['code'],
        target_map={'name': widgets['name_srch'], 'unit': widgets['unit']},
        lookup_fn=lambda val: input_handler.get_coordinator_lookup(val, 'code'),
        next_focus=widgets['qty'],
        status_label=widgets['status'],
        on_sync=_on_sync,
        auto_jump=False,
    )

    # Link Name Search -> Code/Unit
    coord.add_link(
        source=widgets['name_srch'],
        target_map={'code': widgets['code'], 'unit': widgets['unit']},
        lookup_fn=lambda val: input_handler.get_coordinator_lookup(val, 'name'),
        next_focus=widgets['qty'],
        status_label=widgets['status'],
        on_sync=_on_sync,
        auto_jump=True, 
    )

    coord.add_link(
        source=widgets['qty'],
        next_focus=widgets['ok_btn'],
        status_label=widgets['status'],
        swallow_empty=True,  # Don't move to OK if Qty is empty
        validate_fn=lambda: input_handler.handle_quantity_input(
            widgets['qty'], 
            unit_type='kg' if widgets['unit'].text().lower() == 'kg' else 'unit'
        )
    )

    # Search Exclusivity (Type in code -> clear name, vice versa)
    enforce_exclusive_lineedits(
        widgets['code'], widgets['name_srch'],
        on_switch_to_a=lambda: _set_gate_state(False),
        on_switch_to_b=lambda: _set_gate_state(False)
    )

    # Name search suggestions
    product_names = [rec[0] for rec in (dbop.PRODUCT_CACHE or {}).values() if rec[0]]
    input_handler.setup_name_search_lineedit(
        widgets['name_srch'], product_names,
        on_selected=lambda: coord._sync_fields(widgets['name_srch'])
    )

    # Auto-clear-on-correction: Clears the red error once the user types a valid qty
    coord.register_validator(
        widgets['qty'],
        lambda: input_handler.handle_quantity_input(
            widgets['qty'], 
            unit_type='kg' if widgets['unit'].text().lower() == 'kg' else 'unit'
        ),
        status_label=widgets['status']
    )

    # --- SECTION 3: EXECUTION ---

    def do_ok():
        try:
            # 1. Validate Product Selection
            if not widgets['code'].text() or not widgets['name_srch'].text():
                raise ValueError("Select a product first")

            # 2. Validate Quantity
            u_type = 'kg' if widgets['unit'].text().lower() == 'kg' else 'unit'
            qty = input_handler.handle_quantity_input(widgets['qty'], unit_type=u_type)

            # 3. Prepare Result for Sales Table
            dlg.manual_entry_result = {
                'product_code': widgets['code'].text(),
                'product_name': widgets['name_srch'].text(),
                'quantity': qty,
                'unit': widgets['unit'].text(),
                'unit_price': float(widgets['qty'].property('unit_price') or 0),
                'editable': True # Ensure it can be edited in the table
            }
            set_dialog_info(dlg, f"{widgets['name_srch'].text()} of {qty} {widgets['unit'].text()} added. ")
            dlg.accept()
        except ValueError as e:
            ui_feedback.set_status_label(widgets['status'], str(e), ok=False)

    def do_cancel():
        set_dialog_info(dlg, "Manual entry cancelled.")
        dlg.reject()

    # Connections
    widgets['ok_btn'].clicked.connect(do_ok)
    widgets['cancel_btn'].clicked.connect(do_cancel)
    if widgets.get('close_btn') is not None:
        widgets['close_btn'].clicked.connect(do_cancel)

    # --- SECTION 4: INITIALIZATION ---
    def barcode_override(barcode):
        """
        Directly injects the scanned barcode into the code field.
        Bypasses the keyboard buffer to prevent all leaked characters.
        """
        le = widgets['code']
        if le:
            # Overwrite widget text with the clean, complete barcode
            le.setText(barcode)
            # Manually trigger the coordinator to map Name and Unit
            coord._sync_fields(le)
        return True # Tells BarcodeManager the scan was handled

    # Attach to the dialog so DialogWrapper can install it
    try:
        dlg.barcode_override_handler = barcode_override
    except Exception:
        pass

    # Focus code field by default
    widgets['code'].setFocus()
    return dlg

def _create_manual_entry_fallback_ui(parent):
    """Generates the QDialog and the widgets dictionary manually."""
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout
    from PyQt5.QtGui import QFont

    dlg = QDialog(parent)
    dlg.setFixedSize(500, 400)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
    dlg.setModal(True)

    f_base = QFont(); f_base.setPointSize(12); f_base.setBold(True)
    dlg.setFont(f_base)

    layout = QVBoxLayout(dlg)
    
    dlg.setStyleSheet("background-color: beige;")
    # Title
    header = QLabel("MANUAL ENTRY (FALLBACK)")
    header.setAlignment(Qt.AlignCenter)
    header.setStyleSheet("font-size: 16pt; color: #991b1b;; font-weight: bold;")
    layout.addWidget(header)

    info = QLabel("UI failure. Check Error log.")
    info.setAlignment(Qt.AlignCenter)
    info.setStyleSheet("font-size: 12pt; color: #4b5563; font-weight: bold;")
    layout.addWidget(info)

    # Grid
    grid = QGridLayout()
    widgets = {
        'code': QLineEdit(), 'name_srch': QLineEdit(), 
        'unit': QLineEdit(), 'qty': QLineEdit(),
        'status': QLabel(""), 'ok_btn': QPushButton("ADD"), 
        'cancel_btn': QPushButton("CANCEL"), 'close_btn': None 
    }
    codelbl = QLabel("Code:")
    codelbl.setStyleSheet("font-size: 12pt; color: #4b5563;")
    grid.addWidget(codelbl, 0, 0) 
    widgets['code'].setStyleSheet("font-size: 12pt; color: #4b5563;")
    grid.addWidget(widgets['code'], 0, 1)

    namelbl = QLabel("Name:")
    namelbl.setStyleSheet("font-size: 12pt; color: #4b5563;")
    grid.addWidget(namelbl, 1, 0) 
    widgets['name_srch'].setStyleSheet("font-size: 12pt; color: #4b5563;")
    grid.addWidget(widgets['name_srch'], 1, 1)

    unitlbl = QLabel("Unit:")
    unitlbl.setStyleSheet("font-size: 12pt; color: #4b5563;")
    grid.addWidget(unitlbl, 2, 0) 
    widgets['unit'].setStyleSheet("font-size: 12pt; color: #4b5563;")
    grid.addWidget(widgets['unit'], 2, 1)

    qtylbl = QLabel("Qty:")
    qtylbl.setStyleSheet("font-size: 12pt; color: #4b5563;")
    grid.addWidget(qtylbl, 3, 0)  
    widgets['qty'].setStyleSheet("font-size: 12pt; color: #4b5563;")
    grid.addWidget(widgets['qty'], 3, 1)
    layout.addLayout(grid)

    # Status
    widgets['status'].setStyleSheet("color: red; font-size: 10pt;")
    widgets['status'].setAlignment(Qt.AlignCenter)
    layout.addWidget(widgets['status'])

    # Buttons
    btns = QHBoxLayout()
    btn_style = "font-size: 16pt; font-weight: bold; min-height: 60px; color: white; border-radius: 4px;"
    widgets['ok_btn'].setStyleSheet(f"background-color: #388e3c; {btn_style}")
    widgets['cancel_btn'].setStyleSheet(f"background-color: #d32f2f; {btn_style}")
    btns.addWidget(widgets['ok_btn']); btns.addWidget(widgets['cancel_btn'])
    layout.addLayout(btns)

    return dlg, widgets


    