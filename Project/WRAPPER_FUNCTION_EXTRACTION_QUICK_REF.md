# Dialog Wrapper Function Extraction - Quick Reference Map

## Current State: Responsibilities & Locations

```
┌────────────────────────────────────────────────────────────────────┐
│              open_dialog_wrapper()  (50 lines)                     │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  SETUP PHASE                                                       │
│  ├─ toggle_dim_overlay(True)                [4x duplicated]       │
│  └─ _start_scanner_modal_block()            [inline]              │
│                                                                    │
│  DIALOG CREATION                                                   │
│  └─ dialog_func(self, *args, **kwargs)      [inline]              │
│                                                                    │
│  CASE A: Dialog returns QDialog                                    │
│  ├─ setFixedSize(dw, dh)                    [5x duplicated math]  │
│  ├─ move(cx, cy)                            [5x duplicated math]  │
│  ├─ Create _cleanup callback                [4x duplicated]       │
│  │  ├─ toggle_dim_overlay(False)            [3x duplicated]       │
│  │  ├─ _end_scanner_modal_block()           [4x duplicated]       │
│  │  ├─ raise_()                             [6x duplicated]       │
│  │  ├─ activateWindow()                     [6x duplicated]       │
│  │  └─ _refocus_sales_table()               [reused - good!]      │
│  ├─ Connect finished signal                 [inline]              │
│  └─ exec_()                                 [inline]              │
│                                                                    │
│  CASE B: Dialog calls exec_() itself                               │
│  ├─ toggle_dim_overlay(False)               [3x duplicated]       │
│  ├─ _end_scanner_modal_block()              [4x duplicated]       │
│  ├─ raise_()                                [6x duplicated]       │
│  ├─ activateWindow()                        [6x duplicated]       │
│  └─ _refocus_sales_table()                  [reused - good!]      │
│                                                                    │
│  ERROR HANDLING                                                    │
│  ├─ toggle_dim_overlay(False)               [3x duplicated]       │
│  ├─ _end_scanner_modal_block()              [4x duplicated]       │
│  └─ Print error                             [inline]              │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│           open_product_menu_dialog()  (30 lines)                   │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  SETUP PHASE                                                       │
│  └─ toggle_dim_overlay(True)                [4x duplicated]       │
│                                                                    │
│  DIALOG EXECUTION                                                  │
│  └─ launch_product_dialog(self, **kwargs)   [inline]              │
│                                                                    │
│  CLEANUP PHASE (in finally)                                        │
│  ├─ toggle_dim_overlay(False)               [3x duplicated]       │
│  ├─ processEvents()                         [1x in product]       │
│  ├─ _clear_barcode_override()               [NOT DEFINED! 🔴]     │
│  ├─ show(), raise_(), activateWindow()      [6x duplicated]       │
│  ├─ clearFocus()                            [inline]              │
│  └─ _refocus_sales_table()                  [reused - good!]      │
│     with QTimer.singleShot(10, ...)         [1x in product]       │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Extracted Functions Dependency Tree

```
┌──────────────────────────────────────────────────────────────────────┐
│                 INDEPENDENT (no dependencies)                         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  _start_scanner_block()                  ← calls barcode_manager     │
│  _end_scanner_block()                    ← calls barcode_manager     │
│  _show_dialog_overlay()                  ← calls overlay_manager     │
│  _hide_dialog_overlay()                  ← calls overlay_manager     │
│  _process_qt_events()                    ← calls QApplication        │
│  _set_barcode_override()                 ← sets local/barcode_mgr    │
│  _clear_barcode_override()               ← clears local/barcode_mgr  │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────────────────────────┐
│              LAYOUT & WINDOW (low dependencies)                       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  _size_and_center_dialog()               ← uses frameGeometry()      │
│  _ensure_main_window_active()            ← show/raise/activate       │
│  _call_dialog_function()                 ← calls user function       │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────────────────────────┐
│              CLEANUP (depends on basic helpers)                       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  _create_cleanup_callback()              ← calls helpers above        │
│    └─ calls: _hide_overlay, _end_scanner,                           │
│       _ensure_main_window, _refocus_sales_table                      │
│                                                                       │
│  _restore_focus_deferred()               ← calls helpers above        │
│    └─ calls: _ensure_main_window, _refocus_sales_table               │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────────────────────────┐
│         HIGH-LEVEL ORCHESTRATORS (compose helpers)                    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  _execute_dialog_auto(dlg, ...)          ← Case A pattern            │
│    └─ calls: _size_and_center_dialog,                               │
│       _create_cleanup_callback, exec_()                              │
│                                                                       │
│  _execute_dialog_self_exec()             ← Case B pattern            │
│    └─ calls: _hide_overlay, _end_scanner,                           │
│       _ensure_main_window, _refocus_sales_table                      │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────────────────────────┐
│          WRAPPER FUNCTIONS (thin orchestrators)                       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  open_dialog_wrapper()                                               │
│    ├─ _show_overlay                                                 │
│    ├─ _start_scanner                                                │
│    ├─ _call_dialog_function                                         │
│    ├─ if Case A: _execute_dialog_auto()                            │
│    └─ if Case B: _execute_dialog_self_exec()                       │
│                                                                       │
│  open_product_menu_dialog()                                          │
│    ├─ _show_overlay                                                 │
│    ├─ _call_dialog_function                                         │
│    ├─ _hide_overlay                                                 │
│    ├─ _process_qt_events                                            │
│    ├─ _clear_barcode_override                                       │
│    └─ _restore_focus_deferred                                       │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Extraction Priority Matrix

