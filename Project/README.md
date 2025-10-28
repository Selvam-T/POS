PyQt5 POS UI scaffold

This workspace contains a minimal scaffold for the POS UI you described. It purposely focuses on UI layout and loading .ui files at runtime. No database or hardware logic is implemented yet.

Files and folders:
- main.py - entry point. (Two variants available)
   - `main.py` (programmatic UI) now builds the UI directly in code (converted from your HTML mockup).
   - Alternatively you can use the `.ui` files in `ui/` and load them with `PyQt5.uic` or compile them into `ui_compiled/`.
- ui/ - Qt Designer .ui files (`main_window.ui`, `sales_frame.ui`). Open these in Qt Designer to edit visually.
- ui_compiled/ - place for generated Python UI modules (optional).
- logic/, db/, hardware/, assets/, config/ - empty folders for future implementation.
- requirements.txt - Python dependencies.

Quick start (Windows, cmd.exe):
1. Create and activate a virtual environment (recommended):
   py -3 -m venv .venv
   .venv\Scripts\activate
2. Install dependencies:
   pip install -r requirements.txt
3. Run the app:
   - To run the programmatic UI (current `main.py`):
     py main.py
   - To run the .ui-loading variant, replace `main.py` with a loader that uses `PyQt5.uic.loadUi` or run the earlier scaffolded loader we provided.

   Note: The current `main.py` now composes `ui/main_window.ui`, `ui/sales_frame.ui`, and `ui/payment_frame.ui` at runtime and will apply `assets/style.qss` if present.

Convert .ui to .py (optional, for production):
- Use pyuic5 to convert:
  py -m PyQt5.uic.pyuic -x ui\main_window.ui -o ui_compiled\main_window_ui.py
  py -m PyQt5.uic.pyuic -x ui\sales_frame.ui -o ui_compiled\sales_frame_ui.py

Notes:
- By default `main.py` loads .ui at runtime. You can import the compiled modules instead for a slightly faster startup.
- Object names in the .ui files match the names you requested (labelCompany, labelDate, labelDay, labelTime, salesTable, vegBtn, manualBtn, totalTitle, totalValue, cancelsaleBtn, onholdBtn, viewholdBtn, burgerBtn).
- Next step: add signals/slots and a mediator in `main.py` to route events between frames without tight coupling.

If you'd like, I can now:
- Add initial signal/slot wiring and stub logic for adding items to the transaction table and updating totals.
- Convert the programmatic UI into `.ui` files (or convert your existing `.ui` files into compiled `.py` modules).
- Add a small SQLite schema and a data access layer under `db/`.
