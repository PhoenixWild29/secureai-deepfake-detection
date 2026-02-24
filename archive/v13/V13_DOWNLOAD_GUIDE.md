# V13 Download Guide

## Issue: Download Seems Stuck

V13 downloads **3 large files** (~2-3GB total), which can take **5-10 minutes** or more depending on your connection speed.

## What's Happening

The model downloads:
1. `model_1.safetensors` (~700MB) - ConvNeXt-Large
2. `model_2.safetensors` (~700MB) - ViT-Large  
3. `model_3.safetensors` (~700MB) - Swin-Large

**Total: ~2.1GB**

## Check Download Progress

Run this to see what's happening:

```bash
cd ~/secureai-deepfake-detection
git pull origin master

# Copy test script
docker cp test_v13_download.py secureai-backend:/app/

# Run with verbose output
docker exec secureai-backend python3 test_v13_download.py
```

## If Download is Stuck

### Option 1: Wait It Out
- First download can take 10-15 minutes
- Files are cached, so future loads are instant
- Check your internet connection speed

### Option 2: Check Cache
```bash
# Check if files are being downloaded
docker exec secureai-backend ls -lh ~/.cache/huggingface/hub/models--ash12321--deepfake-detector-v13/
```

### Option 3: Manual Download
If automatic download keeps failing:

1. Download files manually from:
   https://huggingface.co/ash12321/deepfake-detector-v13/tree/main

2. Place files in cache directory:
   ```bash
   # Find cache directory
   docker exec secureai-backend python3 -c "from huggingface_hub import hf_hub_download; print(hf_hub_download.__code__.co_filename)"
   ```

## Improved Download Code

The updated code now:
- ✅ Has retry logic (3 attempts)
- ✅ Shows progress messages
- ✅ Resumes interrupted downloads
- ✅ Better error handling

## Test After Download

Once download completes:

```bash
docker exec secureai-backend python3 -c "
from ai_model.deepfake_detector_v13 import get_deepfake_detector_v13
import logging
logging.basicConfig(level=logging.INFO)

v13 = get_deepfake_detector_v13()
if v13 and v13.model_loaded:
    print('✅ V13 ready!')
    print(f'Models: {len(v13.models)}/3')
"
```

## Expected Timeline

- **Fast connection (100+ Mbps)**: 2-3 minutes
- **Medium connection (50 Mbps)**: 5-7 minutes
- **Slow connection (10 Mbps)**: 10-15 minutes

**Be patient - it's worth it!** The model is 699M parameters and provides 95.86% F1 score! 🚀
