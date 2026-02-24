@echo off
REM Fixed installation script for Ensemble Detector Dependencies
echo Installing Ensemble Detector Dependencies (Fixed Version)...
echo.

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Upgrade pip first to avoid compatibility issues
echo ========================================
echo Step 1: Upgrading pip...
echo ========================================
python -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip
    pause
    exit /b 1
)

REM Install open-clip-torch (most critical)
echo.
echo ========================================
echo Step 2: Installing open-clip-torch...
echo ========================================
python -m pip install open-clip-torch>=2.20.0
if errorlevel 1 (
    echo WARNING: open-clip-torch installation had issues
    echo Trying alternative installation method...
    python -m pip install open-clip-torch --no-cache-dir
)

REM Install face detection (needed for LAA-Net preprocessing)
echo.
echo ========================================
echo Step 3: Installing face detection (MTCNN)...
echo ========================================
python -m pip install mtcnn>=0.1.1

REM Install LAA-Net dependencies (with flexible versions)
echo.
echo ========================================
echo Step 4: Installing LAA-Net dependencies...
echo ========================================
echo Installing albumentations...
python -m pip install albumentations>=1.1.0

echo Installing imgaug...
python -m pip install imgaug>=0.4.0

echo Installing scikit-image (using compatible version)...
REM Try to install latest compatible version first
python -m pip install scikit-image --upgrade
if errorlevel 1 (
    echo Trying specific version...
    python -m pip install "scikit-image>=0.20.0"
)

echo Installing tensorboardX...
python -m pip install tensorboardX>=2.5.0

echo.
echo ========================================
echo Installation Summary
echo ========================================
echo.
echo Core dependencies installed:
echo   - open-clip-torch (for CLIP detection)
echo   - mtcnn (for face detection)
echo.
echo LAA-Net dependencies installed:
echo   - albumentations
echo   - imgaug
echo   - scikit-image
echo   - tensorboardX
echo.
echo ========================================
echo Next Steps:
echo ========================================
echo 1. Test the detector: python test_ensemble_detector.py
echo 2. If open-clip-torch failed, try: python -m pip install open-clip-torch --no-cache-dir
echo 3. For LAA-Net setup: run setup_laa_net_complete.bat
echo.
pause

