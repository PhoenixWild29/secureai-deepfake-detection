# Test Everything - Complete Guide

## 🎯 Goal: Verify All Models Are Working

This guide tests:
1. ✅ V13 Model Loading
2. ✅ Ultimate Ensemble (All Models)
3. ✅ Test on Real Videos

---

## Step 1: Pull Latest Code

```bash
cd ~/secureai-deepfake-detection
git pull origin master
```

---

## Step 2: Test V13 Model Loading

```bash
# Copy test script
docker cp test_v13_loading.py secureai-backend:/app/

# Test V13
docker exec secureai-backend python3 test_v13_loading.py
```

**Expected Output:**
- ✅ V13 loaded successfully!
- Models loaded: 3/3
- Inference successful

---

## Step 3: Test Ultimate Ensemble

```bash
# Copy test script
docker cp test_ultimate_ensemble.py secureai-backend:/app/

# Test all models
docker exec secureai-backend python3 test_ultimate_ensemble.py
```

**Expected Output:**
- ✅ CLIP loaded successfully
- ✅ ResNet50 model created
- ✅ DeepFake Detector V13 loaded successfully!
- ✅ XceptionNet loaded successfully (or EfficientNet)
- ✅ Ultimate Ensemble loaded successfully!

---

## Step 4: Test on a Real Video

```bash
# Test on a video
docker exec secureai-backend python3 -c "
from ai_model.ensemble_detector import get_ensemble_detector
from utils.video_paths import VideoPathManager
import logging
logging.basicConfig(level=logging.INFO)

print('=' * 70)
print('🧪 Testing Ultimate Ensemble on Video')
print('=' * 70)
print()

# Find a test video
vm = VideoPathManager()
test_video = vm.find_video('test_video_1.mp4') or vm.find_video('*.mp4')

if test_video:
    print(f'Testing on: {test_video}')
    print()
    
    # Load ensemble
    print('Loading ultimate ensemble...')
    ensemble = get_ensemble_detector()
    
    if ensemble:
        print('✅ Ensemble loaded!')
        print()
        print('Running detection...')
        result = ensemble.detect(test_video)
        
        print()
        print('=' * 70)
        print('📊 Results')
        print('=' * 70)
        print(f'Video: {test_video}')
        print(f'Is Deepfake: {result[\"is_deepfake\"]}')
        print(f'Ensemble Probability: {result[\"ensemble_fake_probability\"]:.3f}')
        print()
        print('Individual Model Results:')
        print(f'  CLIP: {result[\"clip_fake_probability\"]:.3f}')
        print(f'  ResNet: {result[\"resnet_fake_probability\"]:.3f}')
        if 'v13_fake_probability' in result:
            print(f'  V13: {result[\"v13_fake_probability\"]:.3f}')
        if 'xception_fake_probability' in result:
            print(f'  XceptionNet: {result[\"xception_fake_probability\"]:.3f}')
        if 'efficientnet_fake_probability' in result:
            print(f'  EfficientNet: {result[\"efficientnet_fake_probability\"]:.3f}')
        print()
        print(f'Confidence: {result[\"overall_confidence\"]:.3f}')
        print(f'Models Used: {result.get(\"models_used\", [])}')
        print(f'Method: {result.get(\"method\", \"unknown\")}')
        print()
        print('✅ Test complete!')
    else:
        print('❌ Ensemble not loaded')
else:
    print('❌ No test videos found')
    print('   Add videos to: uploads/, test_videos/, or datasets/')
"
```

---

## Step 5: Comprehensive Test (All at Once)

```bash
# Copy comprehensive test script
docker cp test_comprehensive.py secureai-backend:/app/

# Run comprehensive test
docker exec secureai-backend python3 test_comprehensive.py
```

---

## Quick Test Commands (Copy-Paste Ready)

### Test V13 Only
```bash
cd ~/secureai-deepfake-detection && git pull origin master && docker cp test_v13_loading.py secureai-backend:/app/ && docker exec secureai-backend python3 test_v13_loading.py
```

### Test Ultimate Ensemble
```bash
cd ~/secureai-deepfake-detection && git pull origin master && docker cp test_ultimate_ensemble.py secureai-backend:/app/ && docker exec secureai-backend python3 test_ultimate_ensemble.py
```

### Test on Video
```bash
docker exec secureai-backend python3 -c "from ai_model.ensemble_detector import get_ensemble_detector; from utils.video_paths import VideoPathManager; vm = VideoPathManager(); video = vm.find_video('*.mp4'); ensemble = get_ensemble_detector(); result = ensemble.detect(video) if video else None; print('✅ Success!' if result else '❌ Failed')"
```

---

## Expected Model Status

After all tests, you should have:

| Model | Status | Notes |
|-------|--------|-------|
| CLIP | ✅ | ViT-B-32, zero-shot |
| ResNet50 | ✅ | 100% test accuracy |
| V13 | ✅ | 3 models (ConvNeXt, ViT, Swin) |
| XceptionNet | ✅ or ⚠️ | May use EfficientNet as fallback |
| EfficientNet | ✅ | Alternative to XceptionNet |
| Ultimate Ensemble | ✅ | All models combined |

---

## Troubleshooting

### If V13 Fails to Load
```bash
# Check if files are downloaded
docker exec secureai-backend python3 check_v13_status.py
```

### If Ensemble Fails
```bash
# Check individual models
docker exec secureai-backend python3 -c "
from ai_model.deepfake_detector_v13 import get_deepfake_detector_v13
from ai_model.xception_detector import get_xception_detector
from ai_model.efficientnet_detector import get_efficientnet_detector

print('V13:', '✅' if get_deepfake_detector_v13() else '❌')
print('XceptionNet:', '✅' if get_xception_detector() else '❌')
print('EfficientNet:', '✅' if get_efficientnet_detector() else '❌')
"
```

---

## Success Criteria

✅ All tests pass
✅ V13 loads all 3 models
✅ Ultimate ensemble combines all available models
✅ Video detection works
✅ Accuracy improved (93-98% expected)

---

**Run these tests to verify everything is working!** 🚀
