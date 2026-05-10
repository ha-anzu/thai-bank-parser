param(
  [string]$Python = "python",
  [string]$Output = "offline-bundle"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Bundle = Join-Path $Root $Output
$Wheelhouse = Join-Path $Bundle "wheelhouse"

if (Test-Path $Bundle) {
  Remove-Item -Recurse -Force $Bundle
}
New-Item -ItemType Directory -Force -Path $Wheelhouse | Out-Null

& $Python -m pip download --only-binary=:all: --dest $Wheelhouse -r (Join-Path $Root "requirements.lock.txt")
& $Python -m pip wheel --no-deps --wheel-dir $Wheelhouse $Root

Copy-Item -Force (Join-Path $Root "scripts\install_offline.ps1") (Join-Path $Bundle "install_offline.ps1")
Copy-Item -Force (Join-Path $Root "README.md") (Join-Path $Bundle "README.md")
Copy-Item -Force (Join-Path $Root "requirements.lock.txt") (Join-Path $Bundle "requirements.lock.txt")

Write-Host "Offline bundle ready:" -ForegroundColor Green
Write-Host $Bundle
Write-Host ""
Write-Host "Install on another machine with:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\install_offline.ps1"
