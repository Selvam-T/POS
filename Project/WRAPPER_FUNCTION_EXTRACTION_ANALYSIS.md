# Dialog Wrapper Function Extraction Analysis

## Executive Summary

Your wrapper functions contain **8-10 distinct, reusable subfunctions** that are currently embedded or duplicated across three wrapper implementations. Extracting these into helper methods would:
- **Eliminate code duplication** (~40-50% reduction in wrapper code)
- **Improve maintainability** (single source of truth for each responsibility)
- **Enable composition** (wrappers become thin orchestrators)
- **Simplify testing** (test individual concerns separately)

---

## Current State: Embedded & Duplicated Logic

### Wrapper 1: `open_dialog_wrapper()` - Cases A & B
```python
def open_dialog_wrapper(self, dialog_func, width_ratio=0.45, height_ratio=0.4, *args, **kwargs):
    # Step 1: Show overlay + block scanner
    # Step 2: Call dialog function
    # Step 3: Type-check to route to Case A or B
    #   Case A:
    #     - Size and center dialog
    #     - Connect cleanup signal
    #     - Execute dialog
    #   Case B:
    #     - Just cleanup and restore focus
    # Step 4: Exception handling with cleanup
```

### Wrapper 2: `open_product_menu_dialog()`
```python
def open_product_menu_dialog(self, *args, **kwargs):
    # Step 1: Show overlay
    # Step 2: Call product dialog (runs exec_ internally)
    # Step 3: Hide overlay
    # Step 4: Process Qt events
    # Step 5: Clear barcode override
    # Step 6: Restore focus with QTimer delay
```

### Issue: Common Tasks Scattered
| Task | open_dialog_wrapper | open_product_menu_dialog | Duplication |
|------|-------------------|-------------------------|-------------|
| Show overlay | ✓ | ✓ | Yes |
| Block scanner | ✓ | ✗ | No (product needs it?) |
| Hide overlay | ✓ | ✓ | Yes |
| Unblock scanner | ✓ | ✗ | No |
| Restore focus | ✓ | ✓ | Yes (different approaches) |
| Exception handling | ✓ | ✓ | Yes |
| Barcode cleanup | ✗ | ✓ | No (not in main wrapper) |

---

## Identified Extractable Subfunctions

### 1️⃣ **Scanner Management Functions**

#### `_start_scanner_block()` → Extracted
**Current Location:** Inline in `open_dialog_wrapper()` (lines 133-136)
```python
# CURRENT - Duplicated & Inline
self.overlay_manager.toggle_dim_overlay(True)
try:
    if hasattr(self, 'barcode_manager'):
        self.barcode_manager._start_scanner_modal_block()
except Exception:
    pass
```

**Extracted Function:**
```python
def _start_scanner_block(self) -> bool:
    """Block barcode scanner during modal dialog.
    
    Returns:
        bool: True if scanner was blocked successfully, False otherwise.
    """
    try:
        if hasattr(self, 'barcode_manager'):
            self.barcode_manager._start_scanner_modal_block()
            return True
    except Exception:
        pass
    return False
```

**Usage:** Called once before dialog opens.
**Benefits:** 
- Single line call instead of 5 lines
- Consistent error handling
- Semantic clarity (reads like intent)

---

#### `_end_scanner_block()` → Extracted
**Current Location:** Duplicated in 4+ places (lines 153-156, 163-166, 174-177, 203)
```python
# CURRENT - Duplicated in 4 locations
try:
    if hasattr(self, 'barcode_manager'):
        self.barcode_manager._end_scanner_modal_block()
except Exception:
    pass
```

**Extracted Function:**
```python
def _end_scanner_block(self) -> bool:
    """Unblock barcode scanner after modal dialog closes.
    
    Returns:
        bool: True if unblocked successfully, False otherwise.
    """
    try:
        if hasattr(self, 'barcode_manager'):
            self.barcode_manager._end_scanner_modal_block()
            return True
    except Exception:
        pass
    return False
```

