# Production Alignment

This document records the development changes used to prepare the project for
the intended client deployment layout. Each phase is tested and reviewed before
it is committed.

## Target Layout

Development:

```text
<PROJECT ROOT>\
|-- Project\             Python source and runtime resources
|-- db\Anumani.db
|-- logs\error.log
|-- backups\
|-- data\
|   |-- json\            Writable JSON/state
|   `-- ads\             Writable customer ads
`-- ico\selvam_pos.ico   Build icon only
```

Packaged client:

```text
C:\SelvamPOS\
|-- app\
|   |-- SelvamPOS.exe
|   `-- _internal\       Bundled UI and assets
|-- db\Anumani.db
|-- logs\error.log
|-- backups\
`-- data\
    |-- json\            Writable JSON/state
    `-- ads\             Writable customer ads
```

## Path Rules

- Paths never depend on the process working directory.
- Development client root is the parent of `Project`.
- Packaged app directory is the directory containing `SelvamPOS.exe`.
- Packaged client root is the parent of the packaged `app` directory.
- Runtime UI and assets resolve relative to `config.py` through `__file__`.
- `sys.frozen`, set by PyInstaller, is used only to select the packaged root
  model. The application does not depend on `sys._MEIPASS`.
- Database, logs, backups, and writable data stay outside the packaged app.
- `POS_DB_PATH` remains an optional database override for tests and support.

## Version Mechanism

- `Project/config.py` owns the application release version in `APP_VERSION`.
- The first production release should use `APP_VERSION = '1.0.0'`.
- Use semantic versioning:
  - `1.0.0`: first stable release.
  - `1.1.0`: feature release with backward-compatible changes.
  - `1.1.1`: bug-fix release.
  - `2.0.0`: major release with breaking behavior, data, or deployment changes.
- `Deployment/version_info.txt` owns the Windows executable metadata consumed
  by PyInstaller.
- Keep `Deployment/version_info.txt` aligned with `APP_VERSION`. Windows file
  versions use four numeric parts, so app version `1.0.0` is written as
  `1,0,0,0` in `filevers` and `prodvers`.
- Trial-build settings such as `TRIAL_BUILD_ENABLED`, `TRIAL_EXPIRY_DATE`, and
  `modules/runtime/trial_build.py` are not the release version. They only
  control trial expiry and clock-rollback protection.

Build from the `Project` directory and pass the Windows version metadata file
to PyInstaller:

```powershell
pyinstaller --name SelvamPOS --version-file ..\Deployment\version_info.txt main.py
```

## Release Installer and Manual Deployment

PyInstaller builds the application executable and bundled runtime files. A
Windows installer is responsible for creating the client-machine folder layout,
copying documentation and starter data, and adding shortcuts.

The intended installer output is:

```text
C:\SelvamPOS\
|-- app\
|   |-- SelvamPOS.exe
|   `-- _internal\
|-- db\
|   `-- Anumani.db
|-- logs\
|   `-- error.log
|-- backups\
|-- data\
|   |-- json\
|   `-- ads\
`-- USERGUIDE.md
```

For the first release, it is acceptable to skip the installer package and
manually create the client folder structure if each file is placed exactly as
shown above. In that manual deployment:

- Copy the PyInstaller output into `C:\SelvamPOS\app`.
- Copy `USERGUIDE.md` to `C:\SelvamPOS\USERGUIDE.md`.
- Copy the starting database to `C:\SelvamPOS\db\Anumani.db`.
- Create `logs`, `backups`, `data\json`, and `data\ads` if they do not exist.
- Keep writable client data outside `C:\SelvamPOS\app` so future app upgrades
  can replace the executable without touching live business data.

For a later release, add an installer script, such as Inno Setup, and have it
apply only the application changes by default. Upgrade installers must not
overwrite the client's live `db\Anumani.db`, `data`, `logs`, or `backups`
content unless the release explicitly includes a reviewed migration or support
procedure. This allows a future version, for example `1.1.0`, to replace
`C:\SelvamPOS\app` while preserving the client's sales, products, ads, logs,
and backups.

## Phase Record

### Phase 0 - Dependency Baseline

