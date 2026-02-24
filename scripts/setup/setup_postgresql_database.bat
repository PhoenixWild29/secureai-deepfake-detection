@echo off
echo ========================================
echo PostgreSQL Database Setup
echo ========================================
echo.

set POSTGRES_PASSWORD=RNYZa9z8
set POSTGRES_PORT=5432
set DB_NAME=secureai_db
set DB_USER=secureai
set DB_PASSWORD=SecureAI2024!DB

echo Configuration:
echo   PostgreSQL Password: %POSTGRES_PASSWORD%
echo   Port: %POSTGRES_PORT%
echo   Database Name: %DB_NAME%
echo   Database User: %DB_USER%
echo.
pause

echo.
echo Step 1: Finding PostgreSQL installation...
set PG_PATH=
if exist "C:\Program Files\PostgreSQL\16\bin\psql.exe" (
    set PG_PATH=C:\Program Files\PostgreSQL\16\bin
    echo Found PostgreSQL 16
) else if exist "C:\Program Files\PostgreSQL\15\bin\psql.exe" (
    set PG_PATH=C:\Program Files\PostgreSQL\15\bin
    echo Found PostgreSQL 15
) else if exist "C:\Program Files\PostgreSQL\14\bin\psql.exe" (
    set PG_PATH=C:\Program Files\PostgreSQL\14\bin
    echo Found PostgreSQL 14
) else (
    echo ERROR: PostgreSQL not found in standard location
    echo Please provide the path to PostgreSQL bin directory:
    set /p PG_PATH="PostgreSQL bin path: "
)

if "%PG_PATH%"=="" (
    echo ERROR: Could not find PostgreSQL
    pause
    exit /b 1
)

echo.
echo Step 2: Creating database and user...
echo.

REM Create SQL script
echo CREATE DATABASE %DB_NAME%; > %TEMP%\setup_db.sql
echo CREATE USER %DB_USER% WITH ENCRYPTED PASSWORD '%DB_PASSWORD%'; >> %TEMP%\setup_db.sql
echo GRANT ALL PRIVILEGES ON DATABASE %DB_NAME% TO %DB_USER%; >> %TEMP%\setup_db.sql
echo \c %DB_NAME% >> %TEMP%\setup_db.sql
echo GRANT ALL ON SCHEMA public TO %DB_USER%; >> %TEMP%\setup_db.sql

echo Running SQL commands...
"%PG_PATH%\psql.exe" -U postgres -f %TEMP%\setup_db.sql

if errorlevel 1 (
    echo.
    echo ERROR: Database setup failed
    echo Please check:
    echo   1. PostgreSQL service is running
    echo   2. Password is correct: %POSTGRES_PASSWORD%
    echo   3. You have admin privileges
    pause
    exit /b 1
)

echo.
echo Step 3: Database and user created successfully!
echo.
echo Database: %DB_NAME%
echo User: %DB_USER%
echo Password: %DB_PASSWORD%
echo.

echo Step 4: Updating .env file...
echo.
set ENV_LINE=DATABASE_URL=postgresql://%DB_USER%:%DB_PASSWORD%@localhost:%POSTGRES_PORT%/%DB_NAME%

REM Check if .env exists and update DATABASE_URL
if exist .env (
    REM Remove old DATABASE_URL line if exists
    findstr /v /c:"DATABASE_URL=" .env > %TEMP%\env_temp.txt 2>nul
    move /y %TEMP%\env_temp.txt .env >nul
    echo %ENV_LINE% >> .env
    echo Added DATABASE_URL to .env file
) else (
    echo %ENV_LINE% > .env
    echo Created .env file with DATABASE_URL
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Initialize database schema: py -c "from database.db_session import init_db; init_db()"
echo   2. Test connection: py -c "from database.db_session import get_db; db = next(get_db()); print('Connected!')"
echo.
pause