**Current Duplication:** 4 separate try-except blocks doing identical work
**Extracted Count:** Down to 1 definition, 4 calls

---

### 2️⃣ **Overlay Management Functions**

#### `_show_dialog_overlay()` → Extracted
**Current Location:** Inline in multiple wrappers
```python
# CURRENT
self.overlay_manager.toggle_dim_overlay(True)
```

**Extracted Function:**
```python
def _show_dialog_overlay(self) -> bool:
    """Show dimming overlay before opening dialog.
    
    Returns:
        bool: True if overlay shown successfully.
    """
    try:
        self.overlay_manager.toggle_dim_overlay(True)
        return True
    except Exception:
        return False
```

**Benefit:** Future-proof if overlay behavior changes (e.g., animation, different overlay types)

---

#### `_hide_dialog_overlay()` → Extracted
**Current Location:** Duplicated in 3 locations
```python
# CURRENT - Duplicated
self.overlay_manager.toggle_dim_overlay(False)
```

**Extracted Function:**
```python
def _hide_dialog_overlay(self) -> bool:
    """Hide dimming overlay after dialog closes.
    
    Returns:
        bool: True if overlay hidden successfully.
    """
    try:
        self.overlay_manager.toggle_dim_overlay(False)
        return True
    except Exception:
        return False
```

**Current Duplication:** 3+ separate calls
**Extracted Count:** 1 definition, 3+ calls

---

### 3️⃣ **Dialog Sizing & Positioning Functions**

#### `_size_and_center_dialog()` → Extracted
**Current Location:** Inline in `open_dialog_wrapper()` Case A (lines 143-147)
```python
# CURRENT - Inline, not reusable
mw, mh = self.frameGeometry().width(), self.frameGeometry().height()
dw, dh = max(360, int(mw * width_ratio)), max(220, int(mh * height_ratio))
dlg.setFixedSize(dw, dh)
mx, my = self.frameGeometry().x(), self.frameGeometry().y()
dlg.move(mx + (mw - dw) // 2, my + (mh - dh) // 2)
```

**Extracted Function:**
```python
def _size_and_center_dialog(self, dlg: QDialog, width_ratio: float = 0.45, 
                            height_ratio: float = 0.4) -> None:
    """Size and center a dialog relative to main window.
    
    Args:
        dlg: Dialog to size and position.
        width_ratio: Dialog width as fraction of main window (0.0-1.0).
        height_ratio: Dialog height as fraction of main window (0.0-1.0).
    
    Ensures:
        - Dialog respects minimum size (360x220)
        - Dialog is centered on main window
    """
    try:
        mw, mh = self.frameGeometry().width(), self.frameGeometry().height()
        dw = max(360, int(mw * width_ratio))
        dh = max(220, int(mh * height_ratio))
        dlg.setFixedSize(dw, dh)
        
        mx, my = self.frameGeometry().x(), self.frameGeometry().y()
        cx = mx + (mw - dw) // 2
        cy = my + (mh - dh) // 2
        dlg.move(cx, cy)
    except Exception:
        # Fallback: let dialog use default sizing
        pass
```

**Current Usage:** Only in Case A
**Potential Usage:** Any simple dialog that needs sizing
**Benefits:**
- Constants documented (360x220 minimum)
- Aspect ratio handling in one place
- Reusable across all wrappers

---

### 4️⃣ **Dialog Cleanup & Restoration Functions**

#### `_create_cleanup_callback()` → Extracted
**Current Location:** Inline in `open_dialog_wrapper()` Case A (lines 148-156)
```python
# CURRENT - Inline, not reusable
def _cleanup(_):
    self.overlay_manager.toggle_dim_overlay(False)
    try:
        if hasattr(self, 'barcode_manager'):
            self.barcode_manager._end_scanner_modal_block()
    except Exception:
        pass
    self.raise_()
    self.activateWindow()
    self._refocus_sales_table()
```

