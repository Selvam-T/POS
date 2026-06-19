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
|-- data\                Writable application data (Phase 4)
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
`-- data\                Writable application data
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
