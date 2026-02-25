@echo off
REM Quick test script for Ensemble Detector
echo ========================================
echo Testing Ensemble Detector
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

echo Running test script...
echo.
python test_ensemble_detector.py

echo.
echo ========================================
echo Test Complete!
echo ========================================
pause

