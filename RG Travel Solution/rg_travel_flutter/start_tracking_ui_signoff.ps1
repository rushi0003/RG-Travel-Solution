param(
    [string]$SessionName = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($SessionName)) {
    $SessionName = Get-Date -Format "yyyyMMdd_HHmmss"
}

$signoffDir = Join-Path $root "signoff\$SessionName"
$screenshotsDir = Join-Path $signoffDir "screenshots"

New-Item -ItemType Directory -Force -Path $screenshotsDir | Out-Null
Copy-Item -Path (Join-Path $root "TRACKING_UI_SIGNOFF.md") -Destination (Join-Path $signoffDir "TRACKING_UI_SIGNOFF.md") -Force

Write-Host "UI sign-off workspace prepared:" -ForegroundColor Green
Write-Host $signoffDir
Write-Host ""
Write-Host "Put screenshots in:"
Write-Host $screenshotsDir
