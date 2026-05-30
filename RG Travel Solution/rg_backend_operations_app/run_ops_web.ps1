$ErrorActionPreference = 'Stop'

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $appDir

if (-not (Test-Path (Join-Path $appDir 'web'))) {
    Write-Error "Web platform not found. Run .\setup_ops_app.ps1 first."
}

& "C:\flutter\bin\flutter.bat" pub get
& "C:\flutter\bin\flutter.bat" run -d chrome
