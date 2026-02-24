@echo off
echo ========================================
echo PostgreSQL Quick Setup
echo ========================================
echo.
echo This script will help you set up PostgreSQL.
echo.
echo Option 1: Use pgAdmin (GUI - Recommended)
echo Option 2: Use Command Line (psql)
echo.
set /p choice="Choose option (1 or 2): "

if "%choice%"=="1" goto pgadmin
if "%choice%"=="2" goto commandline
goto end

:pgadmin
echo.
echo ========================================
echo pgAdmin Setup Instructions
echo ========================================
echo.
echo 1. Open pgAdmin 4 from Start Menu
echo 2. Connect to server (password: RNYZa9z8)
echo 3. Create database: secureai_db
echo 4. Create user: secureai (password: SecureAI2024!DB)
echo 5. Grant permissions (see POSTGRESQL_MANUAL_SETUP.md)
echo.
echo Opening guide...
start POSTGRESQL_MANUAL_SETUP.md
pause
goto config

:commandline
echo.
echo ========================================
echo Command Line Setup
echo ========================================
echo.
echo Finding PostgreSQL installation...
set PG_PATH=
if exist "C:\Program Files\PostgreSQL\16\bin\psql.exe" (
    set PG_PATH=C:\Program Files\PostgreSQL\16\bin
) else if exist "C:\Program Files\PostgreSQL\15\bin\psql.exe" (
    set PG_PATH=C:\Program Files\PostgreSQL\15\bin
) else if exist "C:\Program Files\PostgreSQL\14\bin\psql.exe" (
    set PG_PATH=C:\Program Files\PostgreSQL\14\bin
)

if "%PG_PATH%"=="" (
    echo ERROR: PostgreSQL not found
    echo Please run pgAdmin setup instead
    pause
    goto end
)

echo Found PostgreSQL at: %PG_PATH%
echo.
echo Creating SQL script...
echo CREATE DATABASE secureai_db; > %TEMP%\setup.sql
echo CREATE USER secureai WITH ENCRYPTED PASSWORD 'SecureAI2024!DB'; >> %TEMP%\setup.sql
echo GRANT ALL PRIVILEGES ON DATABASE secureai_db TO secureai; >> %TEMP%\setup.sql
echo \c secureai_db >> %TEMP%\setup.sql
echo GRANT ALL ON SCHEMA public TO secureai; >> %TEMP%\setup.sql

echo.
echo Running SQL commands...
echo You will be prompted for the postgres password: RNYZa9z8
echo.
"%PG_PATH%\psql.exe" -U postgres -f %TEMP%\setup.sql

if errorlevel 1 (
    echo.
    echo Setup failed. Please use pgAdmin method instead.
    pause
    goto end
)

echo.
echo Database setup complete!
goto config

:config
echo.
echo ========================================
echo Configuration
echo ========================================
echo.
echo Adding DATABASE_URL to .env file...
echo DATABASE_URL=postgresql://secureai:SecureAI2024!DB@localhost:5432/secureai_db >> .env
echo.
echo Configuration complete!
echo.
echo Next steps:
echo   1. Initialize schema: py -c "from database.db_session import init_db; init_db()"
echo   2. Test connection: py -c "from database.db_session import get_db; db = next(get_db()); print('OK: Connected!')"
echo.

:end
pause