**Extracted Function:**
```python
def _create_cleanup_callback(self, restore_focus: bool = True):
    """Create a cleanup callback for dialog finished signal.
    
    Args:
        restore_focus: If True, restore focus to sales table after cleanup.
    
    Returns:
        Callable: Function to connect to dlg.finished signal.
    
    Cleanup steps:
        1. Hide overlay
        2. Unblock scanner
        3. Raise and activate main window
        4. (Optional) Restore focus to sales table
    """
    def _cleanup(_result=None):
        try:
            self._hide_dialog_overlay()
            self._end_scanner_block()
            self.raise_()
            self.activateWindow()
            if restore_focus:
                self._refocus_sales_table()
        except Exception as e:
            print(f'Cleanup callback failed: {e}')
    
    return _cleanup
```

**Current Usage:** Case A only (inline)
**Potential Usage:** Any dialog using Case A pattern
**Benefits:**
- Extracted as factory function (creates reusable cleanup)
- Enables different cleanup strategies (with/without focus restore)
- Can be enhanced later with logging, metrics

---

### 5️⃣ **Window Focus & Activation Functions**

#### `_ensure_main_window_active()` → Extracted
**Current Location:** Inline in multiple locations (lines 155-156, 165-166, etc.)
```python
# CURRENT - Duplicated in multiple places
self.raise_()
self.activateWindow()
```

**Extracted Function:**
```python
def _ensure_main_window_active(self) -> bool:
    """Ensure main window is visible, raised, and has focus.
    
    Returns:
        bool: True if successful.
    
    Steps:
        1. Show window
        2. Raise above other windows
        3. Activate (set focus)
    """
    try:
        self.show()
        self.raise_()
        self.activateWindow()
        return True
    except Exception:
        return False
```

**Current Duplication:** 6+ separate occurrences
**Benefits:**
- Consistent window activation across all wrappers
- Single place to enhance (add animations, logging)
- Test-friendly

---

#### `_process_qt_events()` → Extracted
**Current Location:** Inline in `open_product_menu_dialog()` (line 203)
```python
# CURRENT
QApplication.processEvents()
```

**Extracted Function:**
```python
def _process_qt_events(self) -> None:
    """Force Qt to process pending events immediately.
    
    Used to:
        - Flush overlay hide/show events
        - Remove overlay from focus chain
        - Process pending timers
    
    Should be called after showing/hiding overlay.
    """
    try:
        QApplication.processEvents()
    except Exception:
        pass
```

**Benefit:** Documents *why* we call processEvents (intent clarity)

---

### 6️⃣ **Focus Restoration Functions**

#### `_restore_sales_table_focus()` → Extracted (Already exists as `_refocus_sales_table()`)
```python
# CURRENT - Already extracted!
def _refocus_sales_table(self) -> None:
    """Restore keyboard focus to sales table."""
    try:
        table = getattr(self, 'sales_table', None)
        if table is not None:
            table.setFocusPolicy(Qt.StrongFocus)
            table.setFocus(Qt.OtherFocusReason)
            if table.rowCount() > 0 and table.columnCount() > 0:
                table.setCurrentCell(0, 0)
    except Exception:
        pass
```

**Status:** ✅ Already extracted (reuse it!)

---

#### `_restore_focus_deferred()` → Extracted
**Current Location:** Inline in `open_product_menu_dialog()` (lines 209-221)
```python
# CURRENT - Inline, product-specific
def _force_focus_restore():
    try:
        self.show()
        self.raise_()
        self.activateWindow()
        fw = QApplication.focusWidget()
        if fw:
            fw.clearFocus()
        self._refocus_sales_table()
    except Exception:
        pass

QTimer.singleShot(10, _force_focus_restore)
```

