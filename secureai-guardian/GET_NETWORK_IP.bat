@echo off
REM Get Network IP Address for Mobile Access
echo ========================================
echo SecureAI Guardian - Network IP Finder
echo ========================================
echo.
echo Finding your network IP address...
echo.

REM Get IPv4 address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set IP=%%a
    set IP=!IP: =!
    echo Your Network IP Address: !IP!
    echo.
    echo ========================================
    echo Mobile Access URLs:
    echo ========================================
    echo Frontend: http://!IP!:3000
    echo Backend:  http://!IP!:5000
    echo.
    echo Use these URLs on your phone (must be on same Wi-Fi)
    echo ========================================
    goto :done
)

:done
echo.
echo Press any key to close...
pause >nul

