# SelvamPOS release builds

## Build a release

From the repository root:

```powershell
.\Deployment\build_release.bat
```

Complete [machine setup](#new-machine-setup), review [configuration](#release-configuration),
and prepare the starter data before running. Wait for **Release complete**.

Outputs:

- `Production/dist/SelvamPOS/` ? executable, `_internal/`, and build manifest.
- `Production/release/SelvamPOS-Setup-<APP_VERSION>.exe` ? installer to distribute.

A failed stage stops the release and returns a nonzero exit code. Old outputs may
remain after failure. Rebuilding the same version replaces its generated output.

For a custom Inno Setup location:

```powershell
.\Deployment\build_release.bat --iscc "C:\Tools\Inno Setup 7\ISCC.exe"
```

You can also set `ISCC_EXE` to the compiler path. Use `build_release.bat --help`
for usage. Scripts select the repository's `.venv` and resolve paths independently
of the working directory.

## How the build works

```text
Development/src/config.py -> generated version metadata
Development/src/         -> PyInstaller -> Production/dist/SelvamPOS/
Executable + starter data -> Inno Setup -> Production/release/
```

The executable build generates metadata and bundles Python, Qt, UI, static assets,
and application dependencies. Writable client data stays outside the bundle.
The installer build validates the production manifest, version, source/resources,
and package hashes; stages the inputs; then compiles the installer.

The starter database comes from `Development/db/<DATABASE_FILENAME>`. SQLite's
backup API includes committed WAL transactions and creates a checked, standalone
snapshot. Runtime starter files come from `Development/runtime_data/`; placeholders
are excluded. Development logs and backups are not packaged.

## New-machine setup

Install **Windows x64 Python 3.12.10**, clone the repository, then run:

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r Development\requirements.txt -r Deployment\requirements-build.txt
```

Confirm the Python patch version before creating `.venv`.
`Development/requirements.txt` supplies runtime dependencies;
`Deployment/requirements-build.txt` supplies pinned PyInstaller/build hooks.
Both install into `.venv`, which is recreated locally rather than committed.
Activation is optional. Runtime requirements use minimum versions, not a complete lock.

Separately install [Inno Setup](https://jrsoftware.org/isinfo.php), verified here
with **7.1.1**. It is a Windows compiler, not a pip package. The build searches PATH
and common Inno Setup 7/6 directories; use `--iscc` for other locations.

Restore approved starter database/runtime contents under `Development/db/` and
`Development/runtime_data/`: Git excludes them, so a fresh clone does not contain
them. The installer also requires `Development/USERGUIDE.md`; the executable
requires `src/ui/`, `src/assets/`, and `src/assets/ico/selvampos.ico`.

## Release configuration

Edit [Development/src/config.py](../Development/src/config.py) before building:

| Setting | Meaning |
|---|---|
| `APP_VERSION` | Single release version: `major.minor.patch`, each component 0?65535, with no leading zeroes or suffixes. |
| `DEVELOPER_NAME` | Software publisher: Windows CompanyName and installer publisher. |
| `COMPANY_NAME` | Client business name displayed by the application. |
| `PRODUCTION_MODE` | Must be `True` for a release; requires login and sets production defaults. |
| `PRINTER_OVERRIDE`, `CASH_DRAWER_OVERRIDE` | `None` follows the mode; `True`/`False` enables/disables each feature independently. |
| `CUSTOMER_DISPLAY_MODE_OVERRIDE` | `None` follows the mode; `'off'`, `'same_screen'`, or `'second_screen'` overrides it. |

`same_screen` opens separate cashier and customer windows on one monitor.
`second_screen` places the customer display fullscreen on the configured second
monitor, hiding it when unavailable. Trial, weighing fallback, and scanner trace
settings remain independent; for trials, review expiry and run
`Development/src/dev_tools/maintenance/write_trial_build_timestamp.py` with `.venv` Python.

Metadata generation reads constants without executing config.py and rejects
invalid values. Both executable FileVersion and ProductVersion use APP_VERSION;
`1.2.3` becomes numeric `(1, 2, 3, 0)`. Installer version and filename use the same
source. Do not edit generated metadata. See [configuration details](../Development/src/module_docs/config.md).

## Deployment files

```text
Deployment/
|-- README.md
|-- build_release.bat
|-- build_exe.bat
|-- build_installer.bat
|-- requirements-build.txt
|-- scripts/
|   |-- build_exe.py
|   |-- build_installer.py
|   `-- generate_version_info.py
|-- installer/
|   `-- SelvamPOS.iss
|-- generated/
|   |-- .gitkeep
|   |-- version_info.txt
|   `-- version_info.iss
`-- tests/
```

| File | Purpose |
|---|---|
| `build_release.bat` | Run executable build, then installer build only after success. |
| `build_exe.bat`, `build_installer.bat` | Locate `.venv`, invoke the corresponding Python helper, return its exit code. |
| `scripts/build_exe.py` | Check inputs/mode, generate metadata, run PyInstaller, and write `build_metadata.json` with version and source/package hashes. |
| `scripts/build_installer.py` | Reject stale/development packages, snapshot starter inputs, compile and publish the installer. |
| `scripts/generate_version_info.py` | Generate Windows executable metadata (`version_info.txt`) and Inno definitions (`version_info.iss`). |
| `installer/SelvamPOS.iss` | Define destination folders, data protection, permissions, shortcuts, and uninstall behavior. Keep its AppId stable across releases. |
| `requirements-build.txt` | Pin build-tool dependencies. |
| `tests/` | Unit checks and an explicit disposable installer verification script. |

## Generated outputs and Git

| Ignored location | Reason |
|---|---|
| `.venv/` | Local Python environment and installed packages. |
| `Deployment/generated/` | Regenerated version metadata and temporary files. |
| `Production/build/` | PyInstaller work/cache, generated `.spec` configuration, installer staging, and test layouts. |
| `Production/dist/` | Executable and bundled dependencies. |
| `Production/release/` | Compiled installers. |
| `Development/` database, runtime data, logs, and backups | Local mutable data and starter inputs, managed separately from source. |
| `.env`, `.env.*`, credential/token JSON files | Local environment settings and credentials; `.env.example`, `.env.sample`, and `.env.template` remain trackable. |

Track scripts, requirements, installer template, tests, and documentation.
`.gitkeep` is explicitly allowed in `Deployment/generated/`, each Production
output directory, and Development's db, logs, backups, runtime_data, json, and ads
directories so Git preserves the empty skeleton. Other contents are ignored.
The `.venv` directory stays fully ignored and is recreated during machine setup.

## Install and uninstall

Run the release installer on the client. It requests administrator permission and
installs by default into `C:\SelvamPOS` on the Windows system drive:

```text
C:\SelvamPOS\
|-- app\                 SelvamPOS.exe, _internal\, build manifest and uninstaller
|-- db\Anumani.db
|-- runtime_data\
|   |-- json\
|   `-- ads\
|-- live_logs\
|-- backups\
`-- USERGUIDE.md
```

A Start Menu shortcut is created; desktop shortcut and launch-after-install are
optional and initially unchecked. Standard Windows users can modify the data
folders. Existing database/runtime files are skipped; missing seed files may be
added during reinstall. Close POS and back up client data before upgrading.
There are no automatic schema migrations.

Uninstall through **Windows Settings ? Apps ? Installed apps ? SelvamPOS**.
Application files, guide, and shortcuts are removed; databases, runtime data,
logs, and backups remain. The current installer includes starter data.

## Verification and troubleshooting

Unit checks:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s Deployment/tests -v
```

Explicit install/reinstall/uninstall verification:

```powershell
.\.venv\Scripts\python.exe -B Deployment\tests\verify_installer.py
```

This compiles a test variant and verifies data preservation inside
`Production/build/`, without elevation, system shortcuts, or application
registration. Test UAC, shortcuts, login, displays, exports, printing, and drawer
operation separately on a disposable client/VM before distribution.

For individual steps, use `build_exe.bat` or `build_installer.bat`.
`build_exe.bat --development` allows packaging with PRODUCTION_MODE=False;
its output cannot be used for a release installer.

Check console errors and `Production/build/SelvamPOS/warn-SelvamPOS.txt` for build
issues. Installer staging, integration logs, and verification.json remain under
`Production/build/installer-*/`. Runtime errors use the client's
`live_logs/error.log`. Rebuild the EXE after source/config changes or a package
fingerprint mismatch. Keep the entire `_internal/` directory with the EXE.
