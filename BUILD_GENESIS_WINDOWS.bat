@echo off
setlocal
cd /d "%~dp0"
echo === GENESIS WINDOWS BUILD ===
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install PyQt6 pillow imagehash pytest safetensors
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m pytest tests\test_model_compatibility.py tests\test_qt_generation_profiles.py tests\test_generation_pipeline.py -q
if errorlevel 1 goto :fail
echo.
echo GENESIS WINDOWS CORE BUILD: PASS
exit /b 0
:fail
echo.
echo GENESIS WINDOWS CORE BUILD: FAILED
pause
exit /b 1
