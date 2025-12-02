# Dialog and Panel Launching Standard

All dialogs and panels (menu, sales, payment, etc.) in the POS system are launched using a single unified wrapper method in `main.py`:

```
self.open_dialog_wrapper(dialog_func, *args, **kwargs)
```

## Purpose
- Standardizes overlay management, dialog sizing/centering, and barcode scanner blocking/unblocking.
- Ensures consistent user experience and simplifies maintenance.
- Used by all dialog launcher methods in `MainLoader`.

## Usage Example
```
self.open_dialog_wrapper(launch_product_dialog, initial_mode='edit')
self.open_dialog_wrapper(launch_vegetable_entry_dialog)
```

## Benefits
- Consistent overlay and scanner handling for all dialogs
- Reduces code duplication and risk of inconsistent dialog behavior
- Easy to add new dialogs: just call `self.open_dialog_wrapper(new_dialog_func)`

## Implementation Notes
- The wrapper is defined as `open_dialog_wrapper` in `main.py`.
- All dialog launcher methods (e.g., `open_product_menu_dialog`, `open_vegetable_entry_dialog`, etc.) delegate to this wrapper.
- Dialogs and panels interact with the scanner only via BarcodeManager's modal block and override helpers.

---
_Last updated: December 2, 2025_
