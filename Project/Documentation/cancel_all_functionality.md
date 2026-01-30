# Cancel All Functionality Documentation

**Location:** `modules/sales/cancel_sale.py` and `main.py`

## Overview

The Cancel All feature provides a safe way for users to clear the entire sales table, resetting the transaction to a clean state. It includes a confirmation dialog to prevent accidental data loss.

---

## User Workflow

1. **User clicks "Cancel All" button** in the sales frame (located in `receiptContainer`)
2. **Confirmation dialog appears** with scanner blocked and overlay dimmed
3. **User chooses:**
   - **CONFIRM:** Clears all rows, resets total to $0.00, closes dialog
   - **CANCEL:** Does nothing, closes dialog, sales table remains unchanged

---

## Implementation Details

### Dialog Controller
**File:** `modules/sales/cancel_sale.py`

```python
def launch_cancelsale_dialog(host_window):
    """Open Cancel Sale confirmation dialog.
    If the UI file fails to load, logs error and shows a minimal fallback dialog.
    Returns:
        QDialog with Accepted/Rejected status based on user choice
    """
```

- Loads UI from `cancel_sale.ui` if available; otherwise, logs error and shows fallback dialog.
- Fallback dialog includes a confirmation message and two styled buttons (Cancel, Yes, Clear All).
- Error is logged to `log/error.log` with timestamp using shared logger.
- Statusbar notification is shown to inform user when fallback is used.

### Main Window Handler
**File:** `main.py`

**Dialog Launcher:**
```python
def open_cancelsale_dialog(self):
    """Open Cancel Sale confirmation dialog."""
    self.dialog_wrapper.open_dialog_scanner_blocked(
        launch_cancelsale_dialog,
        dialog_key='cancel_sale',
        on_finish=lambda: self._clear_sales_table()
    )
```

**Post-Dialog Action:**
```python
def _clear_sales_table(self):
    """Clear all items from sales table and reset total to zero.
    
    Called after user confirms Cancel All action.
    """
```

**Actions performed on CONFIRM:**
1. Checks dialog result (`QDialog.Accepted`)
2. Clears all rows: `self.sales_table.setRowCount(0)`
3. Resets total to $0.00 via `recompute_total(self.sales_table)`
4. Updates bound `totalValue` label automatically

---

## Side Effects

### Immediate Effects:
- **Sales table:** All rows removed
- **Total display:** Shows `$ 0.00`
- **Product menu:** REMOVE/UPDATE tabs re-enable (no longer blocked by active sale)

### Future Considerations:
When payment frame is implemented, `_clear_sales_table()` should also:
- Clear payment input fields (CASH, NETS, PAYNOW, VOUCHER)
- Reset transaction ID/state
- Clear change calculation
- Reset payment validation states

Placeholder comment exists in code for future implementation.

---

## Dialog Wrapper Integration

**Pattern:** Follows same structure as logout, admin, reports dialogs

- **Scanner:** Blocked during dialog (prevents stray input)
- **Overlay:** Dims background to indicate modal state
- **Dialog key:** `'cancel_sale'` registered in wrapper
- **Size:** Default 70% width x 70% height (configured in dialog_wrapper.py)

---

## Code Organization

### Method Grouping in main.py:

```python
# ========== Sales Frame Dialog Handlers ==========
def open_cancelsale_dialog(self): ...

# ========== Post-Dialog Action Handlers ==========
def _clear_sales_table(self): ...
def _perform_logout(self): ...
```

**Why `_clear_sales_table()` is in main.py:**
- Needs access to `self.sales_table` (main window instance attribute)
- Needs access to `self.dialog_wrapper._last_dialog` (to check result)
- Operates on main window context (table, labels, future payment frame)
- Cannot be in `cancel_sale.py` without tight coupling

---

## Testing Checklist

✅ Click Cancel All → dialog opens with overlay  
✅ Click CANCEL → dialog closes, table unchanged  
✅ Click CONFIRM → table clears, total shows $0.00  
✅ Scanner blocked during dialog  
✅ Product menu tabs re-enable after clear  
✅ Add items after clear works normally  

---

## Related Files


- `ui/cancel_sale.ui` - Dialog UI definition
- `modules/sales/cancel_sale.py` - Dialog controller and fallback logic
- `modules/ui_utils/error_logger.py` - Shared error logger
- `main.py` - Dialog launcher and post-action handler
- `modules/sales/sales_frame_setup.py` - Button wiring (line ~90)
- `modules/table/table_operations.py` - `recompute_total()` function

---

*Last updated: December 22, 2025*