```
╔════════════════════════════════════════════════════════════════════╗
║  IMPACT (Duplication / Code Reduction)                             ║
║                                                                    ║
║  HIGH ┌────────────────────────────────────────────────────────┐  ║
║       │  P1: _clear_barcode_override()  [MISSING!]            │  ║
║       │  P1: _end_scanner_block()       [4x dup]              │  ║
║       │  P1: _hide_dialog_overlay()     [3x dup]              │  ║
║       │  P1: _ensure_main_window_active() [6x dup]            │  ║
║       │                                                        │  ║
║       │  P2: _size_and_center_dialog()  [1x → reuse]          │  ║
║       │  P2: _create_cleanup_callback() [4x pattern]          │  ║
║       │  P2: _execute_dialog_auto()     [composite]           │  ║
║       │  P2: _execute_dialog_self_exec()[composite]           │  ║
║       │                                                        │  ║
║       │  P3: _process_qt_events()       [1x → doc]            │  ║
║       │  P3: _restore_focus_deferred()  [1x → reuse]          │  ║
║       │  P3: _set_barcode_override()    [mirror]              │  ║
║       │  P3: _start_scanner_block()     [1x]                  │  ║
║       │  P3: _call_dialog_function()    [1x]                  │  ║
║  LOW  └────────────────────────────────────────────────────────┘  ║
║       ▲                                                             ║
║       └─ EFFORT (complexity, lines of code)                       ║
║                                                                    ║
║  RECOMMENDATION: Start with P1 (quick wins), then P2 (structure)  ║
╚════════════════════════════════════════════════════════════════════╝
```

---

## Current Duplication Heat Map

```
Function/Responsibility              Location Count    Duplication
═══════════════════════════════════════════════════════════════════

toggle_dim_overlay(False)             4 places         🔴🔴🔴🔴
_end_scanner_modal_block()            4 places         🔴🔴🔴🔴
raise_() + activateWindow()           6+ places        🔴🔴🔴🔴🔴🔴
Size & center math (dw, dh, move)     Multiple         🔴🔴🔴

toggle_dim_overlay(True)              2 places         🟡🟡
_refocus_sales_table()                Already extracted ✅
Dialog sizing (min 360x220)           Multiple         🟡

_start_scanner_modal_block()          1 place          🟢
_clear_barcode_override()             Missing!         🔴 CRITICAL
QApplication.processEvents()          1 place          🟢
QTimer.singleShot()                   1 place          🟢
```

---

## Before / After Code Complexity

### Current State
```
┌─ open_dialog_wrapper: 50 lines
│   ├─ Case A logic: ~20 lines (including nested _cleanup)
│   ├─ Case B logic: ~10 lines
│   └─ Error handling: ~6 lines
│
├─ open_product_menu_dialog: 30 lines
│   ├─ Setup: ~3 lines
│   ├─ Try-exec: ~2 lines
│   ├─ Finally block: ~20 lines (nested _force_focus_restore)
│
├─ Duplication hotspots: 6+ functions (scanner, overlay, focus)
└─ Bug: _clear_barcode_override() called but not defined!

Total wrapper complexity: ~80 lines + scattered, duplicated helpers
```

### After Extraction
```
┌─ open_dialog_wrapper: ~15 lines
│   ├─ Setup: ~2 lines (_show_overlay, _start_scanner)
│   ├─ Call dialog: ~1 line (_call_dialog_function)
│   ├─ Route & execute: ~3 lines (if/else to execute functions)
│   └─ Error handling: ~2 lines (hide/unblock + error msg)
│
├─ open_product_menu_dialog: ~10 lines
│   ├─ Setup: ~1 line (_show_overlay)
│   ├─ Try-exec: ~1 line (_call_dialog_function)
│   ├─ Finally: ~5 lines (4 helper calls + 1 deferred focus)
│
├─ Extracted helpers: ~60 lines (14 focused functions)
│   ├─ Scanner management: ~15 lines (2 functions)
│   ├─ Overlay management: ~15 lines (2 functions)
│   ├─ Layout & positioning: ~10 lines (1 function)
│   ├─ Cleanup: ~10 lines (2 functions)
│   └─ Focus management: ~10 lines (3 functions)
│
├─ Zero duplication: each responsibility in 1 place
└─ Bug fixed: _clear_barcode_override() properly defined

Total complexity: ~25 lines visible + 60 lines organized helpers
(Much easier to understand, test, and maintain)
```

---

## Function Extraction Checklist

