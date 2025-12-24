# Dialog Wrapper Architecture

## Overview

The `DialogWrapper` class (`modules/wrappers/dialog_wrapper.py`) provides unified management of modal dialogs across the POS application. It handles overlay dimming, barcode scanner blocking, dialog sizing/centering, and focus restoration.

**Key benefit:** Eliminates 40+ lines of duplicated cleanup code across all dialog launchers.

---

## Architecture

### Unified Pattern: Case A Only

All dialogs now follow the **Case A pattern**:

```
Dialog Controller (e.g., logout_menu.py)
    ↓ Creates and returns QDialog
    ↓
DialogWrapper.open_dialog_scanner_blocked() or open_dialog_scanner_enabled()
    ↓ Wrapper handles: exec_(), sizing, centering, cleanup
```

**Before:** Mixed Case A (wrapper exec) and Case B (dialog exec)
**After:** Unified Case A (wrapper always controls exec)

---

## Class: DialogWrapper

Location: `modules/wrappers/dialog_wrapper.py`

### Dialog Size Configuration

Dialog sizes are controlled by the `DIALOG_RATIOS` dictionary, where each dialog maps to `(width_ratio, height_ratio)` as fractions of the maximized main window:

```python
DIALOG_RATIOS = {
    'vegetable_entry': (0.5, 0.7),
    'manual_entry': (0.4, 0.3),
    'logout_menu': (0.4, 0.4),
    'admin_menu': (0.7, 0.7),
    'history_menu': (0.7, 0.7),
    'reports_menu': (0.7, 0.7),
    'greeting_menu': (0.7, 0.7),
    'product_menu': (0.7, 0.7),
    'vegetable_menu': (0.7, 0.7),
    'on_hold': (0.7, 0.7),
    'view_hold': (0.7, 0.7),
    'cancel_sale': (0.7, 0.7),
}
```

Actual dialog size respects the `minimumSize` constraint from the `.ui` file as a safety floor.

### Constructor

```python
def __init__(self, main_window):
    self.main = main_window
```

### Helper Functions

- `_show_overlay()` / `_hide_overlay()` - Overlay dimming
- `_block_scanner()` / `_unblock_scanner()` - Scanner input blocking
- `_restore_focus()` - Focus restoration to main window
- `_refocus_sales_table()` - Focus to sales table
- `_clear_scanner_override()` - Clears product menu barcode override
- `_setup_dialog_geometry(dlg, width_ratio, height_ratio)` - Sizes and centers dialog based on ratios
- `_create_cleanup(on_finish=None)` - Factory for dialog close callbacks

---

## Main Wrapper Functions

### `open_dialog_scanner_blocked(dialog_func, dialog_key=None, on_finish=None, *args, **kwargs)`

Universal wrapper for all standard dialogs.

**Behavior:**
1. Show overlay and block scanner
2. Call dialog function → get QDialog
3. Look up size ratios from `DIALOG_RATIOS` using `dialog_key`
4. Size and center dialog based on ratios (respecting minimumSize floor)
5. Connect cleanup to finished signal
6. Execute dialog
7. On close: hide overlay, unblock scanner, restore focus, call optional on_finish

**Example:**
```python
def open_logout_menu_dialog(self):
    self.dialog_wrapper.open_dialog_scanner_blocked(
        launch_logout_dialog,
        dialog_key='logout_menu',
        on_finish=self._perform_logout
    )

def open_admin_menu_dialog(self):
    self.dialog_wrapper.open_dialog_scanner_blocked(
        launch_admin_dialog,
        dialog_key='admin_menu',
        current_user='Admin',
        is_admin=True
    )
```

### `open_dialog_scanner_enabled(dialog_func, dialog_key=None, **kwargs)`

Special wrapper for product_menu (allows barcode input during dialog).

**Differences from standard:**
- Scanner is **NOT blocked** (allows barcode scanning in product code field)
- Resets barcode override on close
- Uses 10ms timer-deferred focus restoration

**Example:**
```python
def open_product_menu_dialog(self, **kwargs):
    self.dialog_wrapper.open_dialog_scanner_enabled(launch_product_dialog, dialog_key='product_menu', **kwargs)
```

---

## Dialog Categorization

### Standard Dialogs (use `open_dialog_scanner_blocked()`)

