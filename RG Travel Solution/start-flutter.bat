@echo off
REM RG Travel Solution - Flutter Quick Start Script (Windows)

setlocal enabledelayedexpansion

cls
echo.
echo ========================================
echo RG Travel Solution - Flutter Setup
echo ========================================
echo.

REM Check Flutter
echo Checking Flutter installation...
flutter --version >nul 2>&1
if errorlevel 1 (
    echo Error: Flutter not found!
    echo Please install Flutter from https://flutter.dev
    pause
    exit /b 1
)
echo [OK] Flutter found

REM Change to Flutter directory
cd /d "rg_travel_flutter"
if errorlevel 1 (
    echo Error: Could not change to rg_travel_flutter directory
    pause
    exit /b 1
)

REM Get dependencies
echo.
echo Getting Flutter dependencies...
flutter pub get
if errorlevel 1 (
    echo Error: Failed to get dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed

REM Show available devices
echo.
echo Available devices:
flutter devices
echo.

REM Check if device is available
flutter devices | find /i "no device" >nul
if not errorlevel 1 (
    echo WARNING: No devices found!
    echo Please:
    echo   - Start an Android emulator or iOS simulator, OR
    echo   - Connect a physical device
    echo.
)

REM Run app
echo.
echo ========================================
echo Starting Flutter app...
echo ========================================
echo.
echo Backend should be running on:
echo   http://localhost:5000
echo.

flutter run

REM If we get here, app exited
echo.
echo Flutter app stopped
pause
