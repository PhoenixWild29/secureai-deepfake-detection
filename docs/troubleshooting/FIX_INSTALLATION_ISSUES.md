# Fixing Installation Issues

## Issues Encountered

1. **Pip compatibility error** when installing `open-clip-torch`
2. **scikit-image==0.17.2 build failure** - too old for Python 3.13

## Solutions Applied

### 1. Fixed Installation Script
Created `install_ensemble_dependencies_fixed.bat` that:
- Upgrades pip first (fixes compatibility issues)
- Uses flexible version constraints (>= instead of ==)
- Has better error handling

### 2. Updated Requirements
Changed in `requirements.txt`:
- `scikit-image==0.17.2` → `scikit-image>=0.17.2`
- `albumentations==1.1.0` → `albumentations>=1.1.0`
- `imgaug==0.4.0` → `imgaug>=0.4.0`

## What to Do Now

### Option 1: Use the Fixed Script (Recommended)
```cmd
install_ensemble_dependencies_fixed.bat
```

### Option 2: Manual Installation (Step by Step)

1. **Upgrade pip:**
   ```cmd
   python -m pip install --upgrade pip
   ```

2. **Install open-clip-torch:**
   ```cmd
   python -m pip install open-clip-torch>=2.20.0
   ```
   If this fails, try:
   ```cmd
   python -m pip install open-clip-torch --no-cache-dir
   ```

3. **Install face detection:**
   ```cmd
   python -m pip install mtcnn>=0.1.1
   ```

4. **Install LAA-Net dependencies:**
   ```cmd
   python -m pip install albumentations>=1.1.0
   python -m pip install imgaug>=0.4.0
   python -m pip install scikit-image --upgrade
   python -m pip install tensorboardX>=2.5.0
   ```

## What's Already Installed

From your output, these are **already installed**:
- ✅ `albumentations-1.1.0`
- ✅ `imgaug-0.4.0`
- ✅ `scikit-image-0.25.2` (newer version installed, which is fine!)
- ✅ `numpy-2.2.6`
- ✅ `opencv-python-headless`
- ✅ Other dependencies

## What Still Needs Installation

1. **open-clip-torch** - This is the critical one for CLIP detection
2. **mtcnn** - For face detection (optional but recommended)

## Quick Fix Commands

Run these in order:

```cmd
REM 1. Upgrade pip
python -m pip install --upgrade pip

REM 2. Install open-clip-torch (try this first)
python -m pip install open-clip-torch>=2.20.0

REM 3. If that fails, try without cache
python -m pip install open-clip-torch --no-cache-dir

REM 4. Install face detection
python -m pip install mtcnn>=0.1.1
```

## Verify Installation

After installation, test:

```cmd
python -c "import open_clip; print('open-clip-torch: OK')"
python -c "from mtcnn import MTCNN; print('MTCNN: OK')"
python test_ensemble_detector.py
```

## Notes

- **scikit-image 0.25.2 is fine** - it's newer than 0.17.2 and will work
- The LAA-Net dependencies are mostly installed
- **open-clip-torch is the critical missing piece** for CLIP detection
- Once open-clip-torch is installed, the detector will work!

## If open-clip-torch Still Fails

Try these alternatives:

1. **Install from GitHub:**
   ```cmd
   python -m pip install git+https://github.com/mlfoundations/open_clip.git
   ```

2. **Install specific version:**
   ```cmd
   python -m pip install open-clip-torch==2.24.0
   ```

3. **Check Python version compatibility:**
   ```cmd
   python --version
   ```
   (Python 3.8-3.12 recommended, 3.13 might have compatibility issues)

4. **Use conda instead:**
   ```cmd
   conda install -c conda-forge open-clip-torch
   ```

