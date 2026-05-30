@echo off
REM RG Travel Solution - Backend Quick Start Script (Windows)
REM This script sets up and runs the backend

setlocal enabledelayedexpansion

REM Color setup (using findstr trick)
for /F %%a in ('copy /Z "%~f0" nul') do set "BS=%%a"

set RED=[91m
set GREEN=[92m
set YELLOW=[93m
set BLUE=[94m
set RESET=[0m

REM Title
cls
echo.
echo %BLUE%========================================%RESET%
echo %BLUE%RG Travel Solution - Backend Setup%RESET%
echo %BLUE%========================================%RESET%
echo.

REM Check Python
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%Error: Python not found!%RESET%
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)
echo %GREEN%✓ Python found%RESET%

REM Check if .env exists
if not exist ".env" (
    echo.
    echo Creating .env file from template...
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo %GREEN%✓ .env created%RESET%
    ) else (
        echo %YELLOW%Warning: .env.example not found%RESET%
    )
)

REM Enter backend directory
cd /d "rg_travel_backend"
if errorlevel 1 (
    echo %RED%Error: Could not change to rg_travel_backend directory%RESET%
    pause
    exit /b 1
)

REM Check virtual environment
if not exist "venv" (
    echo.
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo %RED%Error: Failed to create virtual environment%RESET%
        pause
        exit /b 1
    )
    echo %GREEN%✓ Virtual environment created%RESET%
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo %RED%Error: Failed to activate virtual environment%RESET%
    pause
    exit /b 1
)
echo %GREEN%✓ Virtual environment activated%RESET%

REM Install dependencies
echo.
echo Installing dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo %RED%Error: Failed to install dependencies%RESET%
    pause
    exit /b 1
)
echo %GREEN%✓ Dependencies installed%RESET%

REM Run verification
echo.
echo Running setup verification...
python verify_setup.py
if errorlevel 1 (
    echo %YELLOW%Warning: Some checks failed%RESET%
)

REM Start application
echo.
echo %GREEN%========================================%RESET%
echo %GREEN%Starting RG Travel Backend...%RESET%
echo %GREEN%========================================%RESET%
echo.
echo %BLUE%Backend will be available at:%RESET%
echo   %BLUE%http://localhost:5000%RESET%
echo.
echo %BLUE%API Documentation:%RESET%
echo   %BLUE%http://localhost:5000/api/health%RESET%
echo.
echo %YELLOW%Press Ctrl+C to stop the server%RESET%
echo.

python app.py

REM If we get here, app exited
echo.
echo %RED%Backend stopped%RESET%
pause
