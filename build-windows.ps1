param(
  [switch]$Package
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv-windows\Scripts\python.exe')) {
  py -3.12 -m venv .venv-windows
}
& .\.venv-windows\Scripts\python.exe -m pip install --upgrade pip
& .\.venv-windows\Scripts\python.exe -m pip install -r requirements-windows.txt
$env:QT_QUICK_CONTROLS_STYLE='Basic'
& .\.venv-windows\Scripts\python.exe -m py_compile qt_cockpit.py main.py
& .\.venv-windows\Scripts\python.exe -m pytest tests\test_asset_inventory.py tests\test_job_queue.py tests\test_visual_browser.py -q
if ($Package) {
  & .\.venv-windows\Scripts\pyinstaller.exe --noconfirm --clean --windowed --name GENESIS-c0ckpit --add-data 'genesis\qt_ui;genesis\qt_ui' --add-data 'genesis\assets;genesis\assets' qt_cockpit.py
}
