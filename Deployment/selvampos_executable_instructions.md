# SelvamPOS Executable Build and Manual Deployment Guide

This guide is for the first production release, version `1.0.0`.

For now, the production build can be prepared from a separate staging folder
such as `POS - Prod` to avoid confusion with the active development workspace.
Later, the development and production build flow can be reconciled into one
clean project structure.

## Recommended Rule

Use a build script for repeatable builds.

Do not manually type the full PyInstaller command every time unless you are
testing or troubleshooting. The script keeps the app name, version, icon,
runtime resources, and Windows version metadata consistent.

## Version Rules

The application version is owned by:

```text
Project\config.py
```

Current first release:

```python
APP_VERSION = '1.0.0'
```

Use semantic versioning:

```text
1.0.0 = First stable production release
1.1.0 = Feature release
1.1.1 = Bug-fix release
2.0.0 = Major release with breaking behavior, data, or deployment changes
```

Windows executable metadata is owned by:

```text
Deployment\version_info.txt
```

Keep `Deployment\version_info.txt` aligned with `APP_VERSION`. Windows file
versions use four numeric parts, so app version `1.0.0` is written as:

```text
filevers=(1, 0, 0, 0)
prodvers=(1, 0, 0, 0)
```

For version `1.0.0`, put this content in `Deployment\version_info.txt`:

```python
# UTF-8
#
# Windows executable version metadata for PyInstaller.
# Keep FileVersion/ProductVersion aligned with Project/config.py APP_VERSION.
# Windows requires four numeric parts, so APP_VERSION 1.0.0 becomes 1,0,0,0.

VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'Anumani Trading Pte Ltd'),
          StringStruct('FileDescription', 'SelvamPOS point of sale application'),
          StringStruct('FileVersion', '1.0.0'),
          StringStruct('InternalName', 'SelvamPOS'),
          StringStruct('OriginalFilename', 'SelvamPOS.exe'),
          StringStruct('ProductName', 'SelvamPOS'),
          StringStruct('ProductVersion', '1.0.0')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
```

For a future version, update `APP_VERSION`, `filevers`, `prodvers`,
`FileVersion`, and `ProductVersion` together.

Trial-build settings are separate from the release version. These are not the
app version:

```text
TRIAL_BUILD_ENABLED
TRIAL_EXPIRY_DATE
modules\runtime\trial_build.py
```

## Production Staging Folder

For the temporary production build workspace, use this kind of structure:

```text
POS - Prod\
|-- build_exe.bat
|-- Deployment\
|   `-- version_info.txt
|-- ico\
|   `-- selvam_pos.ico
|-- Project\
|   |-- main.py
|   |-- config.py
|   |-- modules\
|   |-- ui\
|   |-- assets\
|   |-- requirements.txt
|   `-- other required runtime source files
|-- db\
|   `-- Anumani.db
|-- data\
|   |-- json\
|   `-- ads\
|-- logs\
|-- backups\
`-- USERGUIDE.md
```

Only copy files required for building and first deployment. Do not copy old
development-only clutter into the production staging folder.

## Required Build Inputs

Before building, confirm these files and folders exist in `POS - Prod`:

```text
Project\main.py
Project\config.py
Project\modules\
Project\ui\
Project\assets\
Project\requirements.txt
Deployment\version_info.txt
ico\selvam_pos.ico
db\Anumani.db
USERGUIDE.md
```

Writable client data must stay outside the packaged app:

```text
db\
logs\
backups\
data\json\
data\ads\
```

Do not bundle `db\Anumani.db`, `logs`, `backups`, or `data` into the EXE
internal application folder. They belong beside the `app` folder on the client
machine.

## Install PyInstaller

Run once on the build machine:

```bat
pip install pyinstaller
```

If dependencies are not already installed, run from the staging root:

```bat
pip install -r Project\requirements.txt
```

## Build Script

Create this file in the staging root:

```text
POS - Prod\build_exe.bat
```

Content:

```bat
@echo off
setlocal

set APP_NAME=SelvamPOS
set VERSION=1.0.0
set ENTRY_FILE=Project\main.py
set ICON_FILE=ico\selvam_pos.ico
set VERSION_FILE=Deployment\version_info.txt

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist %APP_NAME%.spec del /q %APP_NAME%.spec

pyinstaller ^
  --noconfirm ^
  --onedir ^
  --windowed ^
  --name %APP_NAME% ^
  --icon %ICON_FILE% ^
  --version-file %VERSION_FILE% ^
  --add-data "Project\ui;ui" ^
  --add-data "Project\assets;assets" ^
  %ENTRY_FILE%

if errorlevel 1 (
  echo.
  echo Build failed.
  pause
  exit /b 1
)

if exist release rmdir /s /q release
mkdir release

powershell Compress-Archive ^
  -Path dist\%APP_NAME%\* ^
  -DestinationPath release\%APP_NAME%-%VERSION%-app.zip ^
  -Force

echo.
echo Build complete.
echo Application ZIP created:
echo release\%APP_NAME%-%VERSION%-app.zip
echo.
pause
```

Run from the staging root:

```bat
build_exe.bat
```

## Direct PyInstaller Command

If you need to run the command manually, run from the staging root:

```bat
pyinstaller --noconfirm --onedir --windowed --name SelvamPOS --icon ico\selvam_pos.ico --version-file Deployment\version_info.txt --add-data "Project\ui;ui" --add-data "Project\assets;assets" Project\main.py
```

