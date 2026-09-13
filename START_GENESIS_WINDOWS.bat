@echo off
setlocal
cd /d "%~dp0"
set QT_QUICK_CONTROLS_STYLE=Basic
set PYTHONUTF8=1
if not exist ".venv-windows\Scripts\python.exe" (
  py -3.12 -m venv .venv-windows
  .venv-windows\Scripts\python.exe -m pip install --upgrade pip
  .venv-windows\Scripts\python.exe -m pip install -r requirements-windows.txt
)
.venv-windows\Scripts\python.exe qt_cockpit.py
endlocal
