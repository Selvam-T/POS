@echo off
setlocal
set "BUILD_PYTHON=%~dp0..\.venv\Scripts\python.exe"
if not exist "%BUILD_PYTHON%" (
  echo ERROR: Project .venv not found. See Deployment\README.md.
  exit /b 1
)
"%BUILD_PYTHON%" -B "%~dp0scripts\build_installer.py" %*
exit /b %errorlevel%
