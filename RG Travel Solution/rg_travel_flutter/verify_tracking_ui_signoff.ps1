param(
    [string]$SessionName = "step23_manual_signoff"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$sessionDir = Join-Path $root "signoff\$SessionName"
$checklistPath = Join-Path $sessionDir "TRACKING_UI_SIGNOFF.md"
$screensDir = Join-Path $sessionDir "screenshots"

if (-not (Test-Path $checklistPath)) {
    Write-Error "Checklist not found: $checklistPath"
}

if (-not (Test-Path $screensDir)) {
    Write-Error "Screenshots directory not found: $screensDir"
}

$requiredScreenshots = @(
    "driver_health_waiting.png",
    "driver_health_synced.png",
    "driver_health_offline.png",
    "admin_live_map_ok.png",
    "admin_live_map_stale.png",
    "employee_live_map_ok.png",
    "employee_live_map_stale.png"
)

$missing = @()
foreach ($name in $requiredScreenshots) {
    $p = Join-Path $screensDir $name
    if (-not (Test-Path $p)) {
        $missing += $name
    }
}

$checklist = Get-Content -Raw $checklistPath
$hasPassChecked = $checklist -match "- \[x\] PASS \(ready for rollout\)"
$hasFailChecked = $checklist -match "- \[x\] FAIL \(fixes required\)"

Write-Host "=== UI Sign-off Audit ===" -ForegroundColor Cyan
Write-Host "Session: $SessionName"
Write-Host "Checklist: $checklistPath"
Write-Host "Screenshots dir: $screensDir"
Write-Host ""

if ($missing.Count -eq 0) {
    Write-Host "Evidence: PASS (all required screenshots present)" -ForegroundColor Green
} else {
    Write-Host "Evidence: FAIL (missing screenshots)" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host " - $_" }
}

if ($hasPassChecked -and -not $hasFailChecked) {
    Write-Host "Decision checkbox: PASS selected" -ForegroundColor Green
} elseif ($hasFailChecked -and -not $hasPassChecked) {
    Write-Host "Decision checkbox: FAIL selected" -ForegroundColor Yellow
} else {
    Write-Host "Decision checkbox: NOT FINALIZED" -ForegroundColor Yellow
}

if ($missing.Count -eq 0 -and $hasPassChecked -and -not $hasFailChecked) {
    Write-Host ""
    Write-Host "Overall: PASS (UI sign-off complete)" -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "Overall: PENDING/FAIL (complete checklist + evidence)" -ForegroundColor Red
exit 1
