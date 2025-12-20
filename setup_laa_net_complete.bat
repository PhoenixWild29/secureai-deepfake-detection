@echo off
REM Complete LAA-Net setup script
echo Setting up LAA-Net integration...
echo.

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Create external directory if it doesn't exist
if not exist external mkdir external

REM Check if LAA-Net already exists
if exist external\laa_net (
    echo LAA-Net directory already exists.
    echo To reinstall, delete external\laa_net and run this script again.
    pause
    exit /b
)

echo Cloning LAA-Net repository...
cd external
git clone https://github.com/10Ring/LAA-Net laa_net
cd ..

if exist external\laa_net (
    echo.
    echo LAA-Net repository cloned successfully!
    echo.
    echo Next steps:
    echo 1. Install LAA-Net dependencies:
    echo    cd external\laa_net
    echo    pip install -r requirements.txt
    echo.
    echo 2. Download pre-trained weights from LAA-Net repository
    echo    (Check their README for download links)
    echo.
    echo 3. Update ai_model\enhanced_detector.py with LAA-Net imports
    echo    (See external\README.md for details)
) else (
    echo.
    echo Failed to clone LAA-Net repository.
    echo Please check your internet connection and try again.
)

pause

