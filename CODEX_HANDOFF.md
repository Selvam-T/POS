# CODEX Handoff

Read this file before changing the POS project on another machine. Update it when handing work to the next Codex session or developer.

## Current state — October 18, 2026

- Repository base commit: `755d234 feat(diagnostics): report products with missing cost prices`.
- The verified source-development interpreter is **CPython 3.12.10, 64-bit**.
- The local `.venv` was recreated with Python 3.12.10 and dependencies were installed from `Project/requirements.txt`.
- The POS application now starts past the previous report-viewer syntax failure.
- Documentation now identifies Python 3.12.10 and PyQt5 as the current source-development baseline. Older Tkinter/ttkbootstrap documents are marked as historical prototypes.

## What changed

- No application source code was changed to resolve the startup error.
- The former error at `Project/modules/menu/report_viewers.py:366` occurred because Python 3.11 cannot parse the nested f-string syntax used there. Python 3.12 can parse it.
- `.venv/` is ignored by Git so the local environment is not accidentally committed.
- `Documentation/Python Environment.md` is the canonical environment setup reference.

## Verified commands and results

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

Investigate the slight widget-rendering difference seen after recreating the environment. Obtain a screenshot and identify the affected widgets before changing code. Compare Windows display scaling, monitor resolution, PyQt5/Qt version, and stylesheet behavior.

## Deferred work

- Do not change `Project/config.py` yet.
- Customer-display and secondary-monitor configuration remain deferred.
- Do not build or deploy a new production package until the source application and a packaged build have been tested with the production hardware.

## Local workspace notes

- `.venv/` is local and must remain uncommitted.
- `live_logs/` is runtime output. Preserve any user-created files there unless the task explicitly requires changing them.
