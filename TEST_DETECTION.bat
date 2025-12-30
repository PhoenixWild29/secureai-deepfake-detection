@echo off
echo ========================================
echo SecureAI DeepFake Detection
echo Quick Test
echo ========================================
echo.

REM Try different Python commands
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python simple_demo.py
    goto :end
)

where python3 >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python3 simple_demo.py
    goto :end
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py simple_demo.py
    goto :end
)

echo ERROR: Python not found!
echo.
echo Please install Python from https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during installation
echo.
pause

:end
pause


