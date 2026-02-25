@echo off
REM Robust server startup script with mobile access verification
echo ========================================
echo SecureAI Guardian - Robust Server Startup
echo ========================================
echo.

REM Get network IP address
echo Detecting network IP address...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set ip=%%a
    set ip=!ip:~1!
    goto :found_ip
)
:found_ip

echo.
echo Network IP detected: %ip%
echo.
echo [1/2] Starting Backend Server...
echo.

REM Start backend
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

REM Start frontend
start "SecureAI Frontend" cmd /k "cd /d "%~dp0" && npm run dev"

timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo Servers Started!
echo ========================================
echo.
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:3000
echo.
echo ========================================
echo MOBILE ACCESS
echo ========================================
echo.
echo Use this URL on your mobile device:
echo   http://%ip%:3000
echo.
echo IMPORTANT: Make sure you see "Network: http://%ip%:3000" 
echo in the frontend server window!
echo.
echo If mobile access doesn't work:
echo   1. Run CHECK_MOBILE_ACCESS.bat to diagnose
echo   2. Run FIX_FIREWALL.bat (as Administrator) if needed
echo.
echo Press any key to close this window...
echo (Servers will continue running in their own windows)
pause >nul