- Added direct `qrcode` and `Pillow` runtime dependencies.
- Verification: dependency imports, Python compilation, 21 UI parses, and 55
  tests passed.
- Commit: `9023bcf chore: declare QR runtime dependencies`.

### Phase 1 - Central Path Model

- Added a testable development/packaged path resolver in `Project/config.py`.
- Preserved existing development paths and `_BASE_DIR` compatibility.
- Defined roots for resources, database, logs, backups, and future writable
  data without moving or creating client files.
- Added development and simulated packaged-layout tests.
- Centralized the replaceable database and login-logo filenames as
  `DATABASE_FILENAME` and `LOGIN_LOGO_FILENAME` in `Project/config.py`.
- Verification: 3 path tests and the full 58-test suite passed; Python source
  compilation passed.
- Initial path-model commit: `66da214 feat: centralize development and
  packaged paths`.
- Filename-constant follow-up: approved for commit with Phase 2.

### Phase 2 - External Database Contract

- Restricted database selection to the explicit `POS_DB_PATH` override or
  `config.DB_PATH`.
- Removed guessed `pos.db` fallback locations and the generic `DB_PATH`
  environment-variable alias.
- Added an existence check before every shared SQLite connection so a missing
  production database cannot be silently replaced with an empty file.
- Opened SQLite in read/write-only URI mode and added a blocking startup error
  that closes the application when the configured database is missing.
- Added focused tests for default selection, override selection, missing-file
  failures, and successful connections.
- Verification: 6 database-contract tests, the full 64-test suite, Python
  compilation, and 21 UI parses passed. The full suite used a disposable copy
  of the database.
- Commit: `5b102bd feat: enforce external database contract`.

### Configuration Organization

- Reordered `Project/config.py` into deployment, identity, runtime, UI,
  sales/data, validation, payment, hardware, and customer-display sections.
- Normalized indentation and replaced repetitive comments with concise section
  guidance while preserving every existing setting name and value.
- Verification: semantic comparison found no added, removed, or changed setting;
  9 focused tests, the full 64-test suite, Python compilation, and 21 UI parses
  passed. The full suite used a disposable database copy.
- Status: approved for commit.

### Phase 3 - Shared External Error Log

- Added shared `config.LOG_PATH` targeting `<CLIENT ROOT>/logs/error.log` in
  both development and packaged layouts.
- Updated the logger and footer controls to use the same path.
- Added reusable creation and truncation helpers; Clear keeps `error.log` and
  truncates it to zero bytes.
- Ignored the runtime `logs/` directory in Git.
- Added focused tests for shared path selection, creation, append, and
  truncate-in-place behavior.
- Updated active project and operator documentation to use `logs/error.log`.
- Removed the superseded root `log/` directory after confirming it contained
  only the empty legacy `error.log`.
- Verification: 4 focused log tests, the full 68-test suite, Python
  compilation, and 21 UI parses passed. The full suite used a disposable
  database copy.
- Status: approved for commit.

### Phase 4 - Runtime Resources and Writable Data

- Centralized UI and asset roots through `config.UI_DIR` and
  `config.ASSETS_DIR` for source and packaged execution.
- Added shared resource helpers and dynamic QSS rewriting for
  `url(assets/...)` references.
- Organized static stylesheets under `Project/assets/qss`; all runtime and
  documentation references use the shared `QSS_DIR` path.
- Moved JSON/state writes to `<CLIENT ROOT>/data/json` and editable ads to
  `<CLIENT ROOT>/data/ads`.
- Moved the five existing JSON/state files and ten existing ads into those
  external development folders, then removed `Project/AppData` and
  `Project/assets/ads` so user content is not bundled into `_internal`.
- Ignored the runtime `data/` directory in Git.
- Added focused resource, QSS, writable-path, and directory-creation tests.
- Verification: 4 focused Phase 4 tests, 17 combined path/data contract tests,
  the full 72-test suite, runtime import smoke checks, Python compilation, and
  21 UI parses passed. The full suite used a disposable database copy.
- The application creates missing `data/json` and `data/ads` directories but
  does not seed or copy ads from static application resources.
- Status: pending review and approval.
