$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

if (-not (Test-Path "config.json")) {
    Copy-Item "config.example.json" "config.json"
    Write-Host "[setup] Created config.json from config.example.json"
}

$VenvPython = Join-Path $RootDir "venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -m venv venv
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        python -m venv venv
    }
    else {
        throw "Python launcher not found. Install Python 3.12+ or make `py` available."
    }

    Write-Host "[setup] Created virtual environment at venv\"
}

& $VenvPython -m pip install --disable-pip-version-check -r requirements.txt

Write-Host "[setup] Running local preflight..."
& $VenvPython scripts\preflight_local.py

Write-Host ""
Write-Host "[setup] Done."
Write-Host "[setup] Start app with: .\venv\Scripts\Activate.ps1"
Write-Host "[setup] Then run: python src\main.py"
