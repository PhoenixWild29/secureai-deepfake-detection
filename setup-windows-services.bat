@echo off
REM SecureAI Guardian - Windows Service Setup (Batch Wrapper)
REM This script runs the PowerShell service setup script

echo ========================================
echo SecureAI Guardian - Windows Service Setup
echo ========================================
echo.

REM Check for PowerShell
powershell -Command "Get-Host" >nul 2>&1
if errorlevel 1 (
    echo ERROR: PowerShell is not available!
    echo Please install PowerShell or run setup-windows-services.ps1 directly
    pause
    exit /b 1
)

echo Running PowerShell service setup script...
echo.
echo NOTE: This script must be run as Administrator!
echo.
pause

REM Run PowerShell script with execution policy bypass
powershell -ExecutionPolicy Bypass -File "%~dp0setup-windows-services.ps1"

if errorlevel 1 (
    echo.
    echo Setup failed! Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo Setup complete!
pause

