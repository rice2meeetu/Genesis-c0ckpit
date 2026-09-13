param(
  [switch]$Package
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$Python = '.\.venv-windows\Scripts\python.exe'
if (-not (Test-Path $Python)) {
  py -3.12 -m venv .venv-windows
}
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements-windows.txt
& $Python -m pip install --no-deps face-recognition==1.3.0
$env:QT_QUICK_CONTROLS_STYLE='Basic'
& $Python -m py_compile qt_cockpit.py main.py
& $Python -m pytest tests -q
if ($Package) {
  & .\.venv-windows\Scripts\pyinstaller.exe --noconfirm --clean --windowed --name GENESIS-c0ckpit --add-data 'genesis\qt_ui;genesis\qt_ui' --add-data 'genesis\assets;genesis\assets' qt_cockpit.py
}
