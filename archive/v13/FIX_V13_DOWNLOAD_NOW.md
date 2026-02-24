# Fix V13 Download - Step by Step

## Problem
Download appears to hang or fail silently. Files not appearing in container.

## Solution: Manual Download with Progress

### Step 1: Check Current Status

```bash
cd ~/secureai-deepfake-detection
git pull origin master

# Copy status checker
docker cp check_v13_status.py secureai-backend:/app/

# Check what's actually downloaded
docker exec secureai-backend python3 check_v13_status.py
```

This will show:
- Which files are downloaded (if any)
- Where they are located
- What's missing

### Step 2: Manual Download (If Files Missing)

```bash
# Copy manual download script
docker cp download_v13_manual.py secureai-backend:/app/

# Run manual download (shows progress)
docker exec secureai-backend python3 download_v13_manual.py
```

This will:
- ✅ Show visible progress
- ✅ Download each file one at a time
- ✅ Show file sizes and download times
- ✅ Handle errors gracefully
- ✅ Resume if interrupted

### Step 3: Verify Download

After download completes:

```bash
# Check status again
docker exec secureai-backend python3 check_v13_status.py
```

Should show all 3 files downloaded.

### Step 4: Test V13

```bash
# Test V13 loading
docker exec secureai-backend python3 -c "
from ai_model.deepfake_detector_v13 import get_deepfake_detector_v13
import logging
logging.basicConfig(level=logging.INFO)

v13 = get_deepfake_detector_v13()
if v13 and v13.model_loaded:
    print('✅ V13 loaded successfully!')
    print(f'Models: {len(v13.models)}/3')
else:
    print('❌ V13 not loaded')
"
```

## Why Manual Download Works Better

1. **Visible Progress**: Shows each file downloading
2. **Better Error Messages**: Tells you exactly what failed
3. **Resumable**: Can restart if interrupted
4. **Verification**: Checks file exists and size after download

## Expected Output

```
[1/3] Downloading ConvNeXt-Large (model_1.safetensors)...
   File size: ~700MB
   Estimated time: 2-5 minutes
   Connecting to Hugging Face...
   ✅ Downloaded: 712.3MB in 127.5 seconds
   Location: /home/app/.cache/huggingface/...

[2/3] Downloading ViT-Large (model_2.safetensors)...
   ...
```

## If Download Still Fails

1. **Check Internet**: `docker exec secureai-backend curl -I https://huggingface.co`
2. **Check Disk Space**: `docker exec secureai-backend df -h`
3. **Check Hugging Face Access**: The model might be private or require authentication

---

**Run the manual download script - it will show you exactly what's happening!** 🚀
