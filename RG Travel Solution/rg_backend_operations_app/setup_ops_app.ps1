$ErrorActionPreference = 'Stop'

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $appDir

Write-Host "Initializing RG Backend Operations App..." -ForegroundColor Cyan
Write-Host "Working directory: $appDir" -ForegroundColor DarkGray

& "C:\flutter\bin\flutter.bat" create . --platforms=android,web,windows --no-pub

Write-Host ""
Write-Host "Platform folders generated." -ForegroundColor Green
Write-Host "Next commands:" -ForegroundColor Cyan
Write-Host "  flutter pub get"
Write-Host "  flutter run -d chrome"
