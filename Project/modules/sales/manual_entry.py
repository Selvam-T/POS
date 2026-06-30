import os
from PyQt5.QtWidgets import QLineEdit, QPushButton, QLabel, QComboBox
from PyQt5.QtCore import Qt, QTimer

from modules.ui_utils.dialog_utils import (
    build_dialog_from_ui, 
    require_widgets, 
    set_dialog_info,
    clear_display,
)
from modules.ui_utils.focus_utils import FieldCoordinator, FocusGate, enforce_exclusive_lineedits
from modules.ui_utils import input_handler, input_validation, ui_feedback
import modules.db_operation as dbop
from config import QSS_DIR, STATUS_LABEL_DURATION_MS, UI_DIR

UI_PATH = os.path.join(UI_DIR, 'manual_entry.ui')
QSS_PATH = os.path.join(QSS_DIR, 'dialog.qss')

def launch_manual_entry_dialog(parent):
    # 1. Guards
    from config import MAX_TABLE_ROWS
    main_sales_table = getattr(parent, 'sales_table', None)
    if main_sales_table is None or main_sales_table.rowCount() >= MAX_TABLE_ROWS:
        from modules.ui_utils.max_rows_dialog import open_max_rows_dialog
        msg = "Table full" if main_sales_table else "Internal Error"
        open_max_rows_dialog(parent, msg).exec_()
        return None

    # 2. Build dialog
    dlg = build_dialog_from_ui(UI_PATH, host_window=parent, dialog_name='Manual Entry', qss_path=QSS_PATH)

    if dlg:
        # Path A: loaded .ui
        widgets = require_widgets(dlg, {
            'code': (QLineEdit, 'manualProductCodeLineEdit'),
            'name_srch': (QLineEdit, 'manualNameSearchLineEdit'),
            'qty': (QLineEdit, 'manualQuantityLineEdit'),
            'unit': (QComboBox, 'manualUnitComboBox'),
            'status': (QLabel, 'manualStatusLabel'),
            'ok_btn': (QPushButton, 'btnManualOk'),
            'cancel_btn': (QPushButton, 'btnManualCancel'),
            'close_btn': (QPushButton, 'customCloseBtn'),
        })
    else:
        # Path B: fallback UI
        dlg, widgets = _create_manual_entry_fallback_ui(parent)
        from modules.ui_utils.dialog_utils import set_dialog_error
        set_dialog_error(dlg, "Error: Manual Entry UI missing. Using fallback.")

    # 3. Gating and UI state
    UNIT_PROMPT = '-- Select Unit --'

    # For Kg products, this combo selects input units; persisted sale units stay Kg.
    widgets['unit'].clear()
    widgets['unit'].setEnabled(False)
    widgets['unit'].setFocusPolicy(Qt.NoFocus)
    widgets['unit'].setProperty('product_unit', '')

    barcode_warning = ui_feedback.create_auto_clearing_warning_label(
        widgets['status'],
        ui_feedback.BARCODE_WARNING_TEXT,
        duration=STATUS_LABEL_DURATION_MS,
    )

    def _clear_barcode_warning_when_code_cleared(_text=None) -> None:
        try:
            if widgets['code'].text().strip():
                return
        except Exception:
            return
        barcode_warning.clear()

    gate = FocusGate([widgets['qty'], widgets['ok_btn']], lock_enabled=True)
    try:
        gate.remember_placeholders([widgets['qty']])
        gate.hide_placeholders([widgets['qty']])
    except Exception:
        pass
    
    def _combo_text() -> str:
        try:
            return (widgets['unit'].currentText() or '').strip()
        except Exception:
            return ''

    def _product_unit() -> str:
        try:
            return str(widgets['unit'].property('product_unit') or '').strip()
        except Exception:
            return ''

    def _is_product_kg() -> bool:
        return _product_unit().lower() == 'kg'

    def _is_input_gram() -> bool:
        return _combo_text().lower() == 'gram'

    def _selected_kg_input_unit() -> bool:
        return _combo_text().lower() in ('kg', 'gram')

    def _set_qty_placeholder() -> None:
        try:
            if _is_product_kg():
                if _is_input_gram():
                    widgets['qty'].setPlaceholderText('Enter grams (e.g. 600)')
                else:
                    widgets['qty'].setPlaceholderText('Enter weight (e.g. 1.5)')
            else:
                widgets['qty'].setPlaceholderText('Enter Quantity')
        except Exception:
            pass

    def _set_combo_items(items, *, enabled: bool, focus_policy=Qt.NoFocus) -> None:
        combo = widgets['unit']
        combo.blockSignals(True)
        try:
            combo.clear()
            combo.addItems(items)
            combo.setCurrentIndex(0 if items else -1)
            combo.setEnabled(enabled)
            combo.setFocusPolicy(focus_policy)
        finally:
            combo.blockSignals(False)

    def _unlock_qty_controls(*, focus_qty: bool = False) -> None:
        gate.set_locked(False)
        try:
            widgets['qty'].setEnabled(True)
            widgets['qty'].setReadOnly(False)
            widgets['qty'].setFocusPolicy(Qt.StrongFocus)
        except Exception:
            pass
        try:
            widgets['ok_btn'].setEnabled(True)
            widgets['ok_btn'].setFocusPolicy(Qt.StrongFocus)
        except Exception:
            pass
        if focus_qty:
            try:
                widgets['qty'].setFocus()
                QTimer.singleShot(0, widgets['qty'].setFocus)
            except Exception:
                pass

    def _set_gate_state(enabled: bool, result: dict = None):
        gate.set_locked(True)
        if enabled and result:
            unit = 'Kg' if (result.get('unit', '').lower() == 'kg') else 'Each'
            widgets['unit'].setProperty('product_unit', unit)
            widgets['qty'].setProperty('unit_price', result.get('price', 0))
            try:
                widgets['qty'].clear()
            except Exception:
                pass

            if unit == 'Kg':
                _set_combo_items([UNIT_PROMPT, 'KG', 'GRAM'], enabled=True, focus_policy=Qt.StrongFocus)
                try:
                    gate.hide_placeholders([widgets['qty']])
                except Exception:
                    pass
            else:
                _set_combo_items(['EACH'], enabled=False, focus_policy=Qt.NoFocus)
                _set_qty_placeholder()
                _unlock_qty_controls()
        else:
            widgets['unit'].setProperty('product_unit', '')
            widgets['qty'].setProperty('unit_price', 0)
            _set_combo_items([], enabled=False, focus_policy=Qt.NoFocus)
            try:
                widgets['qty'].clear()
            except Exception:
                pass
            try:
                gate.hide_placeholders([widgets['qty']])
            except Exception:
                pass

    _set_gate_state(False)

    # 4. Coordinator
    coord = FieldCoordinator(dlg)

    def _on_sync(result):
        _set_gate_state(bool(result), result)

    def _focus_after_product_sync():
        if _is_product_kg():
            widgets['unit'].setFocus()
            QTimer.singleShot(0, widgets['unit'].setFocus)
        else:
            _unlock_qty_controls(focus_qty=True)

    def _on_unit_changed(_index=None):
        if not _is_product_kg():
            return

        if _selected_kg_input_unit():
            _set_qty_placeholder()
            _unlock_qty_controls()
            try:
                widgets['qty'].clear()
            except Exception:
                pass
            _unlock_qty_controls(focus_qty=True)
            ui_feedback.set_status_label(widgets['status'], f"{_combo_text()} unit selected", ok=True)
        else:
            gate.set_locked(True)
            try:
                widgets['qty'].clear()
                gate.hide_placeholders([widgets['qty']])
            except Exception:
                pass

    try:
        widgets['unit'].currentIndexChanged.connect(_on_unit_changed)
    except Exception:
        pass

    def _quantity_for_current_unit() -> float:
        if _is_product_kg():
            if not _selected_kg_input_unit():
                raise ValueError("Select KG or GRAM")

            if _is_input_gram():
                text = widgets['qty'].text().strip()
                try:
                    raw_qty = float(text)
                except (ValueError, TypeError):
                    raise ValueError("Quantity must be a number")
                qty_kg = raw_qty / 1000.0
                ok, err = input_validation.validate_quantity(str(qty_kg), unit_type='kg')
                if not ok:
                    raise ValueError(err or "Invalid weight")
                return qty_kg

            return input_handler.handle_quantity_input(widgets['qty'], unit_type='kg')

        return input_handler.handle_quantity_input(widgets['qty'], unit_type='unit')

    # Code -> name
    coord.add_link(
        source=widgets['code'],
        target_map={'name': widgets['name_srch']},
        lookup_fn=lambda val: input_handler.get_coordinator_lookup(val, 'code'),
        next_focus=_focus_after_product_sync,
        status_label=widgets['status'],
        on_sync=_on_sync,
        auto_jump=False,
    )

    # Name -> code
    coord.add_link(
        source=widgets['name_srch'],
        target_map={'code': widgets['code']},
        lookup_fn=lambda val: input_handler.get_coordinator_lookup(val, 'name'),
        next_focus=_focus_after_product_sync,
        status_label=widgets['status'],
        on_sync=_on_sync,
        auto_jump=False,
    )

    coord.add_link(
        source=widgets['qty'],
        next_focus=widgets['ok_btn'],
        status_label=widgets['status'],
        swallow_empty=True,
        validate_fn=_quantity_for_current_unit
    )

    # Exclusive product search fields
    enforce_exclusive_lineedits(
        widgets['code'], widgets['name_srch'],
        on_switch_to_a=lambda: clear_display([widgets['qty'], widgets['unit']], widgets['status'], extra_post_clear=lambda: _set_gate_state(False)),
        on_switch_to_b=lambda: clear_display([widgets['qty'], widgets['unit']], widgets['status'], extra_post_clear=lambda: _set_gate_state(False))
    )

    # Name search suggestions
    product_names = [rec[0] for rec in (dbop.PRODUCT_CACHE or {}).values() if rec[0]]
    def _name_selected():
        try:
            coord._sync_fields(widgets['name_srch'])
        except Exception:
            pass
        try:
            _focus_after_product_sync()
        except Exception:
            pass

    input_handler.setup_name_search_lineedit(
        widgets['name_srch'], product_names,
        on_selected=_name_selected,
        trigger_on_finish=False,
    )

    try:
        widgets['code'].textEdited.connect(_clear_barcode_warning_when_code_cleared)
    except Exception:
        pass

    # Commit typed name search on Enter
    def _commit_name_srch() -> None:
        try:
            txt = widgets['name_srch'].text() or ''
        except Exception:
            txt = ''
        try:
            result = input_handler.get_coordinator_lookup(txt, 'name')
        except Exception:
            result = None
        try:
            coord._sync_fields(widgets['name_srch'])
        except Exception:
            pass
        if result:
            try:
                _focus_after_product_sync()
            except Exception:
                pass

    try:
        widgets['name_srch'].returnPressed.connect(_commit_name_srch)
    except Exception:
        pass

    # Auto-clear quantity errors once valid
    coord.register_validator(
        widgets['qty'],
        _quantity_for_current_unit,
        status_label=widgets['status']
    )

    # 5. Execution
    def do_ok():
        try:
            # Validate product
            if not widgets['code'].text() or not widgets['name_srch'].text():
                raise ValueError("Select a product first")

            # Validate quantity
            product_unit = _product_unit() or 'Each'
            qty = _quantity_for_current_unit()

            # Prepare result
            dlg.manual_entry_result = {
                'product_code': widgets['code'].text(),
                'product_name': widgets['name_srch'].text(),
                'quantity': qty,
                'unit': product_unit,
                'unit_price': float(widgets['qty'].property('unit_price') or 0),
                'editable': True
            }
            set_dialog_info(dlg, f"{widgets['name_srch'].text()} of {qty} {product_unit} added. ")
            dlg.accept()
        except ValueError as e:
            ui_feedback.set_status_label(widgets['status'], str(e), ok=False)

    def do_cancel():
        set_dialog_info(dlg, "Manual entry cancelled.")
        dlg.reject()

    widgets['ok_btn'].clicked.connect(do_ok)
    widgets['cancel_btn'].clicked.connect(do_cancel)
    if widgets.get('close_btn') is not None:
        widgets['close_btn'].clicked.connect(do_cancel)

    # 6. Initialization
    def barcode_override(barcode):
        le = widgets['code']
        if le:
            le.setText(barcode)
            coord._sync_fields(le)
        return True

    try:
        dlg.barcode_override_handler = barcode_override
    except Exception:
        pass

    widgets['code'].setFocus()
    return dlg

