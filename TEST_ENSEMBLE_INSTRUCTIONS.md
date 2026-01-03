# Ensemble Testing Instructions

## Step 1: Pull Latest Changes

```bash
# On your server
cd ~/secureai-deepfake-detection
git pull origin master
```

## Step 2: Copy Script to Container

```bash
# Copy the comprehensive ensemble testing script
docker cp test_ensemble_comprehensive.py secureai-backend:/app/
```

## Step 3: Run Ensemble Test

### Option A: Test on Available Videos (Recommended)

```bash
# Run comprehensive test (will find videos automatically)
docker exec secureai-backend python /app/test_ensemble_comprehensive.py
```

This script will:
- Find videos in `uploads/`, `test_videos/`, or dataset directories
- Test CLIP, ResNet50, and Ensemble on each video
- Compare performance metrics
- Generate report: `ensemble_test_results.json`

### Option B: Test on Specific Video

```bash
# Test ensemble on a specific video
docker exec secureai-backend python -c "
from ai_model.detect import detect_fake
result = detect_fake('uploads/your_video.mp4', model_type='ensemble')
print('Ensemble Result:')
print(f'  Is Fake: {result.get(\"is_fake\", False)}')
print(f'  Confidence: {result.get(\"confidence\", 0):.3f}')
print(f'  Ensemble Prob: {result.get(\"ensemble_fake_probability\", 0):.3f}')
print(f'  CLIP Prob: {result.get(\"clip_fake_probability\", 0):.3f}')
print(f'  ResNet Prob: {result.get(\"resnet_fake_probability\", 0):.3f}')
print(f'  Method: {result.get(\"method\", \"unknown\")}')
"
```

## What to Expect

### If Videos Are Found:
- Script tests all three models (CLIP, ResNet50, Ensemble)
- Shows predictions and confidence for each
- Calculates accuracy metrics (if ground truth available)
- Compares ensemble vs individual models

### If No Videos Found:
- Script will tell you where to place videos
- You can upload a video via the web interface first
- Or manually place videos in `uploads/` directory

## Understanding Results

### Good Ensemble Performance:
- **Ensemble accuracy > individual models**: Ensemble is working
- **Higher confidence**: Ensemble provides more confident predictions
- **Consistent predictions**: All models agree

### Ensemble Components:
- **CLIP probability**: Zero-shot detection score
- **ResNet probability**: Trained deepfake detector score
- **Ensemble probability**: Weighted combination of both

### Expected Improvements:
- Ensemble should match or exceed best individual model
- Typically 1-5% accuracy improvement
- More stable predictions (less variance)

## Troubleshooting

### "No test videos found"
- Upload a video via the web interface (it goes to `uploads/`)
- Or manually copy a video to `uploads/` directory
- Script will automatically detect it

### "Import errors"
- Ensure you pulled latest code: `git pull origin master`
- Check if ensemble_detector.py exists: `docker exec secureai-backend ls -la /app/ai_model/ensemble_detector.py`

### "Model not found"
- ResNet50 model should be at: `ai_model/resnet_resnet50_final.pth`
- Check: `docker exec secureai-backend ls -la /app/ai_model/resnet*.pth`

## Quick Test (Single Video)

If you just want to quickly test the ensemble on one video:

```bash
# Replace 'test.mp4' with your video filename
docker exec secureai-backend python -c "
import sys
sys.path.insert(0, '/app/ai_model')
from detect import detect_fake
result = detect_fake('uploads/test.mp4', model_type='ensemble')
print('=== Ensemble Test Result ===')
print(f'Prediction: {\"FAKE\" if result.get(\"is_fake\") else \"REAL\"}')
print(f'Ensemble Confidence: {result.get(\"ensemble_fake_probability\", result.get(\"confidence\", 0)):.3f}')
print(f'CLIP Score: {result.get(\"clip_fake_probability\", 0):.3f}')
print(f'ResNet Score: {result.get(\"resnet_fake_probability\", 0):.3f}')
print(f'Method: {result.get(\"method\", \"unknown\")}')
"
```

## Next Steps After Testing

1. **If ensemble outperforms**: Update API to use `model_type='ensemble'` by default
2. **If results are similar**: Ensemble provides redundancy and confidence
3. **If ensemble underperforms**: May need to tune ensemble weights

