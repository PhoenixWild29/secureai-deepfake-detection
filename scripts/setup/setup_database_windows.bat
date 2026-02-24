@echo off
echo ========================================
echo PostgreSQL Database Setup
echo ========================================
echo.

echo This script will help you set up PostgreSQL database.
echo.

echo Step 1: Install PostgreSQL
echo Download from: https://www.postgresql.org/download/windows/
echo.
echo Step 2: During installation, remember the postgres user password
echo.
echo Step 3: After installation, run this script again to create database
echo.
pause

echo.
echo ========================================
echo Database Creation
echo ========================================
echo.

set /p db_name=Enter database name (default: secureai_db): 
if "%db_name%"=="" set db_name=secureai_db

set /p db_user=Enter database user (default: secureai): 
if "%db_user%"=="" set db_user=secureai

set /p db_password=Enter database password: 

echo.
echo Creating database and user...
echo.
echo Run these commands in psql (as postgres user):
echo   CREATE DATABASE %db_name%;
echo   CREATE USER %db_user% WITH ENCRYPTED PASSWORD '%db_password%';
echo   GRANT ALL PRIVILEGES ON DATABASE %db_name% TO %db_user%;
echo   \c %db_name%
echo   GRANT ALL ON SCHEMA public TO %db_user%;
echo.

echo To open psql:
echo   1. Open Command Prompt as Administrator
echo   2. Navigate to PostgreSQL bin folder (usually C:\Program Files\PostgreSQL\15\bin)
echo   3. Run: psql -U postgres
echo.

pause

echo.
echo ========================================
echo Configuration
echo ========================================
echo.
echo Add this to your .env file:
echo DATABASE_URL=postgresql://%db_user%:%db_password%@localhost:5432/%db_name%
echo.

set /p configure="Add to .env file now? (y/n): "
if /i "%configure%"=="y" (
    echo DATABASE_URL=postgresql://%db_user%:%db_password%@localhost:5432/%db_name% >> .env
    echo.
    echo Added to .env file!
)

echo.
echo ========================================
echo Initialize Database
echo ========================================
echo.
set /p init="Initialize database schema now? (y/n): "
if /i "%init%"=="y" (
    echo.
    echo Initializing database schema...
    py -c "from database.db_session import init_db; init_db()"
    echo.
    echo Database schema initialized!
)

echo.
set /p migrate="Migrate existing data from files? (y/n): "
if /i "%migrate%"=="y" (
    echo.
    echo Migrating data...
    py database/migrate_from_files.py
    echo.
    echo Migration complete!
)

echo.
echo ========================================
echo Verification
echo ========================================
echo.
echo Testing database connection...
py -c "from database.db_session import get_db; db = next(get_db()); print('Database connection successful!'); print('Tables created:', db.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = ''public''').scalar())" 2>nul
if errorlevel 1 (
    echo.
    echo Database connection failed. Please check:
    echo   1. PostgreSQL is running
    echo   2. DATABASE_URL is correct in .env
    echo   3. User has proper permissions
) else (
    echo.
    echo Database is ready!
)

echo.
echo Setup complete!
pause