def _create_manual_entry_fallback_ui(parent):
    """Generates the QDialog and the widgets dictionary manually."""
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QComboBox
    from PyQt5.QtGui import QFont

    dlg = QDialog(parent)
    dlg.setFixedSize(500, 400)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
    dlg.setModal(True)

    f_base = QFont(); f_base.setPointSize(12); f_base.setBold(True)
    dlg.setFont(f_base)

    layout = QVBoxLayout(dlg)
    
    dlg.setStyleSheet("background-color: beige;")
    header = QLabel("MANUAL ENTRY (FALLBACK)")
    header.setAlignment(Qt.AlignCenter)
    header.setStyleSheet("font-size: 16pt; color: #991b1b;; font-weight: bold;")
    layout.addWidget(header)

    info = QLabel("UI failure. Check Error log.")
    info.setAlignment(Qt.AlignCenter)
    info.setStyleSheet("font-size: 12pt; color: #4b5563; font-weight: bold;")
    layout.addWidget(info)

    grid = QGridLayout()
    widgets = {
        'code': QLineEdit(), 'name_srch': QLineEdit(), 
        'unit': QComboBox(), 'qty': QLineEdit(),
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

    widgets['status'].setStyleSheet("color: red; font-size: 10pt;")
    widgets['status'].setAlignment(Qt.AlignCenter)
    layout.addWidget(widgets['status'])

    btns = QHBoxLayout()
    btn_style = "font-size: 16pt; font-weight: bold; min-height: 60px; color: white; border-radius: 4px;"
    widgets['ok_btn'].setStyleSheet(f"background-color: #388e3c; {btn_style}")
    widgets['cancel_btn'].setStyleSheet(f"background-color: #d32f2f; {btn_style}")
    btns.addWidget(widgets['ok_btn']); btns.addWidget(widgets['cancel_btn'])
    layout.addLayout(btns)

    return dlg, widgets
