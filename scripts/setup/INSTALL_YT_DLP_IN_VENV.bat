@echo off
REM Install yt-dlp in the virtual environment
echo ========================================
echo Installing yt-dlp in Virtual Environment
echo ========================================
echo.

if exist ".venv\Scripts\python.exe" (
    echo Found virtual environment at .venv
    echo Installing yt-dlp...
    .venv\Scripts\python.exe -m pip install yt-dlp
    echo.
    echo Verifying installation...
    .venv\Scripts\python.exe -m yt_dlp --version
    echo.
    echo ========================================
    echo Installation complete!
    echo ========================================
    echo.
    echo Please restart your backend server for changes to take effect.
) else if exist "venv\Scripts\python.exe" (
    echo Found virtual environment at venv
    echo Installing yt-dlp...
    venv\Scripts\python.exe -m pip install yt-dlp
    echo.
    echo Verifying installation...
    venv\Scripts\python.exe -m yt_dlp --version
    echo.
    echo ========================================
    echo Installation complete!
    echo ========================================
    echo.
    echo Please restart your backend server for changes to take effect.
) else (
    echo No virtual environment found.
    echo Installing yt-dlp globally...
    py -m pip install yt-dlp
    echo.
    echo Verifying installation...
    py -m yt_dlp --version
    echo.
    echo ========================================
    echo Installation complete!
    echo ========================================
    echo.
    echo Please restart your backend server for changes to take effect.
)

echo.
pause

