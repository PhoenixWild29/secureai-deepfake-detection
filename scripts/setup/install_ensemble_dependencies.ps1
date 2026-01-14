# PowerShell script to install Ensemble Detector dependencies
Write-Host "Installing Ensemble Detector Dependencies..." -ForegroundColor Green
Write-Host ""

# Activate virtual environment if it exists
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .\.venv\Scripts\Activate.ps1
}

# Upgrade pip first to avoid compatibility issues
Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Install new dependencies
Write-Host "Installing open-clip-torch..." -ForegroundColor Cyan
python -m pip install open-clip-torch>=2.20.0

Write-Host "Installing LAA-Net dependencies..." -ForegroundColor Cyan
python -m pip install albumentations>=1.1.0
python -m pip install imgaug>=0.4.0
python -m pip install scikit-image>=0.17.2
python -m pip install tensorboardX>=2.5.0

Write-Host "Installing face detection..." -ForegroundColor Cyan
python -m pip install mtcnn>=0.1.1

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "You can now test the detector with:" -ForegroundColor Yellow
Write-Host "  python ai_model\enhanced_detector.py" -ForegroundColor Yellow

