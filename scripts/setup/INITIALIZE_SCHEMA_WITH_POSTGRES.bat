@echo off
echo ========================================
echo Initialize Database Schema
echo ========================================
echo.
echo This will initialize the database schema using the postgres superuser.
echo.
pause

py -c "import os; os.environ['DATABASE_URL'] = 'postgresql://postgres:RNYZa9z8@localhost:5432/secureai_db'; from database.db_session import create_engine, Base; from database.models import *; engine = create_engine(os.environ['DATABASE_URL']); Base.metadata.create_all(bind=engine); print('OK: Database schema initialized successfully!')"

if errorlevel 1 (
    echo.
    echo ERROR: Schema initialization failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Schema Initialized!
echo ========================================
echo.
echo Next: Fix secureai user password in pgAdmin
echo Then update .env with: DATABASE_URL=postgresql://secureai:YOUR_PASSWORD@localhost:5432/secureai_db
echo.
pause

