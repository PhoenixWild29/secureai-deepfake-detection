# Debug V13 Hanging Issue

## Problem
All 3 model files are downloaded, but V13 loading hangs at "Creating ViT-Large architecture..."

## Root Cause
The ViT-Large model creation is likely:
1. Taking a very long time (ViT-Large is huge)
2. Failing silently
3. Using wrong backbone name

## Solution: Test Each Model Individually

```bash
cd ~/secureai-deepfake-detection
git pull origin master

# Copy individual test script
docker cp test_v13_models_individually.py secureai-backend:/app/

# Test each model separately
docker exec secureai-backend python3 test_v13_models_individually.py
```

This will:
- Test each model one at a time
- Show exactly where it fails
- Test model creation separately from weight loading
- Give detailed error messages

## Alternative: Check Backbone Names

The issue might be the backbone name. Try checking available models:

```bash
docker exec secureai-backend python3 -c "
import timm
# Check ViT models
vit_models = timm.list_models('*vit_large*', pretrained=False)
print('ViT-Large models:', vit_models[:10])

# Check if our exact name exists
print('vit_large_patch16_224 exists:', 'vit_large_patch16_224' in timm.list_models(pretrained=False))
"
```

## Quick Fix: Skip V13 for Now

If V13 keeps hanging, you can still use the ensemble without it:

```bash
# Test ensemble without V13
docker exec secureai-backend python3 -c "
from ai_model.ensemble_detector import get_ensemble_detector
ensemble = get_ensemble_detector()
print('Ensemble loaded:', ensemble is not None)
print('V13 available:', ensemble.v13_detector and ensemble.v13_detector.model_loaded if hasattr(ensemble, 'v13_detector') else False)
"
```

The ensemble will work with CLIP + ResNet50 + XceptionNet + EfficientNet, which is still excellent!

---

**Run the individual model test to find exactly where it's hanging!** 🔍
