@echo off
REM Install dependencies for Ensemble Detector
echo Installing Ensemble Detector Dependencies...
echo.

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Upgrade pip first to avoid compatibility issues
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install new dependencies
echo Installing open-clip-torch...
python -m pip install open-clip-torch>=2.20.0

echo Installing LAA-Net dependencies...
python -m pip install albumentations>=1.1.0
python -m pip install imgaug>=0.4.0
python -m pip install scikit-image>=0.17.2
python -m pip install tensorboardX>=2.5.0

echo Installing face detection...
python -m pip install mtcnn>=0.1.1

echo.
echo Installation complete!
echo.
echo You can now test the detector with:
echo   python ai_model\enhanced_detector.py
pause

