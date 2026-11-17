; Compile through Deployment/build_installer.bat so inputs are validated.
#ifndef AppSource
  #error "Use Deployment/build_installer.bat"
#endif
#include VersionInclude

[Setup]
; Stable identity: never change this GUID between releases.
AppId={{A818BCA9-5302-489C-AFEF-B0D01D2BB506}
AppName=SelvamPOS
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}.0
DefaultDirName={sd}\SelvamPOS
DefaultGroupName=SelvamPOS
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#ReleaseDir}
OutputBaseFilename=SelvamPOS-Setup-{#MyAppVersion}
SetupIconFile={#AppSource}\_internal\assets\ico\selvampos.ico
UninstallDisplayIcon={app}\app\SelvamPOS.exe
UninstallFilesDir={app}\app
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Dirs]
; Only mutable data directories grant write access to standard Windows users.
Name: "{app}\db"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\runtime_data"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\runtime_data\json"; Flags: uninsneveruninstall
Name: "{app}\runtime_data\ads"; Flags: uninsneveruninstall
Name: "{app}\live_logs"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\backups"; Permissions: users-modify; Flags: uninsneveruninstall

[Files]
Source: "{#AppSource}\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#GuideSource}"; DestDir: "{app}"; Flags: ignoreversion
; Seed only missing files. Preserve client data during reinstall AND uninstall.
Source: "{#SeedSource}\db\{#DatabaseFilename}"; DestDir: "{app}\db"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "{#SeedSource}\runtime_data\*"; DestDir: "{app}\runtime_data"; Excludes: ".gitkeep"; Flags: onlyifdoesntexist uninsneveruninstall recursesubdirs createallsubdirs skipifsourcedoesntexist

[Icons]
Name: "{autoprograms}\SelvamPOS"; Filename: "{app}\app\SelvamPOS.exe"; WorkingDir: "{app}\app"
Name: "{autodesktop}\SelvamPOS"; Filename: "{app}\app\SelvamPOS.exe"; WorkingDir: "{app}\app"; Tasks: desktopicon

[Run]
Filename: "{app}\app\SelvamPOS.exe"; Description: "Launch SelvamPOS"; Flags: nowait postinstall skipifsilent unchecked
