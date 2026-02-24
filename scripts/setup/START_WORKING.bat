@echo off
cls
echo ========================================
echo SecureAI DeepFake Detection System
echo ========================================
echo.
echo Starting web server...
echo Please wait for initialization...
echo.
echo Once you see "Running on http://0.0.0.0:5000"
echo Open your browser to: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

py start_server_simple.py

echo.
echo Server stopped.
pause
