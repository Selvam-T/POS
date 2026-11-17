@echo off
setlocal
if /I "%~1"=="--help" goto help
if /I "%~1"=="-h" goto help

echo [1/2] Building production executable...
call "%~dp0build_exe.bat"
set "RELEASE_EXIT_CODE=%errorlevel%"
if not "%RELEASE_EXIT_CODE%"=="0" (
  echo Release stopped: executable build failed. Installer build was skipped.
  exit /b %RELEASE_EXIT_CODE%
)

echo [2/2] Building installer...
call "%~dp0build_installer.bat" %*
set "RELEASE_EXIT_CODE=%errorlevel%"
if not "%RELEASE_EXIT_CODE%"=="0" (
  echo Release stopped: installer build failed.
  exit /b %RELEASE_EXIT_CODE%
)

echo Release complete. See the installer path printed above.
exit /b 0

:help
echo Usage: build_release.bat [--iscc PATH]
echo Builds the production executable, then its installer. Stops on any failure.
echo Optional arguments are forwarded only to build_installer.bat.
echo See Deployment\README.md for new-machine setup and configuration.
exit /b 0
