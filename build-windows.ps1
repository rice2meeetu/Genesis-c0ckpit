param(
  [switch]$Package,
  [switch]$PremiumSmoke
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
& $Python -m py_compile qt_cockpit.py qt_cockpit_premium.py main.py
& $Python -m pytest tests -q
if ($PremiumSmoke) {
  $env:QT_QPA_PLATFORM='offscreen'
  $env:QT_QUICK_BACKEND='software'
  $env:QSG_RHI_BACKEND='software'
  & $Python qt_cockpit_premium.py --page home --width 1400 --height 900 --smoke
  if ($LASTEXITCODE -ne 0) { throw "Premium QML smoke exited with code $LASTEXITCODE." }
  & $Python qt_cockpit_premium.py --page poses --width 1400 --height 900 --smoke
  if ($LASTEXITCODE -ne 0) { throw "Premium pose smoke exited with code $LASTEXITCODE." }
  & $Python qt_cockpit_premium.py --page create --width 1400 --height 900 --smoke
  if ($LASTEXITCODE -ne 0) { throw "Premium create smoke exited with code $LASTEXITCODE." }
  & $Python qt_cockpit_premium.py --tool-smoke
  if ($LASTEXITCODE -ne 0) { throw "Premium tool-host smoke exited with code $LASTEXITCODE." }
  Write-Host 'GENESIS PREMIUM SOURCE SMOKE: PASS'
}
if ($Package) {
  & .\.venv-windows\Scripts\pyinstaller.exe --noconfirm --clean --windowed --name GENESIS-c0ckpit --add-data 'genesis\qt_ui;genesis\qt_ui' --add-data 'genesis\assets;genesis\assets' --add-data 'genesis\reference;genesis\reference' qt_cockpit_premium.py
  $Exe = '.\dist\GENESIS-c0ckpit\GENESIS-c0ckpit.exe'
  if (-not (Test-Path $Exe)) { throw 'Packaged GENESIS executable was not created.' }
  if ($PremiumSmoke) {
    $premium = Start-Process -FilePath $Exe -ArgumentList '--page','home','--width','1400','--height','900','--smoke' -Wait -PassThru
    if ($premium.ExitCode -ne 0) { throw "Packaged GENESIS premium smoke exited with code $($premium.ExitCode)." }
    $tools = Start-Process -FilePath $Exe -ArgumentList '--tool-smoke' -Wait -PassThru
    if ($tools.ExitCode -ne 0) { throw "Packaged GENESIS tool-host smoke exited with code $($tools.ExitCode)." }
    Write-Host 'GENESIS PREMIUM PACKAGED SMOKE: PASS'
  }
}