**Extracted Function:**
```python
def _restore_focus_deferred(self, delay_ms: int = 10) -> None:
    """Restore focus to sales table with a deferred execution.
    
    Args:
        delay_ms: Milliseconds to delay before restoring focus (default: 10ms).
    
    Used when:
        - Focus has been captured by hidden widgets
        - Qt event processing needs to catch up
        - Overlay has just been hidden
    
    Steps:
        1. Wait for Qt events to process
        2. Ensure main window is active
        3. Clear focus from any stray widget
        4. Restore to sales table
    """
    def _do_restore():
        try:
            self._ensure_main_window_active()
            fw = QApplication.focusWidget()
            if fw is not None:
                fw.clearFocus()
            self._refocus_sales_table()
        except Exception as e:
            print(f'Focus restoration failed: {e}')
    
    QTimer.singleShot(delay_ms, _do_restore)
```

**Current Usage:** Only in product dialog
**Potential Usage:** Any dialog where overlay has focus issues
**Benefits:**
- Configurable delay
- Reusable for other dialogs with similar issues
- Centralized logic if timing needs adjustment

---

### 7️⃣ **Barcode Override Functions**

#### `_set_barcode_override()` → Extracted
**Current Location:** In `product_menu.py` (line ~720)
```python
# CURRENT - In product_menu.py, not in main.py
main_window._barcodeOverride = _barcode_to_product_code
if hasattr(main_window, 'barcode_manager'):
    main_window.barcode_manager._barcodeOverride = _barcode_to_product_code
```

**Extracted Function:**
```python
def _set_barcode_override(self, override_func: callable) -> bool:
    """Install a custom barcode handler override.
    
    Args:
        override_func: Function(barcode: str) -> bool that returns True if handled.
    
    Returns:
        bool: True if override was installed successfully.
    
    Used by:
        - Product dialog to intercept barcodes for product search
        - Any dialog that needs custom barcode handling
    
    Ensures both main_window and barcode_manager have the override.
    """
    try:
        self._barcodeOverride = override_func
        if hasattr(self, 'barcode_manager'):
            self.barcode_manager._barcodeOverride = override_func
        return True
    except Exception:
        return False
```

**Current Location:** Duplicated in product_menu.py
**Benefits:**
- Centralized in main window for consistency
- Easier to add logging/debugging
- Can be extended for multiple overrides

---

#### `_clear_barcode_override()` → Extracted (Referenced but undefined!)
**Current Location:** Called at line 204 but **NOT DEFINED**
```python
# CURRENT - Missing!
try:
    self._clear_barcode_override()
except Exception:
    pass
```

**Extracted Function:**
```python
def _clear_barcode_override(self) -> bool:
    """Remove any custom barcode handler override.
    
    Returns:
        bool: True if override was cleared successfully.
    
    Called when:
        - Product dialog closes
        - Dialog with barcode override exits
        - Application needs to resume normal barcode handling
    
    Restores default barcode routing.
    """
    try:
        self._barcodeOverride = None
        if hasattr(self, 'barcode_manager'):
            self.barcode_manager._barcodeOverride = None
        return True
    except Exception:
        return False
```

**Current Status:** 🔴 Called but not defined (bug!)
**Benefits:**
- Fixes the missing method error
- Symmetric with `_set_barcode_override()`
- Cleanup guarantee

---

### 8️⃣ **Dialog Execution & Error Handling Functions**

#### `_execute_dialog_auto()` → Extracted (Case A Pattern)
**Current Location:** Inline in `open_dialog_wrapper()` Case A (lines 142-160)
```python
# CURRENT - Inline, not reusable
if isinstance(dlg, QDialog):
    mw, mh = self.frameGeometry().width(), self.frameGeometry().height()
    dw, dh = max(360, int(mw * width_ratio)), max(220, int(mh * height_ratio))
    dlg.setFixedSize(dw, dh)
    mx, my = self.frameGeometry().x(), self.frameGeometry().y()
    dlg.move(mx + (mw - dw) // 2, my + (mh - dh) // 2)
    
    def _cleanup(_):
        # ... cleanup code
    
    dlg.finished.connect(_cleanup)
    dlg.exec_()
```

