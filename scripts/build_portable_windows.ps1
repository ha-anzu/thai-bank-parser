param(
  [string]$PythonHome = "",
  [string]$Output = "portable-windows"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Portable = Join-Path $Root $Output
$Runtime = Join-Path $Portable "python"
$Bundle = Join-Path $Portable "offline-bundle"

if (-not $PythonHome) {
  $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
  if (-not $pythonCommand) {
    throw "PythonHome was not provided and python was not found on PATH."
  }
  $PythonHome = Split-Path -Parent (Split-Path -Parent $pythonCommand.Source)
}

if (-not (Test-Path (Join-Path $PythonHome "python.exe"))) {
  throw "PythonHome must point to a Python runtime folder containing python.exe: $PythonHome"
}

if (Test-Path $Portable) {
  Remove-Item -Recurse -Force $Portable
}
New-Item -ItemType Directory -Force -Path $Portable | Out-Null

Copy-Item -Recurse -Force $PythonHome $Runtime

powershell -ExecutionPolicy Bypass -File (Join-Path $Root "scripts\build_offline_bundle.ps1") `
  -Python (Join-Path $Runtime "python.exe") `
  -Output (Join-Path $Output "offline-bundle")

$Launcher = @'
param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root "python\python.exe"
& $Python -m thai_bank_parser.cli @Args
'@
[System.IO.File]::WriteAllText((Join-Path $Portable "tbp.ps1"), $Launcher, [System.Text.UTF8Encoding]::new($false))

$Install = @'
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root "python\python.exe"
$Installer = Join-Path $Root "offline-bundle\install_offline.ps1"
powershell -ExecutionPolicy Bypass -File $Installer -Python $Python
Write-Host ""
Write-Host "Portable TBP is ready." -ForegroundColor Green
Write-Host "Run:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\tbp.ps1 start"
'@
[System.IO.File]::WriteAllText((Join-Path $Portable "install.ps1"), $Install, [System.Text.UTF8Encoding]::new($false))

Write-Host "Portable Windows folder ready:" -ForegroundColor Green
Write-Host $Portable
Write-Host ""
Write-Host "First run:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\install.ps1"
Write-Host "Then:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\tbp.ps1 start"
