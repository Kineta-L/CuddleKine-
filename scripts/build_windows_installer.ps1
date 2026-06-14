param(
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$TauriResources = Join-Path $Root "desktop\src-tauri\resources"
$BackendResourceDir = Join-Path $TauriResources "backend"
$WorkflowResourceDir = Join-Path $TauriResources "comfyui\workflows"

& (Join-Path $PSScriptRoot "build_backend.ps1") -Python $Python

New-Item -ItemType Directory -Force $BackendResourceDir | Out-Null
New-Item -ItemType Directory -Force $WorkflowResourceDir | Out-Null

Copy-Item `
  -LiteralPath (Join-Path $Root "release\backend\cuddlekine-backend.exe") `
  -Destination (Join-Path $BackendResourceDir "cuddlekine-backend.exe") `
  -Force

Copy-Item `
  -LiteralPath (Join-Path $Root "comfyui\workflows\*") `
  -Destination $WorkflowResourceDir `
  -Recurse `
  -Force

Push-Location (Join-Path $Root "desktop")
try {
  npm.cmd install
  npm.cmd run tauri build
}
finally {
  Pop-Location
}

Write-Host "Installer artifacts are under:"
Write-Host (Join-Path $Root "desktop\src-tauri\target\release\bundle")
