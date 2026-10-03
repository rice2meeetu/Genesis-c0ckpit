$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$venvDir = Join-Path $PSScriptRoot '.venv-win'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'

if (-not (Test-Path $venvPython)) {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        & py -3 -m venv $venvDir
    } else {
        $python = Get-Command python -ErrorAction SilentlyContinue
        if (-not $python) {
            throw 'Python 3 was not found. Install Python 3.11+ and run this launcher again.'
        }
        & python -m venv $venvDir
    }
}

& $venvPython -m pip install --disable-pip-version-check -r (Join-Path $PSScriptRoot 'requirements-windows.txt')

$runtimeDir = Join-Path $env:TEMP 'GENESIS-runtime'
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
$env:XDG_RUNTIME_DIR = $runtimeDir

if (-not $env:GENESIS_BACKEND_MODE) {
    $env:GENESIS_BACKEND_MODE = 'RUNPOD'
}

& $venvPython (Join-Path $PSScriptRoot 'qt_cockpit_linux_premium.py') --page home @args
exit $LASTEXITCODE
