# Step-by-Step Setup Guide

## Step 1: Install Dependencies ✅

You have two options to install the new dependencies:

### Option A: Run the Batch Script (Windows)
```cmd
install_ensemble_dependencies.bat
```

### Option B: Run the PowerShell Script
```powershell
.\install_ensemble_dependencies.ps1
```

### Option C: Manual Installation
```cmd
python -m pip install open-clip-torch>=2.20.0
python -m pip install albumentations==1.1.0
python -m pip install imgaug==0.4.0
python -m pip install scikit-image==0.17.2
python -m pip install tensorboardX>=2.5.0
python -m pip install mtcnn>=0.1.1
```

**Expected output:** Dependencies install successfully. The first run of CLIP will download model weights (this may take a few minutes).

---

## Step 2: Test CLIP-Only Detection ✅

Run the test script:

```cmd
python test_ensemble_detector.py
```

Or test directly:

```python
from ai_model.enhanced_detector import EnhancedDetector

detector = EnhancedDetector()
result = detector.detect('sample_video.mp4')
print(result)
```

**Expected output:**
- Detector initializes successfully
- CLIP model loads (first time downloads weights)
- Detection runs on test videos
- Results show ensemble_fake_probability, clip_fake_probability, etc.

**Note:** If you see "LAA-Net: Not available", that's expected - we'll set it up in Step 3.

---

## Step 3: Set Up LAA-Net (Optional but Recommended) ✅

### Option A: Run the Setup Script
```cmd
setup_laa_net_complete.bat
```

### Option B: Manual Setup

1. **Clone LAA-Net repository:**
   ```cmd
   cd external
   git clone https://github.com/10Ring/LAA-Net laa_net
   cd ..
   ```

2. **Install LAA-Net dependencies:**
   ```cmd
   cd external\laa_net
   pip install -r requirements.txt
   cd ..\..
   ```

3. **Download pre-trained weights:**
   - Check the LAA-Net repository README for download links
   - Usually available on Google Drive
   - Place weights in `external\laa_net\weights\` or note the path

4. **Update the detector code:**
   - Open `ai_model\enhanced_detector.py`
   - Find the LAA-Net import section (around line 20-30)
   - Uncomment and adjust imports based on actual LAA-Net structure
   - Update the `__init__` method to load LAA-Net model
   - Implement the `laa_detect_frames` method (see TODOs in code)

**Expected result:** Full ensemble detection with both CLIP and LAA-Net working together.

---

## Troubleshooting

### Issue: "Module not found" errors
**Solution:** Make sure you've run Step 1 to install dependencies.

### Issue: CLIP model download fails
**Solution:** Check internet connection. The first run downloads ~600MB of model weights.

### Issue: "Python was not found"
**Solution:** 
- Activate your virtual environment: `.venv\Scripts\activate.bat`
- Or use full path to Python: `C:\Python\python.exe -m pip install ...`

### Issue: LAA-Net setup fails
**Solution:** 
- The detector works fine with CLIP-only mode
- LAA-Net is optional - you can use CLIP-only detection
- Check `external\README.md` for detailed LAA-Net setup instructions

### Issue: Face detection errors
**Solution:**
- Install MTCNN: `pip install mtcnn`
- The detector falls back to OpenCV Haar cascades if MTCNN unavailable

---

## Verification Checklist

After completing all steps:

- [ ] Dependencies installed (Step 1)
- [ ] CLIP-only detection works (Step 2)
- [ ] Test script runs successfully
- [ ] LAA-Net repository cloned (Step 3, optional)
- [ ] LAA-Net weights downloaded (Step 3, optional)
- [ ] Full ensemble working (Step 3, optional)

---

## Quick Test Commands

```cmd
# Test 1: Import check
python -c "from ai_model.enhanced_detector import EnhancedDetector; print('Import successful!')"

# Test 2: Initialization check
python -c "from ai_model.enhanced_detector import EnhancedDetector; d = EnhancedDetector(); print(f'Detector ready on {d.device}')"

# Test 3: Full test
python test_ensemble_detector.py
```

---

## Next Steps After Setup

1. **Integrate with API:** Use the detector in `api.py` endpoints
2. **Test with your videos:** Try real and deepfake videos
3. **Fine-tune prompts:** Adjust CLIP prompts for your use case
4. **Add adaptive weighting:** Improve ensemble fusion logic

---

## Need Help?

- See `ENSEMBLE_DETECTOR_SETUP.md` for detailed documentation
- Check `IMPLEMENTATION_SUMMARY.md` for architecture details
- Review `QUICK_START_ENSEMBLE.md` for quick reference