**Extracted Function:**
```python
def _execute_dialog_auto(self, dlg: QDialog, width_ratio: float = 0.45, 
                         height_ratio: float = 0.4) -> int:
    """Execute a dialog that returns QDialog (Case A).
    
    Args:
        dlg: The QDialog to execute.
        width_ratio: Dialog width ratio (default 0.45).
        height_ratio: Dialog height ratio (default 0.4).
    
    Returns:
        int: Dialog result code (QDialog.Accepted or Rejected).
    
    Steps:
        1. Size and center dialog
        2. Connect cleanup callback to finished signal
        3. Execute dialog modally
    """
    try:
        self._size_and_center_dialog(dlg, width_ratio, height_ratio)
        cleanup = self._create_cleanup_callback(restore_focus=True)
        dlg.finished.connect(cleanup)
        return dlg.exec_()
    except Exception as e:
        print(f'Dialog execution failed: {e}')
        self._create_cleanup_callback()(None)  # Force cleanup on error
        return QDialog.Rejected
```

**Benefits:**
- Reusable for any Case A dialog
- Cleaner error handling
- Single place to modify dialog execution behavior

---

#### `_execute_dialog_self_exec()` → Extracted (Case B Pattern)
**Current Location:** Inline in multiple dialog functions
```python
# CURRENT - In each dialog function
dlg.exec_()
return None  # or no return
```

**Extracted Function:**
```python
def _execute_dialog_self_exec(self, dialog_result: any = None) -> None:
    """Handle cleanup after a dialog that calls exec_() itself (Case B).
    
    Args:
        dialog_result: Optional result from the dialog (unused, for consistency).
    
    Called when:
        - Dialog function has already called dlg.exec_()
        - Dialog has managed its own modality
        - Function returns None
    
    Steps:
        1. Hide overlay
        2. Unblock scanner
        3. Ensure main window active
        4. Restore focus
    """
    try:
        self._hide_dialog_overlay()
        self._end_scanner_block()
        self._ensure_main_window_active()
        self._refocus_sales_table()
    except Exception as e:
        print(f'Self-exec cleanup failed: {e}')
```

**Benefits:**
- Named function clarifies Case B pattern
- Consistent cleanup across all Case B dialogs
- Easy to extend for new Case B dialogs

---

### 9️⃣ **Dialog Function Caller**

#### `_call_dialog_function()` → Extracted
**Current Location:** Inline in `open_dialog_wrapper()` (line 139)
```python
# CURRENT
dlg = dialog_func(self, *args, **kwargs)
```

**Extracted Function:**
```python
def _call_dialog_function(self, dialog_func: callable, *args, **kwargs) -> any:
    """Call a dialog controller function safely.
    
    Args:
        dialog_func: The dialog controller function to call.
        *args, **kwargs: Arguments to pass to the function.
    
    Returns:
        Result from dialog_func (QDialog instance or None).
    
    Handles:
        - Exception catching and logging
        - Type validation
    """
    try:
        result = dialog_func(self, *args, **kwargs)
        return result
    except Exception as e:
        print(f'Dialog function call failed: {e}')
        return None
```

**Benefit:** Documents the contract and enables future enhancements (logging, metrics)

---

## Summary: All Extractable Functions

