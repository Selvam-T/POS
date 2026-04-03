import os
import csv
from datetime import datetime
from pathlib import Path
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QWidget, QPushButton, QLineEdit, QToolButton, QLabel, QTabWidget, QListWidget
from modules.ui_utils.error_logger import log_error
from modules.ui_utils.dialog_utils import build_dialog_from_ui, require_widgets, set_dialog_error, set_dialog_info, report_exception_post_close, build_error_fallback_dialog
from modules.ui_utils.focus_utils import FieldCoordinator, FocusGate, set_initial_focus
from modules.ui_utils import input_handler
from modules.db_operation.db import get_conn
from modules.db_operation.products_repo import get_product_list_schema_and_rows
from modules.db_operation.users_repo import verify_password, update_password, clear_must_change_password
from modules.ui_utils import ui_feedback
from modules.menu.screen2_ads_helper import Screen2AdsController

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(THIS_DIR))
UI_DIR = os.path.join(BASE_DIR, 'ui')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
QSS_PATH = os.path.join(ASSETS_DIR, 'dialog.qss')


# Build and return the admin settings dialog.
def launch_admin_dialog(host_window, user_id: int | None = None, is_admin: bool = True, force_change: bool = False):
    """Open the Admin Settings dialog.

    Args:
        host_window: Main window instance.
        user_id: Logged-in user id for password verification and update.
        is_admin: If False, dialog is read-only.

    Returns:
        QDialog instance.
    """
    # Use shared dialog builder for consistent behavior
    ui_path = os.path.join(UI_DIR, 'admin_menu.ui')
    dlg = build_dialog_from_ui(ui_path, host_window=host_window, dialog_name='admin_menu', qss_path=QSS_PATH)
    if dlg is None:
        return build_error_fallback_dialog(host_window, 'Admin Settings', QSS_PATH)

    # Resolve required widgets (hard-fail if UI changed)
    try:
        widgets = require_widgets(dlg, {
            'tabWidget': (QTabWidget, 'tabWidget'),
            'adminCur': (QLineEdit, 'adminCurPwdLineEdit'),
            'adminNew': (QLineEdit, 'adminNewPwdLineEdit'),
            'adminEye': (QToolButton, 'adminToolBtn'),
            'adminEye2': (QToolButton, 'adminToolBtn2'),
            'adminStatus': (QLabel, 'adminStatusLabel'),
            'btnAdminOk': (QPushButton, 'btnAdminOk'),
            'btnAdminCancel': (QPushButton, 'btnAdminCancel'),
            'staffCur': (QLineEdit, 'staffCurPwdLineEdit'),
            'staffNew': (QLineEdit, 'staffNewPwdLineEdit'),
            'staffEye': (QToolButton, 'staffToolBtn'),
            'staffEye2': (QToolButton, 'staffToolBtn2'),
            'staffStatus': (QLabel, 'staffStatusLabel'),
            'btnStaffOk': (QPushButton, 'btnStaffOk'),
            'btnStaffCancel': (QPushButton, 'btnStaffCancel'),
            'screen2List': (QListWidget, 'screen2ListWidget'),
            'screen2Preview': (QLabel, 'screen2PreviewLabel'),
            'screen2Count': (QLabel, 'screen2CountLabel'),
            'screen2Status': (QLabel, 'screen2StatusLabel'),
            'screen2Add': (QPushButton, 'addScreen2Btn'),
            'screen2Remove': (QPushButton, 'removeScreen2Btn'),
            'screen2Up': (QPushButton, 'upScreen2Btn'),
            'screen2Down': (QPushButton, 'downScreen2Btn'),

            # EXPORT
            'csvExportBtn': (QPushButton, 'csvExportBtn'),
            'xlsxExportBtn': (QPushButton, 'xlsxExportBtn'),
            'sqlExportBtn': (QPushButton, 'sqlExportBtn'),
            'exportStatusLabel': (QLabel, 'exportStatusLabel'),

            'customClose': (QPushButton, 'customCloseBtn'),
        }, hard_fail=True)
    except Exception as e:
        try:
            log_error(f"admin_menu: require_widgets failed: {e}")
        except Exception:
            pass
        return dlg

    tabWidget = widgets['tabWidget']
    adminCur = widgets['adminCur']
    adminNew = widgets['adminNew']
    adminEye = widgets['adminEye']
    adminEye2 = widgets['adminEye2']
    adminStatus = widgets['adminStatus']
    btnAdminOk = widgets['btnAdminOk']
    btnAdminCancel = widgets['btnAdminCancel']
    staffCur = widgets['staffCur']
    staffNew = widgets['staffNew']
    staffEye = widgets['staffEye']
    staffEye2 = widgets['staffEye2']
    staffStatus = widgets['staffStatus']
    btnStaffOk = widgets['btnStaffOk']
    btnStaffCancel = widgets['btnStaffCancel']
    screen2List = widgets['screen2List']
    screen2Preview = widgets['screen2Preview']
    screen2Count = widgets['screen2Count']
    screen2Status = widgets['screen2Status']
    screen2Add = widgets['screen2Add']
    screen2Remove = widgets['screen2Remove']
    screen2Up = widgets['screen2Up']
    screen2Down = widgets['screen2Down']
    csvExportBtn = widgets['csvExportBtn']
    xlsxExportBtn = widgets['xlsxExportBtn']
    sqlExportBtn = widgets['sqlExportBtn']
    exportStatusLabel = widgets['exportStatusLabel']
    customClose = widgets.get('customClose')

    # Titlebar close
    if customClose is not None:
        try:
            # Use a lambda so the call resolves to the current `dlg.reject` (may be wrapped later).
            customClose.clicked.connect(lambda: dlg.reject())
        except Exception:
            pass

    # Toggle visibility buttons
    # Wire password visibility toggle.
    def _wire_eye(btn, le):
        try:
            btn.toggled.connect(lambda checked: le.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password))
        except Exception:
            pass

    _wire_eye(adminEye, adminCur)
    _wire_eye(adminEye2, adminNew)
    _wire_eye(staffEye, staffCur)
    _wire_eye(staffEye2, staffNew)

    # Coordinator & gates
    fc = FieldCoordinator(dlg)

    # Fixed user ids for password change (documented invariant in DB seed)
    ADMIN_USER_ID = 1
    STAFF_USER_ID = 2

    # Determine user id for admin (prefer explicit arg; fallback to fixed id)
    try:
        admin_uid = int(user_id) if user_id is not None else ADMIN_USER_ID
    except Exception:
        admin_uid = ADMIN_USER_ID

    # Determine user id for staff (fixed id)
    staff_uid = STAFF_USER_ID

    # If forcing a password change, restrict UI to ADMIN tab and prevent cancel/close.
    if force_change:
        try:
            # Disable all tabs except the first (ADMIN) so user cannot switch away.
            for i in range(tabWidget.count()):
                tabWidget.setTabEnabled(i, i == 0)
        except Exception:
            pass
        # Disable cancel/close actions while in forced-change mode.
        try:
            btnAdminCancel.setEnabled(False)
        except Exception:
            pass
        try:
            btnStaffCancel.setEnabled(False)
        except Exception:
            pass
        try:
            if customClose is not None:
                customClose.setEnabled(False)
        except Exception:
            pass
        try:
            dlg.reject = lambda: None
        except Exception:
            pass

    def _setup_password_tab(*, cur_edit, new_edit, ok_btn, status_lbl, user_id: int | None):
        # Focus gate: lock new-password and OK button until current password validated
        try:
            new_edit.setReadOnly(False)
        except Exception:
            pass
        gate = FocusGate([new_edit, ok_btn], lock_enabled=True, lock_read_only=True)
        gate.remember()
        try:
            gate.remember_placeholders([new_edit])
            gate.hide_placeholders([new_edit])
        except Exception:
            pass
        gate.lock()

        # Validate current password before unlocking new password.
        def _validate_current():
            txt = cur_edit.text() or ''
            if not txt:
                raise ValueError('Enter current password')
            try:
                ok = False
                if user_id is not None:
                    ok = verify_password(user_id, txt)
                if not ok:
                    raise ValueError('Invalid current password')
            except ValueError:
                raise
            except Exception:
                raise ValueError('Password check failed')
            try:
                gate.unlock()
                gate.restore_placeholders([new_edit])
            except Exception:
                pass
            return True

        # Validate new password using shared rules.
        def _validate_new():
            try:
                return input_handler.handle_password_input(new_edit)
            except ValueError:
                raise
            except Exception:
                raise ValueError('Invalid new password')

        fc.register_validator(cur_edit, _validate_current, status_lbl)
        fc.add_link(cur_edit, target_map={}, next_focus=new_edit, status_label=status_lbl, validate_fn=_validate_current, auto_jump=True)

        fc.register_validator(new_edit, _validate_new, status_lbl)
        fc.add_link(new_edit, target_map={}, next_focus=ok_btn, status_label=status_lbl, validate_fn=_validate_new, auto_jump=True)

        def _on_ok():
            try:
                _validate_current()
                new_pwd = _validate_new()
            except ValueError as e:
                fc.set_error(new_edit if 'new' in str(e).lower() else cur_edit, str(e), status_label=status_lbl)
                return

            try:
                if user_id is None:
                    raise Exception('User id not found')
                # UNCOMMENT next line to simulate raise Exception('Simulated update failure')
                #raise Exception('Simulated update failure')
                update_password(user_id, new_pwd)
                # If this dialog was opened to force a password change, clear the DB flag.
                try:
                    if force_change:
                        clear_must_change_password(user_id)
                except Exception:
                    pass
            except Exception as exc:
                report_exception_post_close(dlg, 'update_password', exc, user_message='Failed to update password', level='error')
                dlg.reject()
                return

            set_dialog_info(dlg, 'Password updated successfully')
            dlg.accept()

        try:
            ok_btn.clicked.connect(_on_ok)
        except Exception:
            pass

    _setup_password_tab(cur_edit=adminCur, new_edit=adminNew, ok_btn=btnAdminOk, status_lbl=adminStatus, user_id=admin_uid)
    _setup_password_tab(cur_edit=staffCur, new_edit=staffNew, ok_btn=btnStaffOk, status_lbl=staffStatus, user_id=staff_uid)

    # Screen 2 ads tab wiring (independent helper).
    try:
        screen2_ctrl = Screen2AdsController(
            list_widget=screen2List,
            preview_label=screen2Preview,
            count_label=screen2Count,
            status_label=screen2Status,
            add_btn=screen2Add,
            remove_btn=screen2Remove,
            up_btn=screen2Up,
            down_btn=screen2Down,
        )
        # Keep a reference so slots remain alive.
        try:
            dlg._screen2_ctrl = screen2_ctrl
        except Exception:
            pass
        screen2_ctrl.wire()
        screen2_ctrl.refresh(select_index=0)
    except Exception:
        try:
            ui_feedback.set_status_label(screen2Status, 'Screen 2 setup failed.', ok=False)
        except Exception:
            pass

    # EXPORT tab wiring (product_list exports only).
    def _exports_dir() -> Path:
        # User-requested location: Documents/POS_Exports
        return Path.home() / 'Documents' / 'POS_Exports'

    def _timestamp_for_filename() -> str:
        # Windows-safe replacement for requested hh:mm format.
        return datetime.now().strftime('%d%b%Y_%H-%M').lower()

    def _base_export_file_stem() -> str:
        return f"product_list_{{kind}}_{_timestamp_for_filename()}"

    def _ensure_exports_folder() -> Path:
        out_dir = _exports_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    def _set_export_status(msg: str, ok: bool) -> None:
        try:
            ui_feedback.set_status_label(exportStatusLabel, msg, ok=ok, duration=3500 if ok else 0)
        except Exception:
            pass

    def _fetch_product_rows_and_headers():
        # Use repo helper to fetch headers and rows so SQL lives in `products_repo`.
        try:
            _, headers, rows = get_product_list_schema_and_rows()
            return headers, rows
        except Exception:
            return [], []

    def _export_csv() -> None:
        try:
            out_dir = _ensure_exports_folder()
            file_name = _base_export_file_stem().format(kind='csv') + '.csv'
            out_path = out_dir / file_name

            headers, rows = _fetch_product_rows_and_headers()
            with out_path.open('w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                if headers:
                    writer.writerow(headers)
                for r in rows:
                    writer.writerow(list(r))

            _set_export_status(f'CSV file exported to {out_dir}', ok=True)
        except Exception as e:
            log_error(f'admin_menu export CSV failed: {e}')
            _set_export_status('CSV export failed.', ok=False)

    def _export_xlsx() -> None:
        try:
            try:
                import importlib
                _openpyxl = importlib.import_module('openpyxl')
                Workbook = getattr(_openpyxl, 'Workbook')
            except Exception as imp_err:
                raise RuntimeError('Missing dependency: openpyxl') from imp_err

            out_dir = _ensure_exports_folder()
            file_name = _base_export_file_stem().format(kind='xlsx') + '.xlsx'
            out_path = out_dir / file_name

            headers, rows = _fetch_product_rows_and_headers()
            wb = Workbook()
            ws = wb.active
            ws.title = 'Product_list'
            if headers:
                ws.append(headers)
            for r in rows:
                ws.append(list(r))
            wb.save(str(out_path))

            _set_export_status(f'XLSX file exported to {out_dir}', ok=True)
        except Exception as e:
            log_error(f'admin_menu export XLSX failed: {e}')
            _set_export_status('XLSX export failed.', ok=False)

    def _sql_literal(v):
        if v is None:
            return 'NULL'
        if isinstance(v, bool):
            return '1' if v else '0'
        if isinstance(v, (int, float)):
            return str(v)
        s = str(v).replace("'", "''")
        return f"'{s}'"

    def _export_sql() -> None:
        try:
            out_dir = _ensure_exports_folder()
            file_name = _base_export_file_stem().format(kind='sql') + '.sql'
            out_path = out_dir / file_name

            create_sql, headers, rows = get_product_list_schema_and_rows()
            if not create_sql:
                raise RuntimeError('Product_list schema not found')

            with out_path.open('w', encoding='utf-8', newline='\n') as f:
                f.write('-- Product_list export\n')
                f.write(f'-- Generated: {datetime.now().isoformat(timespec="seconds")}\n\n')
                f.write('BEGIN TRANSACTION;\n')
                f.write(f'{create_sql};\n')
                if headers:
                    cols_sql = ', '.join([f'"{h}"' for h in headers])
                    for r in rows:
                        vals_sql = ', '.join([_sql_literal(v) for v in list(r)])
                        f.write(f'INSERT INTO "Product_list" ({cols_sql}) VALUES ({vals_sql});\n')
                f.write('COMMIT;\n')

            _set_export_status(f'SQL file exported to {out_dir}', ok=True)
        except Exception as e:
            log_error(f'admin_menu export SQL failed: {e}')
            _set_export_status('SQL export failed.', ok=False)

    try:
        csvExportBtn.clicked.connect(_export_csv)
        xlsxExportBtn.clicked.connect(_export_xlsx)
        sqlExportBtn.clicked.connect(_export_sql)
    except Exception:
        pass

    # Land focus on CSV export button when EXPORT tab is selected.
    def _focus_export_btn_on_tab_change(index: int) -> None:
        try:
            tab = tabWidget.widget(index)
            tab_name = tab.objectName() if tab is not None else ''
        except Exception:
            tab_name = ''
        if tab_name == 'tabExport':
            try:
                csvExportBtn.setFocus()
            except Exception:
                pass

    try:
        tabWidget.currentChanged.connect(_focus_export_btn_on_tab_change)
        _focus_export_btn_on_tab_change(tabWidget.currentIndex())
    except Exception:
        pass

    # Cancel/Close buttons
    try:
        # Preserve original reject so we can call it directly from handlers.
        orig_reject = getattr(dlg, 'reject', None)
    except Exception:
        orig_reject = None

    # Only wrap dialog reject to provide a generic post-close message when
    # not forcing a password change (force_change disables reject earlier).
    try:
        if not force_change and callable(orig_reject):
            def _reject_with_default_msg():
                try:
                    if not getattr(dlg, 'main_status_msg', None):
                        set_dialog_info(dlg, 'Admin dialog closed.', duration=3000)
                except Exception:
                    pass
                try:
                    orig_reject()
                except Exception:
                    pass
            dlg.reject = _reject_with_default_msg
    except Exception:
        pass

    try:
        def _on_admin_cancel():
            try:
                set_dialog_info(dlg, 'Admin password change cancelled.', duration=3000)
            except Exception:
                pass
            try:
                if callable(orig_reject):
                    orig_reject()
                else:
                    dlg.reject()
            except Exception:
                pass

        def _on_staff_cancel():
            try:
                set_dialog_info(dlg, 'Staff password change cancelled.', duration=3000)
            except Exception:
                pass
            try:
                if callable(orig_reject):
                    orig_reject()
                else:
                    dlg.reject()
            except Exception:
                pass

        btnAdminCancel.clicked.connect(_on_admin_cancel)
        btnStaffCancel.clicked.connect(_on_staff_cancel)
    except Exception:
        pass

    # Set initial focus to admin current password field and select all
    try:
        set_initial_focus(dlg, tab_widget=tabWidget, tab_name='ADMIN', first_widget=adminCur)
    except Exception:
        try:
            adminCur.setFocus()
        except Exception:
            pass

    return dlg


# Backward-compatible alias (older imports/call-sites).
open_admin_dialog = launch_admin_dialog
