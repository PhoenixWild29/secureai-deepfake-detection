@echo off
REM Diagnostic script to check mobile access configuration
echo ========================================
echo Mobile Access Diagnostic Tool
echo ========================================
echo.

echo [1/5] Checking network IP addresses...
echo.
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set ip=%%a
    set ip=!ip:~1!
    echo   Found IP: !ip!
)
echo.

echo [2/5] Checking if ports are listening...
echo.
netstat -an | findstr ":3000" >nul
if %errorlevel% == 0 (
    echo   [OK] Port 3000 is in use (Frontend)
) else (
    echo   [ERROR] Port 3000 is NOT in use - Frontend server not running!
)
netstat -an | findstr ":5000" >nul
if %errorlevel% == 0 (
    echo   [OK] Port 5000 is in use (Backend)
) else (
    echo   [ERROR] Port 5000 is NOT in use - Backend server not running!
)
echo.

echo [3/5] Checking Vite configuration...
echo.
if exist "vite.config.ts" (
    findstr /i "host.*0.0.0.0" vite.config.ts >nul
    if %errorlevel% == 0 (
        echo   [OK] Vite configured for network access (host: 0.0.0.0)
    ) else (
        echo   [WARNING] Vite host configuration not found
    )
) else (
    echo   [ERROR] vite.config.ts not found!
)
echo.

echo [4/5] Checking Windows Firewall rules...
echo.
netsh advfirewall firewall show rule name="Vite Dev Server" >nul 2>&1
if %errorlevel% == 0 (
    echo   [OK] Firewall rule for port 3000 exists
) else (
    echo   [WARNING] No firewall rule for port 3000 - may be blocked
)
netsh advfirewall firewall show rule name="Flask Backend" >nul 2>&1
if %errorlevel% == 0 (
    echo   [OK] Firewall rule for port 5000 exists
) else (
    echo   [WARNING] No firewall rule for port 5000 - may be blocked
)
echo.

echo [5/5] Network IP Addresses to use on mobile:
echo.
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set ip=%%a
    set ip=!ip:~1!
    echo   http://!ip!:3000
)
echo.

echo ========================================
echo Diagnostic Complete
echo ========================================
echo.
echo If ports are not in use, start the servers:
echo   1. Backend: py api.py
echo   2. Frontend: cd secureai-guardian ^&^& npm run dev
echo.
echo If firewall rules are missing, run as Administrator:
echo   New-NetFirewallRule -DisplayName "Vite Dev Server" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
echo   New-NetFirewallRule -DisplayName "Flask Backend" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
echo.
pause

