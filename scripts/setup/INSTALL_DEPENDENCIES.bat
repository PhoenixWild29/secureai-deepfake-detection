@echo off
echo ========================================
echo SecureAI DeepFake Detection
echo Installing Dependencies...
echo ========================================
echo.
echo This will take 5-10 minutes...
echo.

REM Try different Python commands
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Using python command...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    goto :success
)

where python3 >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Using python3 command...
    python3 -m pip install --upgrade pip
    python3 -m pip install -r requirements.txt
    goto :success
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Using py command...
    py -m pip install --upgrade pip
    py -m pip install -r requirements.txt
    goto :success
)

echo ERROR: Python not found!
echo.
echo Please install Python from https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during installation
echo.
pause
goto :end

:success
echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Double-click START_WEB_INTERFACE.bat
echo 2. Open browser to http://localhost:5000
echo 3. Upload a video to test
echo.
pause

:end


