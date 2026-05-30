param(
    [string]$BaseUrl = "http://127.0.0.1:5000",
    [switch]$CheckSocket
)

$ErrorActionPreference = "Stop"

$flutterDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $flutterDir
$backendDir = Join-Path $repoRoot "rg_travel_backend"
$verifierPath = Join-Path $backendDir "tools\verify_live_tracking_e2e.py"

if (-not (Test-Path $backendDir)) {
    Write-Error "Backend directory not found: $backendDir"
}

if (-not (Test-Path $verifierPath)) {
    Write-Error "Verifier script not found: $verifierPath"
}

Write-Host "=== Live Tracking Smoke Check ===" -ForegroundColor Cyan
Write-Host "Backend Dir : $backendDir"
Write-Host "Base URL    : $BaseUrl"
Write-Host "Socket Check: $($CheckSocket.IsPresent)"
Write-Host ""

Push-Location $backendDir
try {
    $args = @("tools/verify_live_tracking_e2e.py", "--base-url", $BaseUrl)
    if ($CheckSocket) {
        $args += "--check-socket"
    }

    Write-Host "Running: python $($args -join ' ')" -ForegroundColor Yellow
    & python @args
    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "Smoke check FAILED (exit code: $exitCode)" -ForegroundColor Red
    exit $exitCode
}

Write-Host ""
Write-Host "Smoke check PASSED." -ForegroundColor Green
exit 0
