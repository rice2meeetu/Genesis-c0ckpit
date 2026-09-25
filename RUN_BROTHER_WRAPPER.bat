@echo off
setlocal
cd /d "%~dp0"
set "QT_QUICK_CONTROLS_STYLE=Basic"

if exist "%~dp0GENESIS-Brother-Image-Wrapper.exe" (
  start "" "%~dp0GENESIS-Brother-Image-Wrapper.exe"
  exit /b 0
)

if exist "%~dp0dist\GENESIS-Brother-Image-Wrapper\GENESIS-Brother-Image-Wrapper.exe" (
  start "" "%~dp0dist\GENESIS-Brother-Image-Wrapper\GENESIS-Brother-Image-Wrapper.exe"
  exit /b 0
)

if exist "%~dp0.venv-brother\Scripts\python.exe" (
  "%~dp0.venv-brother\Scripts\python.exe" "%~dp0qt_cockpit_brother_windows.py"
  exit /b %errorlevel%
)

echo GENESIS Brother wrapper has not been built yet.
echo Run BUILD_BROTHER_WRAPPER_WINDOWS.bat first.
pause
exit /b 1
