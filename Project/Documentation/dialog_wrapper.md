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
DialogWrapper.open_standard_dialog() or open_product_dialog()
    ↓ Wrapper handles: exec_(), sizing, centering, cleanup
```

**Before:** Mixed Case A (wrapper exec) and Case B (dialog exec)
**After:** Unified Case A (wrapper always controls exec)

---

## Class: DialogWrapper

Location: `modules/wrappers/dialog_wrapper.py`

### Constructor

```python
def __init__(self, main_window):
    self.main = main_window
```

### Helper Functions

- `_show_overlay()` - Shows overlay (dims background)
- `_hide_overlay()` - Hides overlay
- `_block_scanner()` - Blocks barcode scanner during dialog
- `_unblock_scanner()` - Re-enables barcode scanner
- `_restore_focus()` - Restores focus to sales table
- `_size_and_center(dlg, width_ratio=0.45, height_ratio=0.4)` - Sizes and centers dialog
- `_create_cleanup(on_finish=None)` - Factory for cleanup callback

---

## Main Wrapper Functions

### `open_standard_dialog(dialog_func, width_ratio=0.45, height_ratio=0.4, on_finish=None, *args, **kwargs)`

Universal wrapper for all standard dialogs.

**Execution:**
1. Show overlay, block scanner
2. Call dialog function → get QDialog
3. Size and center dialog
4. Connect cleanup to finished signal
5. Call `dlg.exec_()`
6. On close: hide overlay, unblock scanner, restore focus, call optional on_finish

**Example:**
```python
def open_logout_menu_dialog(self):
    self.dialog_wrapper.open_standard_dialog(
        launch_logout_dialog,
        on_finish=self._perform_logout
    )

def open_admin_menu_dialog(self):
    self.dialog_wrapper.open_standard_dialog(
        launch_admin_dialog,
        current_user='Admin',
        is_admin=True
    )
```

### `open_product_dialog(dialog_func, **kwargs)`

Special wrapper for product_menu (allows barcode input).

**Differences:**
- Scanner is **NOT blocked** (allows barcode scanning)
- Resets barcode override on close
- Uses 10ms timer-deferred focus restoration

**Example:**
```python
def open_product_menu_dialog(self, **kwargs):
    self.dialog_wrapper.open_product_dialog(launch_product_dialog, **kwargs)
```

---

## Dialog Categorization

### Standard Dialogs (use `open_standard_dialog()`)

| Dialog | Blocks Scanner |
|--------|----------------|
| logout_menu | Yes |
| admin_menu | Yes |
| greeting_menu | Yes |
| devices_menu | Yes |
| reports_menu | Yes |
| vegetable_menu | Yes |
| vegetable_entry | Yes |
| manual_entry | Yes |
| onhold | Yes |
| viewhold | Yes |
| cancelsale | Yes |

### Product Dialog (use `open_product_dialog()`)

| Dialog | Blocks Scanner |
|--------|----------------|
| product_menu | **No** |

---

## Integration with main.py

```python
class MainLoader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.overlay_manager = OverlayManager(self)
        self.dialog_wrapper = DialogWrapper(self)
```

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

_Last updated: December 15, 2025_