If you build from inside the `Project` directory instead, the version-file path
changes:

```powershell
pyinstaller --name SelvamPOS --version-file ..\Deployment\version_info.txt main.py
```

## PyInstaller Output

After a successful build:

```text
POS - Prod\
|-- dist\
|   `-- SelvamPOS\
|       |-- SelvamPOS.exe
|       `-- _internal\
`-- release\
    `-- SelvamPOS-1.0.0-app.zip
```

The ZIP contains only the packaged application folder contents. It does not
contain the client database, logs, backups, user guide, or external data folders.

## What the PyInstaller Options Mean

`--noconfirm`

Overwrites old build files without asking.

`--onedir`

Creates one application folder containing the EXE and dependencies. This is
recommended for POS applications.

`--windowed`

Runs without opening a black command prompt window. This is recommended for GUI
apps.

`--name SelvamPOS`

Creates:

```text
SelvamPOS.exe
```

`--icon ico\selvam_pos.ico`

Bakes the icon into the EXE file.

`--version-file Deployment\version_info.txt`

Bakes Windows file metadata into the EXE, including product name and version.

`--add-data "Project\ui;ui"`

Copies Qt Designer `.ui` files into the packaged runtime resources.

`--add-data "Project\assets;assets"`

Copies static runtime assets, including QSS, icons, and images, into the
packaged runtime resources.

## Client Installation Structure

For the first release, it is acceptable to skip a formal installer and manually
create the client folder structure.

Create this on the client PC:

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

Manual deployment steps:

1. Create `C:\SelvamPOS`.
2. Create `C:\SelvamPOS\app`.
3. Copy everything from `dist\SelvamPOS\` into `C:\SelvamPOS\app\`.
4. Create `C:\SelvamPOS\db`.
5. Copy the starting database to `C:\SelvamPOS\db\Anumani.db`.
6. Copy `USERGUIDE.md` to `C:\SelvamPOS\USERGUIDE.md`.
7. Create `C:\SelvamPOS\logs`.
8. Create an empty `C:\SelvamPOS\logs\error.log` if it does not exist.
9. Create `C:\SelvamPOS\backups`.
10. Create `C:\SelvamPOS\data\json`.
11. Create `C:\SelvamPOS\data\ads`.
12. Copy starter JSON/data files and starter ads only if they are required for
    the first client setup.

## Important Data Safety Rule

The client database and writable data are business data.

Do not overwrite these during normal upgrades:

```text
C:\SelvamPOS\db\Anumani.db
C:\SelvamPOS\data\
C:\SelvamPOS\logs\
C:\SelvamPOS\backups\
```

For a future version such as `1.1.0`, replace only:

```text
C:\SelvamPOS\app\
```

Always back up this file before upgrading:

```text
C:\SelvamPOS\db\Anumani.db
```

Only replace or modify the live database when the release includes a reviewed
database migration or support procedure.

## Running the Application

Command line:

```bat
C:\SelvamPOS\app\SelvamPOS.exe
```

GUI:

```text
Open C:\SelvamPOS\app\
Double-click SelvamPOS.exe
```

## Desktop Shortcut

Right-click:

```text
C:\SelvamPOS\app\SelvamPOS.exe
```

Select:

```text
Send To -> Desktop (Create Shortcut)
```

Rename the shortcut:

```text
SelvamPOS
```

## Future Installer

PyInstaller only creates the executable application folder. It does not create a
complete professional Windows installer.

For a future release, use an installer tool such as:

```text
Inno Setup
```

The installer can:

- Install files to `C:\SelvamPOS\`.
- Copy `SelvamPOS.exe` and `_internal` to `C:\SelvamPOS\app`.
- Copy `USERGUIDE.md`.
- Create `db`, `logs`, `backups`, `data\json`, and `data\ads` when missing.
- Create desktop and Start Menu shortcuts.
- Avoid overwriting the client's live database and writable data during
  upgrades.

Recommended installer name:

```text
SelvamPOS-Setup-1.0.0.exe
```

## Taskbar Pinning

Windows generally prevents applications from silently pinning themselves to the
taskbar.

Industry practice:

- Create desktop shortcut.
- Create Start Menu shortcut.
- Let the user manually select "Pin to taskbar".

## What Is the `.spec` File?

When PyInstaller builds your app, it creates:

```text
SelvamPOS.spec
```

The `.spec` file is a PyInstaller build configuration file. It remembers build
details such as:

- Entry file.
- App name.
- Icon.
- Version file.
- Extra files.
- Hidden imports.
- Build mode.

For simple builds, you can delete it and rebuild using `build_exe.bat`.

For advanced builds, edit the `.spec` file and build using:

```bat
pyinstaller SelvamPOS.spec
```

For now, use the `.bat` script.

## Trial Expiry

Industry practice is to disable usage after expiry, not delete files.

The current project controls trial behavior from `Project\config.py`:

```python
TRIAL_BUILD_ENABLED = False
TRIAL_EXPIRY_DATE = date(2026, 6, 30)
TRIAL_EXPIRED_MESSAGE = 'Testing period expired. Please contact SelvamPOS support.'
```

Before creating a trial executable, refresh the embedded UTC build timestamp
from the `Project` directory:

```powershell
python dev_tools\maintenance\write_trial_build_timestamp.py
```

Do not:

- Delete client files.
- Rename files randomly.
- Destroy databases.
- Self-destruct the application.

Instead:

- Block login.
- Display the expiry message.
- Keep client data intact.