| Dialog | Width Ratio | Height Ratio | Blocks Scanner |
|--------|-------------|--------------|----------------|
| logout_menu | 0.4 | 0.4 | Yes |
| admin_menu | 0.7 | 0.7 | Yes |
| greeting_menu | 0.7 | 0.7 | Yes |
| history_menu | 0.7 | 0.7 | Yes |
| reports_menu | 0.7 | 0.7 | Yes |
| vegetable_menu | 0.7 | 0.7 | Yes |
| vegetable_entry | 0.5 | 0.7 | Yes |
| manual_entry | 0.4 | 0.3 | Yes |
| on_hold | 0.7 | 0.7 | Yes |
| view_hold | 0.7 | 0.7 | Yes |
| cancel_sale | 0.7 | 0.7 | Yes |

### Product Dialog (use `open_dialog_scanner_enabled()`)

| Dialog | Width Ratio | Height Ratio | Blocks Scanner |
|--------|-------------|--------------|----------------|
| product_menu | 0.7 | 0.7 | **No** |

**Note:** All ratios are fractions of the maximized main window dimensions. Actual size respects minimumSize from `.ui` file as a safety floor.

---

## Integration with main.py

```python
class MainLoader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.overlay_manager = OverlayManager(self)
        self.dialog_wrapper = DialogWrapper(self)
        # ... setup_sales_frame() calls ...
        # Uses _rebuild_mixed_editable_table for unit-aware row states
```

### Vegetable Entry Dialog Integration

The `open_vegetable_entry_dialog` callback combines existing sales rows with new vegetable entries:

```python
def open_vegetable_entry_dialog(self):
    def callback(veg_rows):
        if not veg_rows:
            return
        
        # Extract existing rows WITH editable states
        existing_rows = []
        for row in range(self.sales_table.rowCount()):
            qty_widget = self.sales_table.cellWidget(row, 2)
            row_editable = not qty_widget.isReadOnly()  # Preserve KG/EACH state
            
            row_data = {
                'product': self.sales_table.item(row, 1).text(),
                'quantity': qty_widget.property('numeric_value') or float(qty_widget.text()),
                'unit_price': float(self.sales_table.item(row, 3).text()),
                'editable': row_editable,
            }
            
            if qty_widget.isReadOnly() and qty_widget.text():
                row_data['display_text'] = qty_widget.text()  # Preserve "600 g" formatting
            
            existing_rows.append(row_data)
        
        # Combine and rebuild with per-row editable states
        combined = existing_rows + veg_rows
        _rebuild_mixed_editable_table(self.sales_table, combined)
    
    self.dialog_wrapper.open_dialog_scanner_blocked(
        launch_vegetable_entry_dialog,
        dialog_key='vegetable_entry',
        on_finish=callback
    )
```

**Key points:**
- Preserves editable state from existing rows (KG items stay read-only)
- Uses `_rebuild_mixed_editable_table()` to handle mixed KG/EACH rows
- Maintains display formatting (e.g., "600 g" for weights)

---

## Dialog Controller Pattern

All dialog controllers must return a QDialog:

```python
def open_logout_dialog(main_window):
    dlg = QDialog(main_window)
    # ... setup ...
    return dlg  # Wrapper calls exec_()
```

---

## Benefits

- **Unified pattern:** All dialogs follow same approach
- **Eliminated duplication:** ~90 lines of cleanup code consolidated
- **Single source of truth:** Overlay/scanner/focus logic in one place
- **Signal-based cleanup:** No race conditions or timing issues
- **Extensible:** Easy to add new dialogs or callbacks

---

## Known Issues & Fixes

### Barcode Scanning with DialogWrapper Integration

**Issue:** When integrating DialogWrapper, ensure all dialog controller functions properly pass keyword arguments when calling internal functions. Specifically, when `handle_barcode_scanned()` calls `_add_product_row()`, the status_bar parameter must be passed as a keyword argument to avoid positional argument mismatches.

**Status:** ✅ Fixed in `modules/sales/salesTable.py` line 570

---

## Testing Checklist

- [ ] Admin dialog: open → OK → overlay gone, focus returns
- [ ] Logout dialog: open → OK → app exits
- [ ] Product menu: open → scan barcode → works
- [ ] Barcode scan: 1st scan adds row correctly with qty=1
- [ ] Barcode scan: 2nd+ scans increment quantity properly
- [ ] All dialogs: X button closes properly
- [ ] Sales table regains focus after any dialog

---

## Related Files

- `main.py` - MainLoader, dialog launchers
- `modules/wrappers/dialog_wrapper.py` - DialogWrapper class
- `modules/menu/*` - Dialog controllers
- `modules/sales/*` - Sales dialog controllers and salesTable utilities
- `modules/ui_utils/overlay_manager.py` - Overlay management
- `modules/devices/barcode_manager.py` - Scanner blocking

---

_Last updated: December 17, 2025_
