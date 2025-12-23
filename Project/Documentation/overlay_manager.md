# Overlay Manager Integration

## Overview
The Overlay Manager (`modules/ui_utils/overlay_manager.py`) provides a centralized, reusable way to show and hide a dimming overlay on the main window. This overlay is used to visually block interaction with the main UI when modal dialogs (such as Vegetable Entry, Manual Entry, Logout, Admin, etc.) are open.

## Usage
- The overlay is managed by the `OverlayManager` class.
- It is instantiated in `MainLoader` (main window) as `self.overlay_manager = OverlayManager(self)`.
- To show the overlay: `self.overlay_manager.toggle_dim_overlay(True)`
- To hide the overlay: `self.overlay_manager.toggle_dim_overlay(False)`

## Refactoring Details
- All previous direct overlay logic (such as `_show_dim_overlay` and `_hide_dim_overlay` methods) in `main.py` has been removed.
- All dialogs that require a dimmed background now call the overlay manager.
- This ensures a consistent look and behavior for all modal dialogs.

## Example Integration
```python
# In main.py, inside MainLoader:
self.overlay_manager = OverlayManager(self)

# When opening a dialog:
self.overlay_manager.toggle_dim_overlay(True)
# ... open dialog ...
self.overlay_manager.toggle_dim_overlay(False)
```

## Benefits
- **Consistency:** All overlays look and behave the same across dialogs.
- **Maintainability:** Overlay logic is in one place, making future changes easy.
- **Reusability:** Any new dialog can use the overlay manager without duplicating code.

## Affected Dialogs
- Vegetable Entry
- Manual Entry
- Logout
- Admin Settings
- Product Menu
- Any future modal dialogs

## File Locations
- Overlay logic: `modules/ui_utils/overlay_manager.py`
- Main integration: `main.py` (see `MainLoader`)

## Related Topics
- See also: `Documentation/logout_and_titlebar.md` for custom title bar and dimming pattern.
- See also: `Documentation/scanner_input_infocus.md` for how overlays interact with scanner modal block.
