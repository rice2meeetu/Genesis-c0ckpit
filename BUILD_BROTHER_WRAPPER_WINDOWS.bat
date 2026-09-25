@echo off
setlocal
cd /d "%~dp0"
echo === GENESIS BROTHER STANDALONE WINDOWS BUILD ===

where py >nul 2>nul || (
  echo Python Launcher was not found. Install Python 3.12 x64, then rerun this file.
  pause
  exit /b 1
)

set "PY=.venv-brother\Scripts\python.exe"
if not exist "%PY%" py -3.12 -m venv .venv-brother
if errorlevel 1 goto :fail

"%PY%" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%PY%" -m pip install -r requirements-brother-windows.txt
if errorlevel 1 goto :fail

"%PY%" -m py_compile qt_cockpit.py qt_cockpit_brother_windows.py genesis\backend_bridge.py genesis\backend_routing.py genesis\model_registry.py
if errorlevel 1 goto :fail

"%PY%" -m pytest -q tests\test_backend_routing.py tests\test_generation_pipeline.py tests\test_qt_generation_profiles.py tests\test_brother_windows_wrapper.py
if errorlevel 1 goto :fail

set "QT_QPA_PLATFORM=offscreen"
set "QT_QUICK_BACKEND=software"
set "QSG_RHI_BACKEND=software"
set "QT_QUICK_CONTROLS_STYLE=Basic"
"%PY%" qt_cockpit_brother_windows.py --page create --width 1400 --height 900 --smoke
if errorlevel 1 goto :fail

"%PY%" -m PyInstaller --noconfirm --clean --windowed ^
  --name GENESIS-Brother-Image-Wrapper ^
  --add-data "genesis\qt_ui;genesis\qt_ui" ^
  --add-data "genesis\assets;genesis\assets" ^
  --add-data "genesis\reference;genesis\reference" ^
  qt_cockpit_brother_windows.py
if errorlevel 1 goto :fail

copy /y RUN_BROTHER_WRAPPER.bat "dist\GENESIS-Brother-Image-Wrapper\RUN_BROTHER_WRAPPER.bat" >nul
copy /y README_BROTHER_WINDOWS_WRAPPER.md "dist\GENESIS-Brother-Image-Wrapper\README_BROTHER_WINDOWS_WRAPPER.md" >nul

"dist\GENESIS-Brother-Image-Wrapper\GENESIS-Brother-Image-Wrapper.exe" --smoke
if errorlevel 1 goto :fail

powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path 'GENESIS-Brother-Image-Wrapper-Windows.zip') { Remove-Item 'GENESIS-Brother-Image-Wrapper-Windows.zip' -Force }; Compress-Archive -Path 'dist\GENESIS-Brother-Image-Wrapper\*' -DestinationPath 'GENESIS-Brother-Image-Wrapper-Windows.zip' -CompressionLevel Optimal"
if errorlevel 1 goto :fail

echo.
echo BUILD PASS
echo Package: %CD%\GENESIS-Brother-Image-Wrapper-Windows.zip
exit /b 0

:fail
echo.
echo BUILD FAILED. Read the error above; no existing GENESIS installation was changed.
pause
exit /b 1
