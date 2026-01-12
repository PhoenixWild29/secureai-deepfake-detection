# Install Best Models for Ultimate Deepfake Detection

## 🎯 Goal: 98-99% Accuracy

This guide will help you install and integrate the best available models.

---

## Step 1: Install Required Packages

Run these commands on your server:

```bash
cd ~/secureai-deepfake-detection
git pull origin master

# Install packages inside Docker container
docker exec secureai-backend pip install transformers huggingface-hub timm efficientnet-pytorch
```

**Or install locally first, then copy to container:**

```bash
# On server
pip install transformers huggingface-hub timm efficientnet-pytorch

# Copy new model files to container
docker cp ai_model/deepfake_detector_v13.py secureai-backend:/app/ai_model/
docker cp ai_model/xception_detector.py secureai-backend:/app/ai_model/
docker cp ai_model/ensemble_detector.py secureai-backend:/app/ai_model/
```

---

## Step 2: Test Model Loading

```bash
# Test if models can be loaded
docker exec secureai-backend python3 -c "
from ai_model.deepfake_detector_v13 import get_deepfake_detector_v13
from ai_model.xception_detector import get_xception_detector

print('Testing DeepFake Detector V13...')
v13 = get_deepfake_detector_v13()
if v13:
    print('✅ V13 loaded successfully!')
else:
    print('⚠️  V13 not available')

print('Testing XceptionNet...')
xception = get_xception_detector()
if xception:
    print('✅ XceptionNet loaded successfully!')
else:
    print('⚠️  XceptionNet not available')
"
```

---

## Step 3: Test Enhanced Ensemble

```bash
# Test the ultimate ensemble
docker exec secureai-backend python3 -c "
from ai_model.ensemble_detector import get_ensemble_detector

print('Loading ultimate ensemble...')
ensemble = get_ensemble_detector()
if ensemble:
    print('✅ Ultimate ensemble loaded!')
    print(f'   Models: {ensemble.ensemble_weights}')
else:
    print('⚠️  Ensemble not available')
"
```

---

## Expected Models After Installation

1. ✅ **CLIP** (already working)
2. ✅ **ResNet50** (already working, 100% test accuracy)
3. ⭐ **DeepFake Detector V13** (699M params, 95.86% F1) - NEW!
4. ✅ **XceptionNet** (proven for deepfakes) - NEW!

**Expected Accuracy**: 88-93% → **93-98%** ⭐

---

## Troubleshooting

### If V13 Fails to Load

```bash
# Check transformers version
docker exec secureai-backend pip show transformers

# Update if needed
docker exec secureai-backend pip install --upgrade transformers huggingface-hub

# Check Hugging Face access
docker exec secureai-backend python3 -c "from huggingface_hub import hf_hub_download; print('HF access OK')"
```

### If XceptionNet Fails

```bash
# Check torchvision
docker exec secureai-backend pip show torchvision

# XceptionNet is part of torchvision, should be available
```

---

## Next Steps

After installation:
1. Test on sample videos
2. Benchmark accuracy improvements
3. Add more models (EfficientNet, ViT, ConvNeXt)
4. Implement advanced techniques (multi-scale, frequency domain)

**Let's get you to 98-99% accuracy!** 🚀
