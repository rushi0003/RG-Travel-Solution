# RG Travel Solution - Backend Quick Start (PowerShell)
# Usage: .\start-backend.ps1

$ErrorActionPreference = "Continue"

# Color functions
function Write-Header { Write-Host "========================================" -ForegroundColor Cyan; Write-Host $args[0] -ForegroundColor Cyan; Write-Host "========================================" -ForegroundColor Cyan }
function Write-Success { Write-Host "✓ $($args -join ' ')" -ForegroundColor Green }
function Write-Error_ { Write-Host "✗ $($args -join ' ')" -ForegroundColor Red }
function Write-Warning_ { Write-Host "⚠ $($args -join ' ')" -ForegroundColor Yellow }
function Write-Info { Write-Host "ℹ $($args -join ' ')" -ForegroundColor Blue }

# Title
Clear-Host
Write-Host ""
Write-Header "RG Travel Solution - Backend Setup"
Write-Host ""

# Check Python
Write-Host "Checking Python installation..."
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error_ "Python not found!"
    Write-Info "Please install Python from https://www.python.org/"
    Read-Host "Press Enter to exit"
    exit 1
}
$version = python --version 2>&1
Write-Success "Python found: $version"

# Check if .env exists
Write-Host ""
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file from template..."
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Success ".env created"
    } else {
        Write-Warning_ ".env.example not found"
    }
} else {
    Write-Info ".env already exists"
}

# Change to backend directory
Write-Host ""
$backendPath = Join-Path (Get-Location) "rg_travel_backend"
if (-not (Test-Path $backendPath)) {
    Write-Error_ "rg_travel_backend directory not found"
    Read-Host "Press Enter to exit"
    exit 1
}

Set-Location $backendPath
Write-Success "Changed to: rg_travel_backend"

# Create virtual environment if needed
Write-Host ""
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error_ "Failed to create virtual environment"
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Success "Virtual environment created"
}

# Activate virtual environment
Write-Host ""
Write-Host "Activating virtual environment..."
& ".\venv\Scripts\Activate.ps1"
Write-Success "Virtual environment activated"

# Install dependencies
Write-Host ""
Write-Host "Installing dependencies..."
pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error_ "Failed to install dependencies"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Success "Dependencies installed"

# Run verification
Write-Host ""
Write-Host "Running setup verification..."
python verify_setup.py
if ($LASTEXITCODE -ne 0) {
    Write-Warning_ "Some checks failed - this may be normal"
}

# Start application
Write-Host ""
Write-Header "Starting RG Travel Backend..."
Write-Host ""
Write-Info "Backend will be available at:"
Write-Host "  http://localhost:5000" -ForegroundColor Cyan
Write-Host ""
Write-Info "API Documentation:"
Write-Host "  http://localhost:5000/api/health" -ForegroundColor Cyan
Write-Host ""
Write-Warning_ "Press Ctrl+C to stop the server"
Write-Host ""

python app.py

Write-Host ""
Write-Error_ "Backend stopped"
Read-Host "Press Enter to exit"
