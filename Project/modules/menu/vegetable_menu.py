import os
from PyQt5.QtWidgets import QLineEdit, QPushButton, QLabel, QComboBox
from PyQt5.QtCore import Qt, QTimer, QDateTime

from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui, require_widgets, set_dialog_main_status_max,
    set_dialog_error, build_error_fallback_dialog
)
from modules.ui_utils.focus_utils import FieldCoordinator, FocusGate
from modules.ui_utils import input_handler, ui_feedback
from modules.db_operation import (
    get_product_full, add_product, delete_product, 
    refresh_product_cache, PRODUCT_CACHE
)

# Constants
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))
UI_PATH = os.path.join(_PROJECT_DIR, 'ui', 'vegetable_menu.ui')
QSS_PATH = os.path.join(_PROJECT_DIR, 'assets', 'dialog.qss')
VEG_SLOTS = 16
DEFAULT_VEG_CATEGORY = 'Vegetable'

def launch_vegetable_menu_dialog(host_window):
    # 1. Build Dialog with Safety Net
    dlg = build_dialog_from_ui(UI_PATH, host_window=host_window, dialog_name='Vegetable Menu', qss_path=QSS_PATH)
    if not dlg:
        return build_error_fallback_dialog(host_window, "Vegetable Menu", QSS_PATH)

    widgets = require_widgets(dlg, {
        'chooser': (QComboBox, 'vegMChooseComboBox'),
        'code': (QLineEdit, 'vegMProductCodeLineEdit'),
        'name': (QLineEdit, 'vegMProductNameLineEdit'),
        'sell': (QLineEdit, 'vegMSellingPriceLineEdit'),
        'cost': (QLineEdit, 'vegMCostPriceLineEdit'),
        'markup': (QLineEdit, 'vegMMarkupLineEdit'),
        'unit': (QComboBox, 'vegMUnitComboBox'),
        'supp': (QLineEdit, 'vegMSupplierLineEdit'),
        'cat': (QLineEdit, 'vegMCategoryLineEdit'),
        'status': (QLabel, 'vegMStatusLabel'),
        'ok_btn': (QPushButton, 'btnVegMOk'),
        'del_btn': (QPushButton, 'btnVegMDel'),
        'cancel_btn': (QPushButton, 'btnVegMCancel'),
        'close_btn': (QPushButton, 'customCloseBtn')
    })

    # --- SECTION 1: GATING & UI ---
    for k in ['code', 'cat', 'markup']:
        widgets[k].setReadOnly(True)
        widgets[k].setFocusPolicy(Qt.NoFocus)

    # Ghost Gating Setup
    _placeholders = {k: widgets[k].placeholderText() for k in ['name', 'sell', 'cost', 'supp']}
    gate = FocusGate([widgets['name'], widgets['sell'], widgets['cost'], widgets['unit'], 
                    widgets['supp'], widgets['ok_btn'], widgets['del_btn']], lock_enabled=True)

    def _set_gate_state(enabled: bool):
        gate.set_locked(not enabled)
        if not enabled:
            for k in ['name', 'sell', 'cost', 'supp', 'markup', 'cat']: widgets[k].clear()
            widgets['markup'].setPlaceholderText("")
            for k in _placeholders: widgets[k].setPlaceholderText("")
            widgets['unit'].setCurrentIndex(-1) # Hides "--Select Unit--"
        else:
            for k, p in _placeholders.items(): widgets[k].setPlaceholderText(p)
            widgets['cat'].setText(DEFAULT_VEG_CATEGORY)
            
            if not widgets['cost'].text():
                widgets['cost'].clear()

    # --- SECTION 2: SLOTS & COORDINATOR ---

    def _populate_slots():
        widgets['chooser'].clear()
        widgets['chooser'].addItem("Select Vegetable to update", userData=None)
        for i in range(1, VEG_SLOTS + 1):
            code = f"VEG{i:02d}"
            rec = (PRODUCT_CACHE or {}).get(code)
            label = str(rec[0]) if rec and rec[0] else f"VEGETABLE {i}"
            widgets['chooser'].addItem(label, userData=code)

    _populate_slots()
    _set_gate_state(False)

    coord = FieldCoordinator(dlg)

    def _slot_lookup(_val):
        code = widgets['chooser'].currentData()
        if not code: return None
        found, pdata = get_product_full(code)
        return {
            'code': code, 'name': pdata.get('name', ''), 'price': str(pdata.get('price', '')),
            'cost': str(pdata.get('cost')) if pdata.get('cost') else "", 'unit': pdata.get('unit', ''),
            'supplier': pdata.get('supplier', ''), '_found': found
        }

    def _on_slot_sync(result):
        if not result:
            _set_gate_state(False)
            return
        _set_gate_state(True)
        # 1. Handle Unit selection
        idx = widgets['unit'].findText(result.get('unit', ''), Qt.MatchFixedString)
        widgets['unit'].setCurrentIndex(idx if idx >= 0 else 0)
        
        # 2. MARKUP CALCULATION ON LOAD
        input_handler.calculate_markup_widgets(
            widgets['sell'], 
            widgets['cost'], 
            widgets['markup']
        )

        # 3. Conditional Focus Jumps
        if result.get('_found'):
            QTimer.singleShot(0, widgets['cancel_btn'].setFocus) # Valid slot -> Safety
        else:
            QTimer.singleShot(0, widgets['name'].setFocus) # Empty slot -> Invitation

    coord.add_link(source=widgets['chooser'], on_sync=_on_slot_sync, lookup_fn=_slot_lookup,
                   target_map={'code': widgets['code'], 'name': widgets['name'], 'price': widgets['sell'], 
                               'cost': widgets['cost'], 'supplier': widgets['supp']})

    # Navigation & Validation Graph
    coord.add_link(widgets['name'], next_focus=widgets['unit'], status_label=widgets['status'],
                   validate_fn=lambda: input_handler.handle_product_name_input(widgets['name'], exclude_code=widgets['code'].text()))
    
    coord.add_link(widgets['unit'], next_focus=widgets['sell'], status_label=widgets['status'])

    coord.add_link(widgets['sell'], next_focus=widgets['cost'], status_label=widgets['status'],
                   validate_fn=lambda: input_handler.handle_selling_price(widgets['sell'], "Selling Price"))

    coord.add_link(widgets['cost'], next_focus=widgets['supp'], status_label=widgets['status'],
                   validate_fn=lambda: input_handler.handle_cost_price(widgets['cost'], "Cost Price"))

    coord.add_link(widgets['supp'], next_focus=widgets['ok_btn'], status_label=widgets['status'],
                   validate_fn=lambda: input_handler.handle_supplier_input(widgets['supp']))

    # Shared Markup Logic
    input_handler.wire_markup_logic(
        sell_le=widgets['sell'], 
        cost_le=widgets['cost'], 
        markup_le=widgets['markup']
    )

    # --- SECTION 3: REWRITE ENGINE ---

    def _execute_rewrite(candidate_veg=None, remove_code=None):
        vegs = []
        for i in range(1, 17):
            code = f"VEG{i:02d}"
            if remove_code == code: continue
            if widgets['code'].text() == code and candidate_veg:
                vegs.append(candidate_veg)
            else:
                found, p = get_product_full(code)
                if found and p.get('name'):
                    vegs.append({'name': p['name'], 'sell': p['price'], 'cost': p.get('cost', 0), 
                                'supp': p.get('supplier', ''), 'unit': p.get('unit', '')})

        sorted_vegs = sorted(vegs, key=lambda x: x['name'].lower())
        try:
            for i in range(1, 17): delete_product(f"VEG{i:02d}")
            now = QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss')
            for i, v in enumerate(sorted_vegs, 1):
                add_product(f"VEG{i:02d}", v['name'], v['sell'], DEFAULT_VEG_CATEGORY, 
                            v['supp'], v['cost'], v['unit'], now)
            refresh_product_cache()
            return True, "Vegetable list updated."
        except Exception as e:
            msg = f"DB Rewrite Failed: {e}"
            from modules.ui_utils.error_logger import log_error
            log_error(msg); set_dialog_error(dlg, msg)
            return False, msg

    # --- SECTION 4: ACTIONS ---

    def do_save():
        try:
            # Final Mandatory Check
            if widgets['unit'].currentIndex() <= 0: raise ValueError("Unit is required")
            name = input_handler.handle_product_name_input(widgets['name'], exclude_code=widgets['code'].text())
            sell = input_handler.handle_selling_price(widgets['sell'], "Selling Price")
            cost = float(input_handler.handle_cost_price(widgets['cost'], "Cost Price") or 0.0)
            
            new_data = {
                'name': name, 'sell': sell, 'cost': cost, 
                'supp': widgets['supp'].text().strip(), 
                'unit': widgets['unit'].currentText()
            }
            
            ok, msg = _execute_rewrite(candidate_veg=new_data)
            if ok:
                set_dialog_main_status_max(dlg, msg, level='info')
                dlg.accept()
            else: raise ValueError(msg)
        except ValueError as e:
            ui_feedback.set_status_label(widgets['status'], str(e), ok=False)

    def do_delete():
        ok, msg = _execute_rewrite(remove_code=widgets['code'].text())
        if ok:
            set_dialog_main_status_max(dlg, f"Vegetable '{widgets['name'].text()}' removed.", level='info')
            dlg.accept()
        else:
            ui_feedback.set_status_label(widgets['status'], msg, ok=False)

    def do_close() -> None:
        # Info-level so it won't override any warning/error queued earlier.
        set_dialog_main_status_max(dlg, 'Vegetable menu closed.', level='info', duration=3000)
        dlg.reject()
        
    widgets['ok_btn'].clicked.connect(do_save)
    widgets['del_btn'].clicked.connect(do_delete)
    widgets['cancel_btn'].clicked.connect(do_close)
    widgets['close_btn'].clicked.connect(do_close)
    widgets['chooser'].setFocus()
    return dlg