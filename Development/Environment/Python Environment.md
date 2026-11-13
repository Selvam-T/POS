# POS Development Environment

## Verified baseline

Use **CPython 3.12.10, 64-bit** for source development of this POS application.
The application uses PyQt5 and SQLite. The project source relies on f-string syntax that Python 3.11 cannot parse, so Python 3.12 or later is required. Python 3.12.10 is the selected, verified baseline.

The production application is distributed as a PyInstaller bundle. Its runtime is part of the deployed application folder, so installing or changing Python on a development machine does not affect an already deployed client installation.

## Windows setup

From the repository root, create a clean virtual environment and install the declared dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r Project\requirements.txt
python --version
python -m pip check
```

The version command must report `Python 3.12.10` before development or testing.

If the Python install manager is installed and an older `py.exe` launcher takes priority, use `pymanager` to install Python 3.12, then create the environment with the registered Python 3.12 interpreter:

```powershell
pymanager install 3.12
py -3.12 -m venv .venv
```

Run the application from the activated environment:

```powershell
cd Project
python main.py
```

## Verification performed on October 18, 2026

- `.venv` reports Python 3.12.10.
- `python -m pip check` reports no broken requirements.
- All 179 Python files under `Project/` compile successfully.
- Installed packages include PyQt5 5.15.11, pynput 1.8.2, python-escpos 3.1, openpyxl 3.1.5, xlwt 1.3.0, qrcode 8.2, and Pillow 13.0.0.

## Environment rules

- Keep the virtual environment local; do not commit `.venv/`.
- Use `python -m pip`, never bare `pip`, so packages are installed into the active interpreter.
- `Project/requirements.txt` declares minimum dependency versions. A fresh environment can therefore install newer package releases. Record exact versions before making a production build.
- Before building a new production bundle, test the source application and the packaged executable, including the scanner, printer, cash drawer, reports, and customer display.
