

# FieldCoordinator & Centralized Keyboard Orchestration

## Purpose
FieldCoordinator is now the Primary Event Interceptor and Keyboard Orchestrator for dialogs. It manages all cross-widget relationships, focus navigation, and UI feedback in a declarative, rules-based manner for PyQt5 dialogs, and globally intercepts keyboard events for registered widgets.


## Key Concepts (2026 Update)
- **Global Enter-Key Hijacking:** The eventFilter now intercepts Return/Enter keys for all registered widgets. By returning True, it prevents QDialog from performing native Accept or "Ghost Click" behaviors.
- **Smart Swallowing:** If Enter is pressed on an empty field, the Coordinator highlights the field and refuses to move focus, trapping the user until a valid value is entered.
- **Simple Jump Support:** Widgets can be linked to a next_focus target for Enter navigation, even without a lookup function.
- **Button Triggering:** If Enter is pressed while a QPushButton is focused, the Coordinator manually triggers obj.click(), ensuring Enter-to-Submit works even with dialog defaults disabled.
- **Declarative Links:** Define all widget relationships up front using `add_link`.
- **Signal Intelligence:** Listens only to user-driven signals (e.g., `textEdited`), not programmatic changes.
- **Reverse Action:** Clearing a source widget clears all mapped targets and resets status.
- **Infinite Loop Prevention:** Blocks signals during programmatic updates to avoid feedback loops.
- **UI Feedback:** Integrates with `ui_feedback.py` and QSS for consistent status coloring.
- **Standardized Status + Auto-Clear (Opt-in):**
   - `coord.set_error(source_widget, msg, status_label=lbl)` records the error source.
   - `coord.register_validator(widget, validate_fn, status_label=lbl)` clears the *last* error once the source widget becomes valid.
   - `coord.set_ok(msg, status_label=lbl)` shows success and clears remembered error state.
   - `coord.clear_status(lbl)` clears the label and resets remembered error state.
- **Reactive Placeholders (Opt-in):** `add_link(..., placeholder_mode='reactive')` hides placeholders initially and shows them only for targets that remain empty after sync.

## Enter Navigation Details

`FieldCoordinator.add_link(..., swallow_empty=...)` controls how Enter behaves on each field:

- `swallow_empty=True` (default): Enter on an empty field is swallowed and focus stays put.
- `swallow_empty=False`: Enter is allowed to advance to `next_focus` even if the field is empty.

This allows “required” vs “optional” fields to share the same navigation mechanism without dialog-level default buttons closing the dialog.

## Opt-in Helpers (Jan 2026)
These helpers are additive and do not affect existing dialogs unless used.

- **Initial Focus + Tab Landing:** `set_initial_focus(...)`
   - Selects a `QTabWidget` tab (by index or tab text) then focuses a given widget.
- **Focus Lock / Unlock (Gate):** `FocusGate`
   - Locks a group of widgets so they cannot be focused until unlocked.
   - Optional behavior:
     - `lock_enabled=True` disables widgets while locked (prevents typing/clicking).
     - `lock_read_only=True` forces `QLineEdit` read-only while locked.
- **Lightweight Focus Toggle:** `set_focus_enabled(...)`
   - Simple function to toggle `Qt.NoFocus` using a caller-owned remember-map.

- **Mutual Exclusivity (Source Fields):** `enforce_exclusive_lineedits(a, b, ...)`
   - When the user starts entering text into one source field, the other is cleared.
   - Uses `textChanged`, so it also works when scanners/programmatic `setText(...)` are involved.
   - Designed for “code search vs name search” UX clarity.

