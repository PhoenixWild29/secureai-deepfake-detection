@echo off
echo Installing Flask-SocketIO and dependencies...
echo.

REM Check if .venv exists
if exist ".venv\Scripts\python.exe" (
    echo Using virtual environment: .venv
    .venv\Scripts\python.exe -m pip install Flask-SocketIO python-socketio
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    echo Installation complete!
    echo You can now start the backend with: py api.py
) else (
    echo No .venv found, installing globally...
    py -m pip install Flask-SocketIO python-socketio
    py -m pip install -r requirements.txt
    echo.
    echo Installation complete!
    echo You can now start the backend with: py api.py
)

pause

