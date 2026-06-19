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
- Verification: 2 path tests and the full 57-test suite passed; Python source
  compilation passed.
- Status: pending review and approval.