### Phase 1: Critical (Do First)
- [ ] `_clear_barcode_override()` — Fixes missing method bug
- [ ] `_end_scanner_block()` — Eliminates 4x duplication
- [ ] `_hide_dialog_overlay()` — Eliminates 3x duplication
- [ ] `_ensure_main_window_active()` — Eliminates 6x duplication
- [ ] `_show_dialog_overlay()` — Consistency with hide

### Phase 2: Structural (Do Second)
- [ ] `_size_and_center_dialog()` — Makes Case A reusable
- [ ] `_create_cleanup_callback()` — Factory pattern for cleanup
- [ ] `_execute_dialog_auto()` — Named Case A pattern
- [ ] `_execute_dialog_self_exec()` — Named Case B pattern

### Phase 3: Polish (Do Last)
- [ ] `_start_scanner_block()` — Symmetry with end_block
- [ ] `_process_qt_events()` — Document intent
- [ ] `_restore_focus_deferred()` — Reuse focus restoration
- [ ] `_set_barcode_override()` — Mirror clear_override
- [ ] `_call_dialog_function()` — Wrapper for dialog calls

---

## Key Insights

### 1. Pattern Recognition
The three wrapper functions follow distinct patterns:
- **Case A:** Dialog returns QDialog → wrapper sizes, centers, connects signal, executes
- **Case B:** Dialog calls exec_() internally → wrapper just cleans up after
- **Case C (Product):** Like Case B but with barcode override + deferred focus

### 2. Shared Responsibilities
Six responsibilities appear 2-6 times:
1. Scanner blocking/unblocking (4x)
2. Overlay toggling (4x+ combined show/hide)
3. Window activation (6x)
4. Focus restoration (multiple patterns)
5. Error cleanup (3x patterns)
6. Dialog sizing (5x duplicated math)

### 3. Abstraction Opportunity
Instead of Case A/B distinction, can think of composition:
```
open_dialog_wrapper = 
  ShowOverlay() +
  BlockScanner() +
  CallDialog() +
  SizeDialog (if returned) +
  ConnectCleanup (if returned) +
  ExecuteDialog (if returned) +
  OR JustCleanup (if already executed) +
  ErrorHandler()
```

### 4. Extension Points
Once extracted, easy to add:
- Case D: "Dialog with custom barcode handling" (like product, but simpler)
- Case E: "Dialog that needs deferred focus" (like product)
- Dialog type registry (map dialog name to handler)
- Instrumentation (logging, metrics per dialog type)
- Animation (overlay fade-in/out)

### 5. Testing Opportunity
Each extracted function can be unit tested:
- `test_scanner_block()` — Verify barcode_manager called
- `test_overlay_management()` — Verify widget visibility
- `test_dialog_sizing()` — Verify centering math
- `test_cleanup_callback()` — Verify all steps execute
- `test_barcode_override()` — Verify set/clear symmetry

---

## Implementation Notes

### Naming Convention
All extracted functions use `_leading_underscore` because:
- They're internal implementation details
- They should only be called by wrapper methods
- Signals "private" scope to other developers

### Return Values
Most return `bool` for symmetry:
- Easier to check if operation succeeded
- Can be chained in logging: `if not _end_scanner_block(): log_error()`
- Empty function can return None

### Documentation Style
Each function includes:
1. One-liner describing what it does
2. Args section (what parameters, types)
3. Returns section (what it gives back)
4. Used when section (context of usage)
5. Ensures/Steps section (guarantees provided)

### Error Handling Strategy
All functions use try-except internally:
- Wrapper doesn't need nested try-except
- Consistent logging of failures
- Graceful degradation (function continues even if part fails)

---

## Risk Assessment

### Low Risk Extractions ✅
- `_clear_barcode_override()` — Simple setter operations
- `_end_scanner_block()` — Already used; just factoring out
- `_hide_dialog_overlay()` — Calls one method; no logic
- `_ensure_main_window_active()` — Calls three methods; no dependencies

### Medium Risk Extractions ⚠️
- `_create_cleanup_callback()` — Creates closure; must preserve context
- `_size_and_center_dialog()` — Math logic; test carefully
- `_restore_focus_deferred()` — Timer-based; threading sensitivity

### Mitigation Strategies
1. Extract one function at a time, test after each
2. Keep original code nearby for reference
3. Run existing functionality tests
4. Verify dialog still opens/closes/focuses correctly
5. Test edge cases (missing attributes, exceptions)

---

## Success Metrics

After completing extraction, you should observe:
- ✅ `open_dialog_wrapper()` reduced from 50 → 15 lines
- ✅ `open_product_menu_dialog()` reduced from 30 → 10 lines
- ✅ Zero duplication of overlay management code
- ✅ Zero duplication of scanner blocking code
- ✅ Zero duplication of focus restoration code
- ✅ `_clear_barcode_override()` method now defined and callable
- ✅ Each extracted function can be read in <30 seconds
- ✅ Each extracted function does one thing well
- ✅ All dialogs still open/close/focus as before
- ✅ New helpers can be reused by future dialogs

