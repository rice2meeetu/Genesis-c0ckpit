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

# PyQt's native Windows Qt Quick Controls style can fail to resolve its
# platform implementation DLL on some Python/Qt wheels. GENESIS supplies its
# own QML appearance, so force the portable Basic control implementation.
$env:QT_QUICK_CONTROLS_STYLE = 'Basic'
$env:QT_QUICK_CONTROLS_FALLBACK_STYLE = 'Basic'

if (-not $env:GENESIS_BACKEND_MODE) {
    $env:GENESIS_BACKEND_MODE = 'RUNPOD'
}

& $venvPython (Join-Path $PSScriptRoot 'qt_cockpit_linux_premium.py') --page home @args
exit $LASTEXITCODE
