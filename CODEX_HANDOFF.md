# CODEX Handoff

Read this file before changing the POS project on another machine. Update it when handing work to the next Codex session or developer.

## Current state — November 13, 2026

- Primary development is now on the Ubuntu VM; retain Windows for UI validation, hardware integration tests and Windows release builds.
- Ubuntu has its own repository-root `.venv` using **CPython 3.12.3, 64-bit**. The previously verified Windows baseline remains **CPython 3.12.10, 64-bit**; these environments do not have identical patch versions.
- Dependencies were installed from `Project/requirements.txt`. The file specifies minimum versions, so future installations can resolve to different package versions.
- Ubuntu prerequisites are `python3.12-venv` and `libxcb-xinerama0`. The latter provides `libxcb-xinerama.so.0`, required by Qt's XCB platform plugin.
- Initial Ubuntu startup aborted because `libxcb-xinerama.so.0` was missing. The package is now installed, and the user reported reaching login. Full application and hardware testing has not been completed.
- No application source or `Project/config.py` changes were needed for this environment setup.
- Follow [Python Environment.md](Development/Environment/Python%20Environment.md) for canonical Ubuntu and Windows setup instructions. The [VM guide](Development/Setup_and_Maintenance/POS_Development_VM_Guide.html) describes the workflow across both guests.

## Ubuntu verification and launch — November 13, 2026

Verified locally:

- Interpreter: `/home/sthiagar/Desktop/Projects/POS_Dev/.venv/bin/python`, Python 3.12.3.
- pip and PyQt5 are installed inside that virtual environment.
- `python -m pip check`: no broken requirements.
- PyQt5 5.15.11; Qt 5.15.14.
- Ubuntu packages `python3.12-venv` and `libxcb-xinerama0` are installed.
- The configured database exists at `db/Anumani.db`.

From the repository root:

```bash
source .venv/bin/activate
python --version
python -m pip check
cd Project
python main.py
```

In VS Code, select the repository's `.venv/bin/python` using **Python: Select Interpreter**. Each new terminal session needs activation, or commands must invoke the environment's interpreter directly.

The Qt platform-plugin failure logged at 3:31:59 PM on November 13 was the earlier startup failure. A later export timestamp does not indicate another failure; inspect individual entry timestamps before diagnosing a recurrence.

## Previous Windows state — October 18, 2026

- Repository base commit: `755d234 feat(diagnostics): report products with missing cost prices`.
- The verified source-development interpreter is **CPython 3.12.10, 64-bit**.
- The local `.venv` was recreated with Python 3.12.10 and dependencies were installed from `Project/requirements.txt`.
- The POS application now starts past the previous report-viewer syntax failure.
- Documentation now identifies Python 3.12.10 and PyQt5 as the current source-development baseline. Older Tkinter/ttkbootstrap documents are marked as historical prototypes.
- Repository-level documentation is organized under `Development/`: architecture, environment, requirements, UI references, and setup/maintenance.

## Previous Windows changes

- No application source code was changed to resolve the startup error.
- The former error at `Project/modules/menu/report_viewers.py:366` occurred because Python 3.11 cannot parse the nested f-string syntax used there. Python 3.12 can parse it.
- `.venv/` is ignored by Git so the local environment is not accidentally committed.
- `Development/Environment/Python Environment.md` is the canonical environment setup reference.
- Current system architecture and technical overview are in `Development/Architecture/`.
- Feature and module implementation references remain in `Project/Documentation/`.

## Previously verified Windows commands and results

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip check
```

Verified results on October 18, 2026:

- Python 3.12.10.
- No broken requirements.
- All 179 Python files under `Project/` compiled successfully with Python 3.12.10.

Run the development application:

```powershell
cd Project
..\.venv\Scripts\python.exe main.py
```

## Next task

Complete Ubuntu source-application checks, including basic navigation and reports, then compare the same source revision on Windows. Startup success does not verify transactions or physical devices.

Investigate the slight widget-rendering difference seen after recreating the environment. Obtain a screenshot and identify the affected widgets before changing code. Compare Windows display scaling, monitor resolution, PyQt5/Qt version, and stylesheet behavior.

## Deferred work

- Do not change `Project/config.py` yet.
- Customer-display and secondary-monitor configuration remain deferred.
- Do not build or deploy a new production package until the source application and a packaged build have been tested with the production hardware.

## Local workspace notes

- `.venv/` is local and must remain uncommitted.
- `live_logs/` is runtime output. Preserve any user-created files there unless the task explicitly requires changing them.
