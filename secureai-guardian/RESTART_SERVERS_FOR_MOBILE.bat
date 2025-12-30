@echo off
REM Restart servers to ensure network access is enabled
echo ========================================
echo Restarting Servers for Mobile Access
echo ========================================
echo.
echo This will restart both servers with network access enabled.
echo.
echo Press Ctrl+C in each server window to stop them first!
echo.
pause

echo.
echo [1/2] Starting Backend Server...
echo.

REM Use py launcher (works on Windows)
if exist "%~dp0..\.venv\Scripts\python.exe" (
    start "SecureAI Backend" cmd /k "cd /d "%~dp0.." && .venv\Scripts\python.exe api.py"
) else if exist "%~dp0..\venv\Scripts\python.exe" (
    start "SecureAI Backend" cmd /k "cd /d "%~dp0.." && venv\Scripts\python.exe api.py"
) else (
    start "SecureAI Backend" cmd /k "cd /d "%~dp0.." && py api.py"
)

timeout /t 3 /nobreak >nul

echo.
echo [2/2] Starting Frontend Server...
echo.

start "SecureAI Frontend" cmd /k "cd /d "%~dp0" && npm run dev"

echo.
echo ========================================
echo Servers are starting!
echo ========================================
echo.
echo Look for the "Network" URL in the frontend window.
echo It should show something like: http://10.0.0.168:3000/
echo.
echo Use that Network URL on your phone!
echo.
pause

