@echo off
setlocal
cd /d "%~dp0"
set QT_QUICK_CONTROLS_STYLE=Basic
set PYTHONUTF8=1
set "PY=.venv-windows\Scripts\python.exe"
if not exist "%PY%" (
  py -3.12 -m venv .venv-windows
  "%PY%" -m pip install --upgrade pip
  "%PY%" -m pip install -r requirements-windows.txt
  "%PY%" -m pip install --no-deps face-recognition==1.3.0
)
"%PY%" -c "import face_recognition" >nul 2>&1
if errorlevel 1 (
  "%PY%" -m pip install "setuptools<82" -r requirements-windows.txt
  "%PY%" -m pip install --no-deps face-recognition==1.3.0
)
"%PY%" qt_cockpit.py
endlocal
