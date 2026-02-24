@echo off
echo ========================================
echo Redis Setup - Quick Guide
echo ========================================
echo.

echo Redis Setup Options:
echo.
echo 1. Docker (Recommended - if Docker Desktop installed)
echo 2. WSL (if WSL installed)
echo 3. Manual Windows Installation
echo.

set /p choice="Choose option (1-3): "

if "%choice%"=="1" goto docker
if "%choice%"=="2" goto wsl
if "%choice%"=="3" goto manual
goto end

:docker
echo.
echo ========================================
echo Docker Setup
echo ========================================
echo.
echo Run this command in a new terminal:
echo   docker run -d -p 6379:6379 --name redis-secureai redis
echo.
echo Then verify with:
echo   docker ps
echo.
pause
goto config

:wsl
echo.
echo ========================================
echo WSL Setup
echo ========================================
echo.
echo Run these commands in WSL:
echo   sudo apt-get update
echo   sudo apt-get install redis-server
echo   sudo service redis-server start
echo.
pause
goto config

:manual
echo.
echo ========================================
echo Manual Windows Installation
echo ========================================
echo.
echo 1. Download Redis for Windows:
echo    https://github.com/microsoftarchive/redis/releases
echo.
echo 2. Download: Redis-x64-*.zip (latest version)
echo.
echo 3. Extract to: C:\Redis
echo.
echo 4. Run: C:\Redis\redis-server.exe
echo.
echo 5. Keep the window open (Redis runs in foreground)
echo.
pause
goto config

:config
echo.
echo ========================================
echo Configuration
echo ========================================
echo.
echo Add this to your .env file:
echo REDIS_URL=redis://localhost:6379/0
echo.

set /p add_env="Add to .env file now? (y/n): "
if /i "%add_env%"=="y" (
    echo REDIS_URL=redis://localhost:6379/0 >> .env
    echo.
    echo Added to .env file!
)

echo.
echo ========================================
echo Testing Redis Connection
echo ========================================
echo.
echo Make sure Redis is running, then press any key to test...
pause

py -c "from performance.caching import REDIS_AVAILABLE; print('Redis Available:', REDIS_AVAILABLE)" 2>nul
if errorlevel 1 (
    echo.
    echo Redis connection failed. Please:
    echo   1. Make sure Redis is running
    echo   2. Check REDIS_URL in .env file
    echo   3. Verify port 6379 is not blocked
) else (
    echo.
    echo Redis is connected and ready!
)

:end
echo.
echo Setup complete!
pause

