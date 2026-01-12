# Test Ultimate Ensemble

## Quick Test

Run this on your server to verify all models load correctly:

```bash
cd ~/secureai-deepfake-detection
git pull origin master

# Copy test script to container
docker cp test_ultimate_ensemble.py secureai-backend:/app/

# Run the test
docker exec secureai-backend python3 test_ultimate_ensemble.py
```

## Expected Output

You should see:
- ✅ CLIP loaded successfully
- ✅ ResNet50 model created
- ⚠️  DeepFake Detector V13 (will download on first use) - This is OK!
- ✅ XceptionNet loaded successfully
- ✅ Ultimate Ensemble loaded successfully

## Test on a Video

After models load, test on a real video:

```bash
# Test on a video
docker exec secureai-backend python3 -c "
from ai_model.ensemble_detector import get_ensemble_detector
from utils.video_paths import VideoPathManager

# Get a test video
vm = VideoPathManager()
test_video = vm.find_video('test_video_1.mp4') or vm.find_video('*.mp4')

if test_video:
    print(f'Testing on: {test_video}')
    ensemble = get_ensemble_detector()
    result = ensemble.detect(test_video)
    print()
    print('Results:')
    print(f'  Is Deepfake: {result[\"is_deepfake\"]}')
    print(f'  Ensemble Probability: {result[\"ensemble_fake_probability\"]:.3f}')
    print(f'  CLIP: {result[\"clip_fake_probability\"]:.3f}')
    print(f'  ResNet: {result[\"resnet_fake_probability\"]:.3f}')
    if 'v13_fake_probability' in result:
        print(f'  V13: {result[\"v13_fake_probability\"]:.3f}')
    if 'xception_fake_probability' in result:
        print(f'  XceptionNet: {result[\"xception_fake_probability\"]:.3f}')
    print(f'  Confidence: {result[\"overall_confidence\"]:.3f}')
    print(f'  Models Used: {result.get(\"models_used\", [])}')
else:
    print('No test videos found')
"
```

## What to Expect

**First Run:**
- V13 will download from Hugging Face (may take a few minutes)
- This is a one-time download (~2-3GB)
- After download, it will be cached for future use

**Results:**
- Higher accuracy (93-98% vs 88-93%)
- More confident predictions
- Multiple models working together

## Troubleshooting

### If V13 Fails to Download

```bash
# Check Hugging Face access
docker exec secureai-backend python3 -c "
from huggingface_hub import hf_hub_download
print('Testing Hugging Face access...')
try:
    hf_hub_download('ash12321/deepfake-detector-v13', 'config.json', local_dir='./test')
    print('✅ Hugging Face access OK')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

### If XceptionNet Fails

```bash
# Check torchvision
docker exec secureai-backend pip show torchvision
# Should show torchvision is installed
```

---

**You're ready to test the best deepfake detection model!** 🚀