| # | Function Name | Type | Current Location | Duplication | Priority |
|---|---|---|---|---|---|
| 1 | `_start_scanner_block()` | Scanner | open_dialog_wrapper | 1 call | Medium |
| 2 | `_end_scanner_block()` | Scanner | 4 locations | 4x | **High** |
| 3 | `_show_dialog_overlay()` | Overlay | Multiple | 2x | Medium |
| 4 | `_hide_dialog_overlay()` | Overlay | Multiple | 3x | **High** |
| 5 | `_size_and_center_dialog()` | Layout | Case A only | 1 instance | **High** |
| 6 | `_create_cleanup_callback()` | Cleanup | Case A only | 1 instance | **High** |
| 7 | `_ensure_main_window_active()` | Focus | Multiple | 6x | **High** |
| 8 | `_process_qt_events()` | Events | Product only | 1x | Medium |
| 9 | `_restore_focus_deferred()` | Focus | Product only | 1x | Medium |
| 10 | `_set_barcode_override()` | Barcode | product_menu.py | 1x | **High** |
| 11 | `_clear_barcode_override()` | Barcode | **MISSING!** | 0 | **Critical** |
| 12 | `_execute_dialog_auto()` | Execution | Case A inline | 1x | **High** |
| 13 | `_execute_dialog_self_exec()` | Execution | Case B pattern | Multiple | **High** |
| 14 | `_call_dialog_function()` | Caller | Inline | 1x | Low |

---

## Recommended Extraction Strategy

### Phase 1: Critical Fixes & Duplicates (Quick Wins)
1. ✅ `_clear_barcode_override()` — **Fixes missing method**
2. ✅ `_end_scanner_block()` — **Eliminates 4x duplication**
3. ✅ `_hide_dialog_overlay()` — **Eliminates 3x duplication**
4. ✅ `_ensure_main_window_active()` — **Eliminates 6x duplication**

**Impact:** ~30 lines of code reduced to 4 method calls + 4 definitions

### Phase 2: High-Value Refactoring (Structural)
5. ✅ `_size_and_center_dialog()` — Makes Case A reusable
6. ✅ `_create_cleanup_callback()` — Factory for cleanup callbacks
7. ✅ `_execute_dialog_auto()` — Case A as named function
8. ✅ `_execute_dialog_self_exec()` — Case B as named function

**Impact:** Main wrapper becomes thin orchestrator; easy to add new dialogs

### Phase 3: Optional Enhancements (Polish)
9. ⭕ `_process_qt_events()` — Documents intent (non-urgent)
10. ⭕ `_restore_focus_deferred()` — Reuses product logic
11. ⭕ `_set_barcode_override()` — Mirrors clear method
12. ⭕ `_call_dialog_function()` — Enables future logging

---

## Benefits Summary

### Code Reduction
```
Current:
  open_dialog_wrapper: ~50 lines
  open_product_menu_dialog: ~30 lines
  Total: ~80 lines of wrapper logic

After Extraction:
  open_dialog_wrapper: ~15 lines (calling subfunctions)
  open_product_menu_dialog: ~10 lines
  Total: ~25 lines of wrapper logic
  
  Plus: ~60 lines of extracted methods
  Net reduction in complexity: easier to understand each piece
```

### Maintainability
- Single source of truth for each responsibility
- If overlay behavior changes, update 1 function (not 3+ places)
- If focus restoration needs tweaking, update 1 function (not 4+ places)
- If scanner blocking logic changes, update 1 function (not 5+ places)

### Testability
Each extracted function can be unit tested independently:
```python
def test_size_and_center_dialog():
    """Test dialog sizing and centering."""
    
def test_cleanup_callback():
    """Test that cleanup performs all steps."""
    
def test_barcode_override_clear():
    """Test that override is actually cleared."""
```

### Extensibility
- Easy to add new wrapper types (Case C, D, E, etc.)
- Dialog functions don't need to duplicate overlay/scanner/focus logic
- Can add instrumentation/logging in one place
- Can change cleanup order globally if needed

---

## Architecture Pattern: Composition Over Duplication

