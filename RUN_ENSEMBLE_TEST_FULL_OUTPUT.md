# Run Ensemble Test - See Full Results

## Issue: Only 4 Videos Found

The script is finding videos in multiple locations. It found 4 videos, likely from:
- `test_video_*.mp4` files in root directory
- Or a subset from `uploads/`

To test more videos, you can:

### Option 1: Test All Videos in uploads/ (up to 10 by default)

```bash
# Set environment variable to test more videos
docker exec secureai-backend bash -c "MAX_TEST_VIDEOS=20 python /app/test_ensemble_comprehensive.py 2>&1 | grep -v 'CUDA error' | grep -v 'cuInit'"
```

### Option 2: See Full Output (Including Progress)

The test might be running but output is being filtered. Try this to see progress:

```bash
# See all output except CUDA errors
docker exec secureai-backend python /app/test_ensemble_comprehensive.py 2>&1 | grep -v "CUDA error" | grep -v "cuInit" | grep -v "stream_executor"
```

### Option 3: Check if Test is Still Running

The test might be processing (CPU inference is slow). Check if it's still running:

```bash
# Check if Python process is running
docker exec secureai-backend ps aux | grep python
```

### Option 4: Test with Timeout and See Partial Results

```bash
# Run with 5 minute timeout, see what we get
timeout 300 docker exec secureai-backend python /app/test_ensemble_comprehensive.py 2>&1 | grep -v "CUDA error" | grep -v "cuInit"
```

## Why Only 4 Videos?

The script checks multiple locations:
1. `test_videos/real/` and `test_videos/fake/` (labeled)
2. `datasets/unified_deepfake/test/` or `/val/` (labeled)
3. `uploads/` (unlabeled - limited to 10 by default)
4. Root directory `test_video*.mp4` files

It found 4 videos, likely from root directory or a subset. The updated script will show you exactly where it's finding videos.

## See Results Even if Test is Slow

If the test is running but slow (CPU inference takes time), you can:

1. **Check the results file** (if it was created):
```bash
docker exec secureai-backend cat /app/ensemble_test_results.json
```

2. **Run test on just 1 video** to see if it works:
```bash
# Test on a single video quickly
docker exec secureai-backend python -c "
from ai_model.detect import detect_fake
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
result = detect_fake('uploads/test_video_2.mp4', model_type='ensemble')
print('Ensemble:', result.get('ensemble_fake_probability', result.get('confidence', 0)))
print('CLIP:', result.get('clip_fake_probability', 0))
print('ResNet:', result.get('resnet_fake_probability', 0))
"
```

