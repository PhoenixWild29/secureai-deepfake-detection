@echo off
REM SecureAI Guardian - Environment Setup Script
REM This script creates the .env.local file with default configuration

echo ========================================
echo SecureAI Guardian - Environment Setup
echo ========================================
echo.

if exist .env.local (
    echo .env.local already exists!
    echo.
    choice /C YN /M "Do you want to overwrite it"
    if errorlevel 2 goto :end
    if errorlevel 1 goto :create
) else (
    goto :create
)

:create
echo Creating .env.local file...
echo.

(
echo # SecureAI Guardian Environment Configuration
echo # This file contains your local environment variables
echo # DO NOT commit this file to version control ^(it's in .gitignore^)
echo.
echo # Backend API URL
echo # For Flask: http://localhost:5000
echo # For FastAPI: http://localhost:8000
echo # Update this to match your backend server port
echo VITE_API_BASE_URL=http://localhost:5000
echo.
echo # Google Gemini API Key ^(for SecureSage AI consultant^)
echo # Get your API key from: https://makersuite.google.com/app/apikey
echo # IMPORTANT: Replace 'your_actual_api_key_here' with your actual Gemini API key
echo GEMINI_API_KEY=your_actual_api_key_here
echo.
echo # WebSocket URL ^(optional, for real-time progress updates^)
echo # For Flask: ws://localhost:5000/ws
echo # For FastAPI: ws://localhost:8000/ws
echo VITE_WS_URL=ws://localhost:5000/ws
echo.
echo # Environment
echo NODE_ENV=development
) > .env.local

echo .env.local created successfully!
echo.
echo IMPORTANT: Edit .env.local and add your Gemini API key!
echo.
echo Next steps:
echo 1. Edit .env.local and replace 'your_actual_api_key_here' with your Gemini API key
echo 2. Make sure your backend server is running ^(python api.py^)
echo 3. Run 'npm run dev' to start the frontend
echo.

:end
pause

