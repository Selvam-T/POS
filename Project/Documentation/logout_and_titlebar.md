# Logout Dialog and Custom Title Bar

This document explains the Logout flow, the frameless custom title bar used by the Logout dialog, and how to style it using QSS.

## Overview

- The main window’s native Close (X) is disabled; users must use the Logout menu button.
- Clicking the Logout button opens a modal confirmation dialog that dims the background.
- The dialog is frameless and renders its own custom title bar inside the dialog content, which allows full styling control over background and the “X” button.

## Why frameless?

Native title bars are drawn by the OS (Windows) and can’t be recolored with Qt stylesheets. A frameless dialog lets us build our own “title bar” UI elements and style them like any other widget.

## Files and object names

- UI: `ui/logout_menu.ui`
  - Title bar frame: `QFrame#customTitleBar`
  - Title text label: `QLabel#customTitle` (hidden by default to show only the big X)
  - Close button: `QPushButton#customCloseBtn`
- Loader/controller: `modules/menu/logout_menu.py` → `launch_logout_dialog(host_window)`
  - The main menu button in `main.py` calls this function.
  - Now uses a declarative pipeline: `build_dialog_from_ui` loads the dialog, and `require_widgets` fetches the buttons by name, replacing manual widget lookup and layout code.
  - Status propagation: If the user clicks "Cancel" (NO), the dialog sets a main status message ("Logout cancelled.") using `set_dialog_main_status_max`, so the main window status bar is always up to date.
  - Security: Focus is explicitly set to the Cancel button to prevent accidental logouts from hitting Enter.
  - Fail-safe: If the .ui file is missing or widget names are wrong, the code falls back to a manual dialog, so logout is always possible.
- Styles: `assets/dialog.qss`

## Styling (QSS)

Selectors you can customize in `assets/dialog.qss`:

```css
/* Dialog background */
QDialog#LogoutDialog {
  background: #ffffff;
}

/* Custom title bar area */
QFrame#customTitleBar {
  background-color: #ffffff; /* Change to your brand color */
}

/* Big X button */
QPushButton#customCloseBtn {
  color: #310761;         /* Text (X) color */
  border: none;
  font-size: 40px;        /* Make X larger/smaller */
  min-width: 40px;        /* Click target size */
  min-height: 40px;
  max-width: 44px;
  max-height: 44px;
}
QPushButton#customCloseBtn:hover {
  background: rgba(255, 255, 255, 0.15);
}
QPushButton#customCloseBtn:pressed {
  background: rgba(255, 255, 255, 0.3);
}
```

### Important: color opacity format

- Use 6‑digit hex `#RRGGBB` for opaque colors, e.g., `#310761`.
- If you use 8‑digit hex, Qt expects `#AARRGGBB` (alpha first). For opaque, use `#ffRRGGBB` (e.g., `#ff310761`).
- A low alpha (like `#31…`) will look washed out on a white background.

## Behavior and UX

- The background dims when the dialog opens and is restored upon close.
- The dialog can be dragged by its custom title bar area (implemented in `main.py`).
- The title text is hidden to emphasize a large close (X) button; you can unhide `customTitle` if you prefer to show a caption.

## Applying the same pattern to other dialogs

To style other dialogs similarly:

1. Change their window flags to `Qt.FramelessWindowHint` in the loader code.
2. Add a `customTitleBar` frame with a `customCloseBtn` to the top of the dialog layout.
3. Optionally include a `customTitle` label and show/hide it as needed.
4. Reuse the QSS selectors or create dialog-specific ones (e.g., by dialog object name).

If you’d like, we can convert Product and Manual entry dialogs to the same custom title bar approach for visual consistency.

## Pipeline Shift: Declarative Wiring for Logout Dialog

The logout dialog now uses a declarative pipeline for UI assembly and event wiring:

- **Consolidated Setup:** Manual QDialog creation, window flags, layouts, and QSS file reading are replaced by `build_dialog_from_ui`.
- **Declarative Wiring:** `require_widgets` is used to fetch buttons, making the code more readable and robust than using multiple `findChild` calls.
- **Status Propagation:** `set_dialog_main_status_max` is called in the cancel handler, so if the user clicks "NO," the main window status bar says "Logout cancelled." instead of remaining blank.
- **Security Focus:** The Cancel button is given focus by default, so accidental Enter presses do not log out the user.
- **Clean Exit:** The dialog is only responsible for the user decision (Accept/Reject). The actual application exit is handled by the main window or dialog wrapper, maintaining separation of concerns.
- **Fail-Safe Design:** If the .ui file is missing or widget names are wrong, the fallback branch creates a working logout dialog programmatically, ensuring logout is always possible.
