@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo       GENESIS c0ckpit PREMIUM WINDOWS VERIFICATION
echo ============================================================
echo.

echo [1/4] Sync/build Python environment, compile, and run tests...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-windows.ps1" -PremiumSmoke
if errorlevel 1 goto :fail

echo.
echo [2/4] Verify premium launcher files...
if not exist "qt_cockpit_premium.py" goto :fail
if not exist "genesis\qt_ui\MainPremium.qml" goto :fail
if not exist "premium-home.png" goto :fail

echo [3/4] Verify premium UI contract test directly...
".venv-windows\Scripts\python.exe" -m pytest tests\test_premium_ui_contract.py -q
if errorlevel 1 goto :fail

echo [4/4] Verification complete.
echo.
echo ============================================================
echo GENESIS PREMIUM WINDOWS: PASS
echo Screenshot: %CD%\premium-home.png
echo Launcher:   %CD%\START_GENESIS_PREMIUM_WINDOWS.bat
echo ============================================================
exit /b 0

:fail
echo.
echo ============================================================
echo GENESIS PREMIUM WINDOWS: FAILED
echo Nothing was promoted over the current known-good launcher.
echo ============================================================
pause
exit /b 1
