@echo off
setlocal
cd /d "%~dp0"
echo === GENESIS WINDOWS BUILD ===
set "PY=.venv-windows\Scripts\python.exe"
if not exist "%PY%" py -3.12 -m venv .venv-windows
"%PY%" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%PY%" -m pip install -r requirements-windows.txt
if errorlevel 1 goto :fail
"%PY%" -m pip install --no-deps face-recognition==1.3.0
if errorlevel 1 goto :fail
"%PY%" -m py_compile qt_cockpit.py main.py
if errorlevel 1 goto :fail
"%PY%" -m pytest tests -q
if errorlevel 1 goto :fail
echo.
echo GENESIS WINDOWS CORE BUILD: PASS
exit /b 0
:fail
echo.
echo GENESIS WINDOWS CORE BUILD: FAILED
pause
exit /b 1
