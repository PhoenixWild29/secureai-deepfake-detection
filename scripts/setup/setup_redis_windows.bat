@echo off
echo ========================================
echo Redis Setup for SecureAI Guardian
echo ========================================
echo.

echo This script will help you set up Redis for caching.
echo.
echo Options:
echo 1. Use Docker (Recommended - Easiest)
echo 2. Use WSL (Windows Subsystem for Linux)
echo 3. Manual installation
echo.

set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" goto docker
if "%choice%"=="2" goto wsl
if "%choice%"=="3" goto manual
goto end

:docker
echo.
echo Installing Redis via Docker...
echo.
echo Step 1: Make sure Docker Desktop is installed
echo Step 2: Run this command:
echo   docker run -d -p 6379:6379 --name redis-secureai redis
echo.
echo After Docker container is running, Redis will be available at localhost:6379
echo.
pause
goto config

:wsl
echo.
echo Setting up Redis in WSL...
echo.
echo Run these commands in WSL:
echo   sudo apt-get update
echo   sudo apt-get install redis-server
echo   sudo service redis-server start
echo.
echo Redis will be available at localhost:6379
echo.
pause
goto config

:manual
echo.
echo Manual Redis Installation:
echo.
echo 1. Download Redis for Windows:
echo    https://github.com/microsoftarchive/redis/releases
echo.
echo 2. Extract and run redis-server.exe
echo.
echo 3. Redis will be available at localhost:6379
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
echo Testing Redis connection...
py -c "import redis; r = redis.Redis(host='localhost', port=6379, db=0); r.ping(); print('Redis connection successful!')" 2>nul
if errorlevel 1 (
    echo.
    echo Redis is not running. Please start Redis first.
    echo Then run: py -c "from performance.caching import REDIS_AVAILABLE; print('Redis:', REDIS_AVAILABLE)"
) else (
    echo.
    echo Redis is running and accessible!
)

:end
echo.
echo Setup complete!
pause