```
┌─────────────────────────────────────────────────────┐
│         Dialog Wrapper Orchestrators                 │
├─────────────────────────────────────────────────────┤
│                                                      │
│  open_dialog_wrapper()        open_product_dialog()│
│      ↓                              ↓               │
│   Calls extracted functions  Calls extracted funcs  │
│                                                      │
└─────────────────────────────────────────────────────┘
         ↓                              ↓
  ┌──────────────────────────────────────────┐
  │     Reusable Helper Functions             │
  ├──────────────────────────────────────────┤
  │                                           │
  │  Scanner Management:                      │
  │  • _start_scanner_block()                │
  │  • _end_scanner_block()                  │
  │                                           │
  │  Overlay Management:                      │
  │  • _show_dialog_overlay()                │
  │  • _hide_dialog_overlay()                │
  │                                           │
  │  Dialog Layout:                           │
  │  • _size_and_center_dialog()             │
  │                                           │
  │  Cleanup:                                 │
  │  • _create_cleanup_callback()            │
  │                                           │
  │  Focus Management:                        │
  │  • _ensure_main_window_active()          │
  │  • _restore_focus_deferred()             │
  │  • _refocus_sales_table() [exists]       │
  │                                           │
  │  Barcode Management:                      │
  │  • _set_barcode_override()               │
  │  • _clear_barcode_override()             │
  │                                           │
  └──────────────────────────────────────────┘
```

---

## Example: Refactored `open_dialog_wrapper()` with Extractions

### Before (Current - 50 lines)
```python
def open_dialog_wrapper(self, dialog_func, width_ratio=0.45, height_ratio=0.4, *args, **kwargs):
    """Open dialog with overlay and scanner block."""
    self.overlay_manager.toggle_dim_overlay(True)
    try:
        if hasattr(self, 'barcode_manager'):
            self.barcode_manager._start_scanner_modal_block()
    except Exception:
        pass
    try:
        dlg = dialog_func(self, *args, **kwargs)
        
        if isinstance(dlg, QDialog):
            # Case A: 15+ lines
            mw, mh = self.frameGeometry().width(), self.frameGeometry().height()
            dw, dh = max(360, int(mw * width_ratio)), max(220, int(mh * height_ratio))
            dlg.setFixedSize(dw, dh)
            mx, my = self.frameGeometry().x(), self.frameGeometry().y()
            dlg.move(mx + (mw - dw) // 2, my + (mh - dh) // 2)
            
            def _cleanup(_):
                self.overlay_manager.toggle_dim_overlay(False)
                try:
                    if hasattr(self, 'barcode_manager'):
                        self.barcode_manager._end_scanner_modal_block()
                except Exception:
                    pass
                self.raise_()
                self.activateWindow()
                self._refocus_sales_table()
            
            dlg.finished.connect(_cleanup)
            dlg.exec_()
        else:
            # Case B: 10+ lines
            self.overlay_manager.toggle_dim_overlay(False)
            try:
                if hasattr(self, 'barcode_manager'):
                    self.barcode_manager._end_scanner_modal_block()
            except Exception:
                pass
            self.raise_()
            self.activateWindow()
            self._refocus_sales_table()
    except Exception as e:
        # Error handling: 6+ lines
        self.overlay_manager.toggle_dim_overlay(False)
        try:
            if hasattr(self, 'barcode_manager'):
                self.barcode_manager._end_scanner_modal_block()
        except Exception:
            pass
        print('Dialog failed:', e)
```

### After (Refactored - ~15 lines)
```python
def open_dialog_wrapper(self, dialog_func, width_ratio=0.45, height_ratio=0.4, *args, **kwargs):
    """Open dialog with overlay and scanner block."""
    self._show_dialog_overlay()
    self._start_scanner_block()
    
    try:
        dlg = self._call_dialog_function(dialog_func, *args, **kwargs)
        
        if isinstance(dlg, QDialog):
            # Case A: Execute with automatic cleanup
            self._execute_dialog_auto(dlg, width_ratio, height_ratio)
        else:
            # Case B: Dialog ran exec_() itself, just cleanup
            self._execute_dialog_self_exec()
            
    except Exception as e:
        print(f'Dialog failed: {e}')
        # Ensure cleanup happens even on error
        self._hide_dialog_overlay()
        self._end_scanner_block()
```

