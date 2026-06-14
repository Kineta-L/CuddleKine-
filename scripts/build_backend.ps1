param(
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendDir = Join-Path $Root "backend"
$ReleaseBackendDir = Join-Path $Root "release\backend"

New-Item -ItemType Directory -Force $ReleaseBackendDir | Out-Null

Push-Location $Root
try {
  & $Python -m pip install --upgrade pip
  & $Python -m pip install -r "backend\requirements.txt" pyinstaller

  & $Python -m PyInstaller `
    --clean `
    --noconfirm `
    --name "cuddlekine-backend" `
    --onefile `
    --paths $BackendDir `
    --collect-submodules "app" `
    --distpath $ReleaseBackendDir `
    --workpath (Join-Path $Root "release\pyinstaller-build") `
    --specpath (Join-Path $Root "release\pyinstaller-spec") `
    "backend\run.py"
}
finally {
  Pop-Location
}

Write-Host "Backend executable created:"
Write-Host (Join-Path $ReleaseBackendDir "cuddlekine-backend.exe")
