
# FieldCoordinator & Coordination Layer Documentation

## Purpose
FieldCoordinator is the heart of the Centralized Relationship Coordinator architecture. It manages all cross-widget relationships, focus navigation, and UI feedback in a declarative, rules-based manner for PyQt5 dialogs.

## Key Concepts
- **Declarative Links:** Define all widget relationships up front using `add_link`, not scattered signal connections.
- **Signal Intelligence:** Listens only to user-driven signals (e.g., `textEdited`), not programmatic changes.
- **Reverse Action:** Clearing a source widget clears all mapped targets and resets status.
- **Infinite Loop Prevention:** Blocks signals during programmatic updates to avoid feedback loops.
- **Focus Navigation:** Handles auto-jump to next field or triggers custom actions on Enter.
- **UI Feedback:** Integrates with `ui_feedback.py` and QSS for consistent status coloring.

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
   ```
3. **Final Validation:**
   Use pure input_handler getters in your OK handler for final data extraction and validation.

## add_link Parameters
- `source`: The user-editable widget (QLineEdit/QComboBox).
- `target_map`: Dict mapping data keys to widgets to fill.
- `lookup_fn`: Stateless function returning a dict or None.
- `next_focus`: Widget or function to trigger on Enter.
- `status_label`: QLabel for status feedback (QSS property + re-polish).
- `on_sync`: Optional hook after sync (e.g., update placeholders).

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
- All cross-widget logic must be declared via FieldCoordinator.
- Input handlers must remain pure (no widget manipulation).
- UI feedback and styling are handled via QSS properties and re-polish (see ui_feedback.py).
- For new dialogs, always follow the three-step implementation guide in the Centralized Relationship Coordinator documentation.

## See Also
- [centralized_relationship_coordinator.md](centralized_relationship_coordinator.md)
- [input_handler.md](input_handler.md)
- [manual_entry.md](manual_entry.md)
- ui_feedback.py
