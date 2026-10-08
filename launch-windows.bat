@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON=.venv\Scripts\python.exe"
if exist "%PYTHON%" goto :run

echo [GENESIS] Creating Windows environment...
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3.12 -m venv .venv 2>nul || py -3 -m venv .venv
) else (
    python -m venv .venv
)
if errorlevel 1 goto :failed

echo [GENESIS] Installing Windows dependencies...
"%PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto :failed
"%PYTHON%" -m pip install -r windows\requirements-windows.txt
if errorlevel 1 goto :failed

:run
echo [GENESIS] Starting GENESIS c0ckpit for Windows...
"%PYTHON%" qt_cockpit_windows.py %*
if errorlevel 1 goto :failed
exit /b 0

:failed
echo.
echo GENESIS could not start. Review the message above.
pause
exit /b 1
