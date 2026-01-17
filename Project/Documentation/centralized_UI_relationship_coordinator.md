# Centralized Relationship Coordinator Architecture

## 1. Overview & Design Philosophy
The Centralized Relationship Coordinator is a rules-based design pattern for PyQt5 dialogs. It replaces traditional spaghetti logic—where every widget manually monitors and updates every other widget—with a central "brain" (FieldCoordinator) that manages relationships between inputs.

### Core Objectives
- **Declarative Logic:** Define "Links" between widgets once, rather than writing dozens of signal connections.
- **Infinite Loop Prevention:** Automatically blocks signals during programmatic updates to prevent "ping-pong" effects between cross-linked widgets.
- **Standardized UX:** Ensures that every dialog in the system handles focus, error coloring, and data clearing in the exact same way.
- **Separation of Concerns:** Business logic (Database), Validation logic (Rules), and UI logic (Focus/Styles) are kept in isolated layers.

## 2. The Architectural Layers
- **Presentation Layer (assets/menu.qss):** Uses dynamic QSS properties for status and error coloring. Styling changes require only QSS edits.
- **Feedback Layer (modules/ui_utils/ui_feedback.py):** Updates widget status properties and triggers style re-polish to reflect QSS changes.
- **Coordination Layer (modules/ui_utils/focus_utils.py):** FieldCoordinator manages all widget relationships, focus, and reverse actions. Uses user-driven signals only.
- **Service Layer (modules/ui_utils/input_handler.py):** Stateless, pure functions for data lookup and validation. No widget manipulation.
- **Data Layer (modules/db_operation/):** Product cache and SQL repository. `product_cache.py` provides fast lookups; `products_repo.py` is SQL-only.

## 3. The Interaction Flow ("Life of a Keypress")
1. User types in a widget.
2. FieldCoordinator intercepts the signal.
3. Calls the assigned lookup function.
4. If match found: updates targets, sets status to success, auto-jumps focus.
5. If not found or cleared: clears targets, sets status to error or none.
6. On Enter: validates and triggers submit action.

## 4. Implementation Guide for New Dialogs
- **Step 1:** Instantiate FieldCoordinator and keep a reference.
- **Step 2:** Define links between widgets using `add_link`.
- **Step 3:** Use pure input_handler getters for final validation in your OK handler.

### Optional: standardized focus landing and focus gating
These are opt-in helpers in `modules/ui_utils/focus_utils.py` that do not change existing dialog behavior unless used:
- `set_initial_focus(...)` — select a `QTabWidget` tab (by index or name) and focus a specific widget on open.
- `FocusGate` / `set_focus_enabled(...)` — lock a group of widgets to `Qt.NoFocus` until a prerequisite field is accepted.

## 5. Benefits Summary
- **Bug Reduction:** No more infinite update loops.
- **Speed:** Auto-jump and declarative logic make dialogs fast and user-friendly.
- **Maintenance:** Centralized logic means changes propagate everywhere instantly.

---

This document is the blueprint for maintaining and extending dialogs in the POS system. All new dialogs should follow this architecture for consistency and maintainability.
