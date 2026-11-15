# POS Development Environment

## Verified baseline

The verified Windows baseline is **CPython 3.12.10, 64-bit**. The current Ubuntu VM uses **CPython 3.12.3, 64-bit** in its own local virtual environment.
The application uses PyQt5 and SQLite. The project source relies on f-string syntax that Python 3.11 cannot parse, so Python 3.12 or later is required. Both current interpreters support that syntax; the Ubuntu environment does not exactly reproduce the Windows baseline. Record and compare Python, PyQt5 and Qt versions when investigating platform differences.

The production application is distributed as a PyInstaller bundle. Its runtime is part of the deployed application folder, so installing or changing Python on a development machine does not affect an already deployed client installation.

## Ubuntu VM setup

Use Ubuntu for primary development and Windows for target-platform UI checks, hardware integration testing and Windows release builds. Each VM must have its own `.venv` at the repository root; do not copy an environment between operating systems.

The following commands assume Ubuntu's Python 3.12 is installed. Install the Ubuntu system prerequisites first:

```bash
sudo apt update
sudo apt install python3.12-venv libxcb-xinerama0
```

- `python3.12-venv` provides virtual environment creation support, including `ensurepip`.
- `libxcb-xinerama0` provides `libxcb-xinerama.so.0`, required by the installed Qt XCB platform plugin to initialize the graphical interface. Ubuntu system packages belong in these setup instructions, not in `Project/requirements.txt`.

For a new checkout without an existing `.venv`, create and activate the environment, then install the Python dependencies:

```bash
cd /home/sthiagar/Desktop/Projects/POS_Dev
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r Project/requirements.txt
```

Adjust the repository path if the checkout is elsewhere. Verify the environment:

```bash
python --version
python -c "import sys; print(sys.executable)"
python -m pip check
python -c "from PyQt5.QtCore import PYQT_VERSION_STR, QT_VERSION_STR; print('PyQt5:', PYQT_VERSION_STR, 'Qt:', QT_VERSION_STR)"
```

The interpreter path should end in `POS_Dev/.venv/bin/python`. In VS Code, run **Python: Select Interpreter** from the Command Palette and select that interpreter.

Run the application from the activated environment:

```bash
cd Project
python main.py
```

The configured development database must already exist at `db/Anumani.db` relative to the repository root. On later terminal sessions, activate the existing environment rather than creating it again:

```bash
cd /home/sthiagar/Desktop/Projects/POS_Dev
source .venv/bin/activate
cd Project
python main.py
```

### Ubuntu Qt startup troubleshooting

If startup ends with `Aborted (core dumped)` and the log reports that no Qt platform plugin could be initialized, inspect the plugin's system dependencies from the repository root:

```bash
ldd .venv/lib/python3.12/site-packages/PyQt5/Qt5/plugins/platforms/libqxcb.so
```

On November 13, 2026, this showed `libxcb-xinerama.so.0 => not found`. Installing `libxcb-xinerama0` resolved that missing dependency. If this library is already installed, inspect the current error and any other `not found` entries before choosing another fix. A successful `pip check` verifies Python dependency compatibility; it does not check Qt's Ubuntu system libraries.

The application log is `live_logs/error.log`. Use each entry's timestamp to distinguish an earlier startup failure from a new one; exporting the log does not make old entries new failures.

### Ubuntu verification — November 13, 2026

- Root-level `.venv` uses Python 3.12.3, with pip and PyQt5 installed inside it.
- `python -m pip check` reports no broken requirements.
- PyQt5 reports version 5.15.11 and Qt reports version 5.15.14.
- Ubuntu packages `python3.12-venv` and `libxcb-xinerama0` are installed.
- `db/Anumani.db` exists; the user reported reaching login after the startup fix. Full application, UI and hardware regression testing remains outstanding.

## Windows setup

From the repository root, create a clean virtual environment and install the declared dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r Project\requirements.txt
python --version
python -m pip check
```

To reproduce the verified Windows baseline, the version command must report `Python 3.12.10`. The `py -3.12` selector chooses a registered Python 3.12 installation, so check its actual patch version.

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

## Windows verification performed on October 18, 2026

- `.venv` reports Python 3.12.10.
- `python -m pip check` reports no broken requirements.
- All 179 Python files under `Project/` compile successfully.
- Installed packages include PyQt5 5.15.11, pynput 1.8.2, python-escpos 3.1, openpyxl 3.1.5, xlwt 1.3.0, qrcode 8.2, and Pillow 13.0.0.

## Environment rules

- Keep each VM's virtual environment at the repository root, local and uncommitted; do not share `.venv/` between operating systems.
- Use `python -m pip`, never bare `pip`, so packages are installed into the active interpreter.
- `Project/requirements.txt` declares minimum dependency versions. A fresh environment can therefore install newer package releases. Record exact versions before making a production build.
- Before building a new production bundle, test the source application and the packaged executable, including the scanner, printer, cash drawer, reports, and customer display.
