# Production outputs

This directory holds generated release artifacts. Build scripts and packaging
configuration belong in [Deployment](../Deployment/), and application source stays
in [Development](../Development/).

```text
Production/
|-- README.md
|-- build/       Temporary PyInstaller output, including generated .spec files
|-- dist/        Executable package: SelvamPOS/SelvamPOS.exe and _internal/
`-- release/     Final installer: SelvamPOS-Setup-<APP_VERSION>.exe
```

Each output directory contains a tracked `.gitkeep` placeholder because Git does
not track empty directories. The root `.gitignore` excludes everything else
inside these directories, including nested files. This keeps executables,
dependencies, temporary build files, and installers out of Git while preserving
the folder skeleton on a fresh clone. `.gitkeep` has no application behavior.

These are build-machine directories. The installed application will live under
`C:\SelvamPOS\app`, with writable database, runtime data, logs, and backups beside
`app`; the repository's Production layout does not change application paths.

See [the release build guide](../Deployment/README.md) for the staged
implementation, scripts, and Git rules. Stage 4 builds the executable package;
Stage 5 builds the versioned Inno Setup installer. Generated contents are kept locally
and excluded from Git.