**Reduction:** 50 → 15 lines (-70% complexity)
**Clarity:** Intent of each step is now obvious
**Maintainability:** Each concern is isolated

---

## Example: Refactored `open_product_menu_dialog()` with Extractions

### Before (Current - 30 lines)
```python
def open_product_menu_dialog(self, *args, **kwargs):
    self.overlay_manager.toggle_dim_overlay(True)
    
    try:
        launch_product_dialog(self, **kwargs)
    except Exception as e:
        print('Product dialog failed:', e)
    finally:
        self.overlay_manager.toggle_dim_overlay(False)
        QApplication.processEvents()
        
        try:
            self._clear_barcode_override()
        except Exception:
            pass

        def _force_focus_restore():
            try:
                self.show()
                self.raise_()
                self.activateWindow()
                fw = QApplication.focusWidget()
                if fw:
                    fw.clearFocus()
                self._refocus_sales_table()
            except Exception:
                pass

        QTimer.singleShot(10, _force_focus_restore)
```

### After (Refactored - ~10 lines)
```python
def open_product_menu_dialog(self, *args, **kwargs):
    """Open Product Management panel with dedicated handling."""
    self._show_dialog_overlay()
    
    try:
        launch_product_dialog(self, **kwargs)
    except Exception as e:
        print(f'Product dialog failed: {e}')
    finally:
        self._hide_dialog_overlay()
        self._process_qt_events()
        self._clear_barcode_override()
        self._restore_focus_deferred(delay_ms=10)
```

**Reduction:** 30 → 10 lines (-67% complexity)
**Clarity:** Each step is named and self-documenting
**Bonus:** `_clear_barcode_override()` is now defined!

---

## Implementation Order Recommendation

### Step 1: Define Missing Method (Fixes Bug)
```python
def _clear_barcode_override(self) -> bool:
    """Remove any custom barcode handler override."""
    try:
        self._barcodeOverride = None
        if hasattr(self, 'barcode_manager'):
            self.barcode_manager._barcodeOverride = None
        return True
    except Exception:
        return False
```

### Step 2: Extract High-Value Duplicates
- `_end_scanner_block()`
- `_hide_dialog_overlay()`
- `_ensure_main_window_active()`

### Step 3: Extract Layout & Cleanup Functions
- `_size_and_center_dialog()`
- `_create_cleanup_callback()`

### Step 4: Refactor Wrappers to Use Extracted Functions
- Update `open_dialog_wrapper()` to call extracted functions
- Update `open_product_menu_dialog()` to call extracted functions

### Step 5: Optional - Add Additional Helpers
- `_process_qt_events()`
- `_restore_focus_deferred()`
- `_set_barcode_override()`

---

## Quality Checklist

When implementing extractions, ensure:

- [ ] Each function has a docstring explaining purpose
- [ ] Return types are documented (returns True/False, int, None, etc.)
- [ ] Edge cases are handled (missing attributes, exceptions)
- [ ] Function names are verb-based (`_start_`, `_stop_`, `_ensure_`, `_create_`, `_clear_`)
- [ ] Consistent parameter naming and ordering
- [ ] No circular dependencies between helpers
- [ ] Each function does one thing (Single Responsibility)
- [ ] Error handling is consistent (try-except pattern)
- [ ] Functions are testable in isolation

---

## Next Steps

1. **Review** this analysis for agreement on extraction strategy
2. **Prioritize** which functions to extract first (recommend Phase 1 + Phase 2)
3. **Implement** in incremental commits (one batch at a time)
4. **Test** that existing functionality still works
5. **Document** in code via docstrings and type hints

