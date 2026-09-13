@echo off
setlocal
cd /d "%~dp0"
set QT_QUICK_CONTROLS_STYLE=Basic
set PYTHONUTF8=1

if not exist ".venv-windows\Scripts\python.exe" (
  echo GENESIS Windows environment is missing. Building it now...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-windows.ps1"
  if errorlevel 1 goto :fail
)

echo Starting GENESIS c0ckpit Premium...
".venv-windows\Scripts\python.exe" qt_cockpit_premium.py
exit /b %errorlevel%

:fail
echo.
echo GENESIS Premium launch preparation failed.
pause
exit /b 1
