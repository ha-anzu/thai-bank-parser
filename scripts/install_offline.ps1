param(
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$Bundle = Split-Path -Parent $MyInvocation.MyCommand.Path
$Wheelhouse = Join-Path $Bundle "wheelhouse"

if (-not (Test-Path $Wheelhouse)) {
  throw "Missing wheelhouse folder: $Wheelhouse"
}

& $Python -m pip install --no-index --find-links $Wheelhouse thai-bank-parser

Write-Host "Thai Bank Parser installed offline." -ForegroundColor Green
Write-Host "Try:"
Write-Host "  tbp start"
