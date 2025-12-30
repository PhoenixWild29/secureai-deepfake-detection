@echo off
REM Script to add Windows Firewall rules for mobile access
echo ========================================
echo Adding Windows Firewall Rules
echo ========================================
echo.
echo This script will add firewall rules to allow:
echo   - Port 3000 (Frontend/Vite)
echo   - Port 5000 (Backend/Flask)
echo.
echo NOTE: This requires Administrator privileges!
echo.
pause

echo.
echo [1/2] Adding rule for port 3000 (Frontend)...
netsh advfirewall firewall add rule name="Vite Dev Server" dir=in action=allow protocol=TCP localport=3000
if %errorlevel% == 0 (
    echo   [OK] Firewall rule added for port 3000
) else (
    echo   [ERROR] Failed to add firewall rule - Run as Administrator!
)

echo.
echo [2/2] Adding rule for port 5000 (Backend)...
netsh advfirewall firewall add rule name="Flask Backend" dir=in action=allow protocol=TCP localport=5000
if %errorlevel% == 0 (
    echo   [OK] Firewall rule added for port 5000
) else (
    echo   [ERROR] Failed to add firewall rule - Run as Administrator!
)

echo.
echo ========================================
echo Firewall Rules Added
echo ========================================
echo.
echo If you see errors, right-click this file and select
echo "Run as Administrator" to try again.
echo.
pause

