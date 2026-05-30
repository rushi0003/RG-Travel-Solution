param(
    [string]$BaseUrl = "http://127.0.0.1:5000",
    [switch]$CheckSocket
)

$ErrorActionPreference = "Stop"

function Run-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "FAILED: $Name" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host "PASS: $Name" -ForegroundColor Green
}

$flutterDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Push-Location $flutterDir
try {
    Run-Step -Name "Backend E2E Smoke" -Action {
        $args = @("-ExecutionPolicy", "Bypass", "-File", ".\run_live_tracking_smoke.ps1", "-BaseUrl", $BaseUrl)
        if ($CheckSocket) {
            $args += "-CheckSocket"
        }
        & powershell @args
    }

    Run-Step -Name "Tracking Analyze (errors/warnings gate)" -Action {
        $analyzeOutput = dart analyze `
            lib/screens/admin/live_tracking_screen.dart `
            lib/screens/tracking/live_tracking_screen.dart `
            lib/screens/employee/driver_tracking_screen.dart `
            lib/screens/employee/live_tracking_view.dart `
            lib/widgets/tracking/osm_live_map.dart `
            lib/widgets/tracking/driver_tracking_health_view.dart `
            lib/services/driver_service.dart `
            lib/services/admin_service.dart
        $matches = $analyzeOutput | Select-String "error -|warning -"
        if ($matches) {
            $matches | ForEach-Object { Write-Host $_ }
            exit 1
        }
    }

    Run-Step -Name "Tracking Tests" -Action {
        & flutter test `
            test/widgets/tracking/driver_tracking_health_view_test.dart `
            test/services/admin_service_test.dart
    }

    Write-Host ""
    Write-Host "Tracking release gate PASSED." -ForegroundColor Green
    exit 0
}
finally {
    Pop-Location
}