### Example: land on a tab and lock fields until first input
```python
from modules.ui_utils.focus_utils import FieldCoordinator, FocusGate, set_initial_focus

coord = FieldCoordinator(dlg)
dlg._coord = coord

# 1) Land on a specific tab + field
set_initial_focus(dlg, tab_widget=tabs, tab_name='ADD', first_widget=code_in)

# 2) Lock all other fields until code is accepted
gate = FocusGate([name_in, price_in, unit_combo, ok_btn], lock_enabled=True)
gate.lock()

def _unlock_rest():
      gate.unlock()

coord.add_link(source=code_in, lookup_fn=lookup_code, next_focus=lambda: (_unlock_rest(), name_in.setFocus()))
```


## Usage Pattern
1. **Instantiate:**
   ```python
   coord = FieldCoordinator(dialog)
   dialog._coord = coord  # Prevent garbage collection
   ```
2. **Define Links:**
   ```python
   coord.add_link(
       source=code_in,
       target_map={'name': name_in, 'unit': unit_dis},
       lookup_fn=lambda val: input_handler.get_coordinator_lookup(val, 'code'),
       next_focus=qty_in,
       status_label=status_lbl,
       on_sync=update_placeholder
   )
   # For simple jumps (no lookup):
   coord.add_link(
       source=qty_in,
       target_map={},
       lookup_fn=None,
       next_focus=btn_ok
   )
   ```
3. **Dynamic Registration:**
   For widgets created at runtime (e.g., table rows), register each new widget with the coordinator as soon as it is created.
4. **Final Validation:**
   Use pure input_handler getters in your OK handler for final data extraction and validation.


## add_link Parameters
- `source`: The user-editable widget (QLineEdit/QComboBox/QPushButton).
- `target_map`: Dict mapping data keys to widgets to fill.
- `lookup_fn`: Stateless function returning a dict or None (optional for simple jumps).
- `next_focus`: Widget or function to trigger on Enter.
- `status_label`: QLabel for status feedback (QSS property + re-polish).
- `on_sync`: Optional hook after sync (e.g., update placeholders).
- `placeholder_mode`: Optional placeholder behavior; use `'reactive'` for sync-driven placeholders.
- `swallow_empty`: Controls Enter behavior for empty fields (required vs optional).

## Validator Auto-Clear Pattern (Optional)
Use this for “error clears after correction” behavior.

```python
coord.set_error(name_edit, 'Error: Product name is required', status_label=status_lbl)
coord.register_validator(
   name_edit,
   lambda: input_handler.handle_product_name_input(name_edit),
   status_label=status_lbl
)
```

## Example
```python
coord = FieldCoordinator(dlg)
coord.add_link(
    source=code_in,
    target_map={'name': name_in, 'unit': unit_dis},
    lookup_fn=lambda val: input_handler.get_coordinator_lookup(val, 'code'),
    next_focus=qty_in,
    status_label=status_lbl,
    on_sync=update_placeholder
)
```


## Integration & Best Practices
- All cross-widget and keyboard logic must be declared via FieldCoordinator.
- Input handlers must remain pure (no widget manipulation).
- UI feedback and styling are handled via QSS properties and re-polish (see ui_feedback.py).
- For new dialogs, always follow the three-step implementation guide in the Centralized Keyboard Orchestration documentation.

## Enter Key Workflow (2026 Model)

| Action                | Character Logic      | Enter Key Logic         | Result                                 |
|-----------------------|---------------------|-------------------------|----------------------------------------|
| Typing '0' or 'a'     | Swallowed by Regex  | N/A                    | Character never appears                |
| Enter on Empty Box    | N/A                 | Swallowed by Coordinator| Focus stays; Box highlights            |
| Enter on Valid Qty    | N/A                 | Jump by Coordinator     | Focus moves to OK Button               |
| Enter on OK Button    | N/A                 | Click by Coordinator    | _handle_ok_all validates & closes      |
| Enter on Veg Button   | N/A                 | Click by Coordinator    | Row added; Focus jumps to OK           |

## See Also
- [centralized_UI_relationship_coordinator.md](centralized_UI_relationship_coordinator.md)
- [input_handler.md](input_handler.md)
- [manual_entry.md](manual_entry.md)
- ui_feedback.py
