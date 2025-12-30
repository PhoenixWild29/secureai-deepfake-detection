@echo off
REM SecureAI Guardian - Start Servers Script
REM This script helps you start both backend and frontend servers

echo ========================================
echo SecureAI Guardian - Server Startup
echo ========================================
echo.

echo [1/2] Starting Backend Server...
echo.
echo Opening new window for backend server...
echo Backend will run on: http://localhost:5000
echo.

REM Use py launcher (works on Windows)
REM Try virtual environment first, then py launcher
if exist "%~dp0..\.venv\Scripts\python.exe" (
    start "SecureAI Backend" cmd /k "cd /d "%~dp0.." && .venv\Scripts\python.exe api.py"
) else if exist "%~dp0..\venv\Scripts\python.exe" (
    start "SecureAI Backend" cmd /k "cd /d "%~dp0.." && venv\Scripts\python.exe api.py"
) else (
    REM Use py launcher (Windows Python launcher)
    start "SecureAI Backend" cmd /k "cd /d "%~dp0.." && py api.py"
)

timeout /t 3 /nobreak >nul

echo.
echo [2/2] Starting Frontend Server...
echo.
echo Opening new window for frontend server...
echo Frontend will run on: http://localhost:3000
echo.

start "SecureAI Frontend" cmd /k "cd /d "%~dp0" && npm run dev"

echo.
echo ========================================
echo Both servers are starting!
echo ========================================
echo.
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:3000
echo.
echo Press any key to close this window...
echo (Servers will continue running in their own windows)
pause >nul

